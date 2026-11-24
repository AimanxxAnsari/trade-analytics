"""Check and convert trade journals in arbitrary formats to the canonical schema.

Journals come from brokers (MT4/MT5 exports), spreadsheets and apps, each with
its own column names, number formats, date formats and sign conventions. This
module maps them onto the canonical schema (``schema.py``) and reports every
decision it made, so a conversion is auditable rather than magic.

Pipeline
--------
1. **Column mapping** - explicit mapping (user JSON / preset) first, then
   automatic matching of normalised header names against an alias table.
2. **Value parsing** - numbers ("$1,234.50", "(12.3)"), directions
   ("Buy", "SHORT", "-1"), timestamps (any format, optional day-first, source
   time zone converted to UTC).
3. **Derivation** - missing fields derived where possible: direction from a
   signed size, P&L from prices, net P&L from gross P&L and costs, risk from an
   R-multiple column or from the stop price, trade ids generated.
4. **Row validation** - every row checked; invalid rows either fail the
   conversion or are dropped (``drop_invalid``) and listed in the report.
5. **Table validation** - the result must pass ``validate_trades``.

See ``docs/design/journal-ingest.md`` and ADR-0007.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from trade_analytics.schema import REQUIRED_COLUMNS, validate_trades

# ---------------------------------------------------------------------------
# Alias table: canonical field -> accepted (normalised) source header names,
# in priority order. Normalisation: lower case, every run of non-alphanumeric
# characters replaced by a single space, trimmed. "P&L" -> "p l", "S/L" -> "s l".
# ---------------------------------------------------------------------------
ALIASES: dict[str, list[str]] = {
    "trade_id": [
        "trade id",
        "id",
        "ticket",
        "trade no",
        "trade number",
        "position id",
        "deal",
        "order id",
        "order",
    ],
    "instrument": [
        "instrument",
        "symbol",
        "ticker",
        "asset",
        "market",
        "pair",
        "coin",
        "item",
        "contract",
        "security",
        "underlying",
    ],
    "direction": [
        "direction",
        "side",
        "type",
        "trade type",
        "action",
        "buy sell",
        "long short",
        "position",
    ],
    "entry_time": [
        "entry time",
        "open time",
        "entry date",
        "open date",
        "opened",
        "time open",
        "entry datetime",
        "open datetime",
        "date opened",
        "date",
        "datetime",
        "time",
    ],
    "exit_time": [
        "exit time",
        "close time",
        "exit date",
        "close date",
        "closed",
        "time close",
        "exit datetime",
        "close datetime",
        "date closed",
    ],
    "entry_price": [
        "entry price",
        "open price",
        "price open",
        "avg entry price",
        "average entry price",
        "entry",
    ],
    "exit_price": [
        "exit price",
        "close price",
        "price close",
        "avg exit price",
        "average exit price",
        "exit",
    ],
    "size": [
        "size",
        "qty",
        "quantity",
        "volume",
        "lots",
        "lot",
        "contracts",
        "units",
        "shares",
        "position size",
        "amount",
    ],
    "pnl": [
        "pnl",
        "net pnl",
        "net p l",
        "p l",
        "net profit",
        "profit",
        "profit loss",
        "realized pnl",
        "realised pnl",
        "closed pnl",
        "gain loss",
        "result",
    ],
    "risk_amount": ["risk amount", "risk", "initial risk", "planned risk", "risk usd", "1r"],
    "stop_price": ["stop price", "stop loss", "stop", "sl", "s l", "initial stop"],
    "setup": ["setup", "strategy", "playbook", "pattern", "tag", "tags"],
}
# Cost columns: all matches are summed into ``fees``.
FEE_ALIASES = [
    "fees",
    "fee",
    "commission",
    "commissions",
    "costs",
    "swap",
    "swaps",
    "taxes",
    "tax",
    "financing",
    "rollover",
    "funding",
]
R_ALIASES = ["r", "r multiple", "r multiple result", "result r"]

LONG_WORDS = {"long", "buy", "b", "l", "bot", "bought", "1", "+1"}
SHORT_WORDS = {"short", "sell", "s", "sld", "sold", "-1"}

PRESETS: dict[str, dict] = {
    # MetaTrader 4/5 "account history" export saved as CSV. The second "Price"
    # column (close price) arrives as "Price.1" after pandas de-duplication.
    "mt4": {
        "columns": {
            "trade_id": "Ticket",
            "entry_time": "Open Time",
            "direction": "Type",
            "size": "Size",
            "instrument": "Item",
            "entry_price": "Price",
            "stop_price": "S / L",
            "exit_time": "Close Time",
            "exit_price": "Price.1",
            "pnl": "Profit",
        },
        "fees": ["Commission", "Taxes", "Swap"],
        "pnl_is_gross": True,
        "time_format": "%Y.%m.%d %H:%M:%S",
    },
}


def normalise_header(name: str) -> str:
    return re.sub(r"[^0-9a-z]+", " ", str(name).lower()).strip()


@dataclass
class ConversionOptions:
    mapping: dict[str, str] = field(default_factory=dict)  # canonical -> source column
    fee_columns: list[str] | None = None  # explicit cost columns
    pnl_is_gross: bool = False  # P&L excludes the cost columns
    timezone: str = "UTC"  # time zone of naive timestamps in the source
    dayfirst: bool = False
    time_format: str | None = None
    multiplier: float = 1.0  # contract multiplier for price-derived P&L / risk
    drop_invalid: bool = False

    @classmethod
    def from_preset(cls, name: str, **overrides) -> ConversionOptions:
        if name not in PRESETS:
            raise ValueError(f"unknown preset {name!r}; available: {sorted(PRESETS)}")
        p = PRESETS[name]
        opts = cls(
            mapping=dict(p["columns"]),
            fee_columns=list(p.get("fees", [])),
            pnl_is_gross=p.get("pnl_is_gross", False),
            time_format=p.get("time_format"),
        )
        for k, v in overrides.items():
            if v is not None:
                setattr(opts, k, v)
        return opts

    @classmethod
    def from_json(cls, path: str | Path, **overrides) -> ConversionOptions:
        cfg = json.loads(Path(path).read_text())
        opts = cls(
            mapping={k: v for k, v in cfg.get("columns", {}).items() if v},  # blanks = auto
            fee_columns=cfg.get("fees"),
            pnl_is_gross=cfg.get("pnl_is_gross", False),
            timezone=cfg.get("timezone", "UTC"),
            dayfirst=cfg.get("dayfirst", False),
            time_format=cfg.get("time_format"),
            multiplier=cfg.get("multiplier", 1.0),
        )
        for k, v in overrides.items():
            if v is not None:
                setattr(opts, k, v)
        return opts


@dataclass
class ConversionResult:
    trades: pd.DataFrame
    mapping: dict[str, str]  # canonical field -> source column (or derivation note)
    fee_columns: list[str]
    unmapped_columns: list[str]
    notes: list[str]
    row_issues: pd.DataFrame  # line (1-based file line incl. header), problem
    n_input_rows: int

    @property
    def n_dropped(self) -> int:
        return int(self.row_issues["line"].nunique()) if len(self.row_issues) else 0

    def to_markdown(self) -> str:
        lines = [
            "# Journal conversion report",
            "",
            f"- Input rows: {self.n_input_rows}",
            f"- Output trades: {len(self.trades)}",
            f"- Rows with problems: {self.n_dropped}",
            "",
            "## Column mapping",
            "",
            "| Canonical field | Source |",
            "|---|---|",
            *[f"| `{k}` | {v} |" for k, v in self.mapping.items()],
            f"| `fees` | {', '.join(self.fee_columns) if self.fee_columns else 'none'} |",
            "",
            f"Unmapped source columns (ignored): {', '.join(self.unmapped_columns) or 'none'}",
            "",
            "## Conversion notes",
            "",
            *[f"- {n}" for n in self.notes],
        ]
        if len(self.row_issues):
            lines += ["", "## Row problems", "", "| File line | Problem |", "|---|---|"]
            lines += [f"| {r.line} | {r.problem} |" for r in self.row_issues.itertuples()]
        return "\n".join(lines) + "\n"


class JournalConversionError(ValueError):
    def __init__(self, message: str, result: ConversionResult | None = None):
        super().__init__(message)
        self.result = result


# --------------------------------------------------------------------- parsing


def parse_numbers(s: pd.Series) -> pd.Series:
    """Parse numbers written as text: currency symbols, thousands separators,
    accounting negatives "(12.5)", unicode minus. Unparseable values -> NaN."""
    if pd.api.types.is_numeric_dtype(s):
        return s.astype(float)
    t = s.astype("string").str.strip()
    neg = t.str.match(r"^\(.*\)$", na=False)
    t = t.str.replace("−", "-", regex=False)
    t = t.str.replace(r"[^0-9eE+\-.]", "", regex=True)
    out = pd.to_numeric(t, errors="coerce")
    return out.where(~neg, -out.abs()).astype(float)


def parse_direction(s: pd.Series) -> pd.Series:
    """Map side words to 'long' / 'short'; anything else -> NA."""
    t = s.astype("string").str.strip().str.lower()
    first = t.str.extract(r"^([+\-]?[a-z0-9]+)", expand=False)
    out = pd.Series(pd.NA, index=s.index, dtype="object")
    out[first.isin(LONG_WORDS).fillna(False)] = "long"
    out[first.isin(SHORT_WORDS).fillna(False)] = "short"
    return out


def parse_times(s: pd.Series, opts: ConversionOptions) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(s):
        t = s
    else:
        fmt = opts.time_format or "mixed"
        t = pd.to_datetime(s, format=fmt, dayfirst=opts.dayfirst, errors="coerce", utc=False)
        if t.dtype == object:  # mixed offsets
            t = pd.to_datetime(s, format=fmt, dayfirst=opts.dayfirst, errors="coerce", utc=True)
    if getattr(t.dt, "tz", None) is None:
        t = t.dt.tz_localize(opts.timezone, ambiguous="NaT", nonexistent="NaT")
    return t.dt.tz_convert("UTC")


# --------------------------------------------------------------------- mapping


def auto_map(columns: list[str], explicit: dict[str, str] | None = None) -> dict[str, str]:
    """Map canonical fields to source columns: explicit first, then aliases."""
    explicit = dict(explicit or {})
    missing = [c for c in explicit.values() if c not in columns]
    if missing:
        raise JournalConversionError(f"mapping refers to columns not in the file: {missing}")
    used = set(explicit.values())
    norm = {c: normalise_header(c) for c in columns}
    mapping = dict(explicit)
    for canon, aliases in ALIASES.items():
        if canon in mapping:
            continue
        for alias in aliases:
            hit = next((c for c in columns if c not in used and norm[c] == alias), None)
            if hit is not None:
                mapping[canon] = hit
                used.add(hit)
                break
    return mapping


def _find_columns(columns: list[str], aliases: list[str], used: set[str]) -> list[str]:
    return [c for c in columns if c not in used and normalise_header(c) in aliases]


# --------------------------------------------------------------------- convert


def convert_journal(raw: pd.DataFrame, opts: ConversionOptions | None = None) -> ConversionResult:
    """Convert a raw journal DataFrame to the canonical schema (see module docstring)."""
    opts = opts or ConversionOptions()
    raw = raw.copy()
    raw.columns = [str(c).strip() for c in raw.columns]
    columns = list(raw.columns)
    notes: list[str] = []

    mapping = auto_map(columns, opts.mapping)
    used = set(mapping.values())
    fee_cols = (
        list(opts.fee_columns)
        if opts.fee_columns is not None
        else _find_columns(columns, FEE_ALIASES, used)
    )
    missing_fee = [c for c in fee_cols if c not in columns]
    if missing_fee:
        raise JournalConversionError(f"fee columns not in the file: {missing_fee}")
    used |= set(fee_cols)
    r_cols = _find_columns(columns, R_ALIASES, used)
    r_col = r_cols[0] if r_cols else None
    if r_col:
        used.add(r_col)
    source = {k: v for k, v in mapping.items()}

    out = pd.DataFrame(index=raw.index)
    get = lambda f: raw[mapping[f]] if f in mapping else None  # noqa: E731

    # Instrument / setup: text.
    if "instrument" in mapping:
        out["instrument"] = get("instrument").astype("string").str.strip()
    if "setup" in mapping:
        out["setup"] = get("setup").astype("string").str.strip()

    # Numbers.
    for f in ("entry_price", "exit_price", "size", "pnl", "risk_amount", "stop_price"):
        if f in mapping:
            out[f] = parse_numbers(get(f))

    # Direction: from a side column, else from the sign of size.
    if "direction" in mapping:
        out["direction"] = parse_direction(get("direction"))
    elif "size" in out:
        out["direction"] = np.where(out["size"] < 0, "short", "long")
        source["direction"] = f"derived from sign of `{mapping['size']}`"
        notes.append("direction derived from the sign of size (negative = short)")
    if "size" in out:
        if (out["size"] < 0).any():
            notes.append("negative sizes converted to absolute values")
        out["size"] = out["size"].abs()

    # Times.
    for f in ("entry_time", "exit_time"):
        if f in mapping:
            out[f] = parse_times(get(f), opts)
    if "entry_time" in out and "exit_time" not in out:
        out["exit_time"] = out["entry_time"]
        source["exit_time"] = f"copied from `{mapping['entry_time']}`"
        notes.append("no exit time column: exit_time set equal to entry_time")
    if opts.timezone != "UTC":
        notes.append(f"naive timestamps interpreted as {opts.timezone} and converted to UTC")

    # Costs. Convention: if any cost value is negative the columns are signed
    # cash flows (MT4: commission -7.0, swap +0.3); otherwise positive costs.
    fees = pd.Series(0.0, index=raw.index)
    if fee_cols:
        cost = pd.concat([parse_numbers(raw[c]).fillna(0.0) for c in fee_cols], axis=1)
        if (cost < 0).any().any():
            fees = -cost.sum(axis=1)
            notes.append(f"cost columns {fee_cols} treated as signed cash flows (fee = -sum)")
        else:
            fees = cost.sum(axis=1)
            notes.append(f"cost columns {fee_cols} treated as positive costs")
    out["fees"] = fees

    # P&L: from a column (net or gross) or derived from prices.
    if "pnl" in out:
        if opts.pnl_is_gross:
            out["pnl"] = out["pnl"] - fees
            notes.append("P&L column is gross: net P&L = P&L - fees")
    elif {"entry_price", "exit_price", "size", "direction"} <= set(out.columns):
        sign = np.where(out["direction"] == "short", -1.0, 1.0)
        out["pnl"] = (
            sign * (out["exit_price"] - out["entry_price"]) * out["size"] * opts.multiplier - fees
        )
        source["pnl"] = "derived: sign x (exit - entry) x size x multiplier - fees"
        notes.append(f"P&L derived from prices (multiplier {opts.multiplier})")

    # Risk: column, else |pnl / R|, else from stop.
    if "risk_amount" not in out:
        if r_col is not None and "pnl" in out:
            r = parse_numbers(raw[r_col])
            out["risk_amount"] = (out["pnl"] / r).abs().where(r != 0)
            source["risk_amount"] = f"derived: |pnl / `{r_col}`|"
            notes.append(f"risk_amount derived from R-multiple column `{r_col}`")
        elif {"stop_price", "entry_price", "size"} <= set(out.columns):
            out["risk_amount"] = (
                (out["entry_price"] - out["stop_price"]).abs() * out["size"] * opts.multiplier
            )
            source["risk_amount"] = "derived: |entry - stop| x size x multiplier"
            notes.append("risk_amount derived from stop price")
    if "risk_amount" in out:
        bad = out["risk_amount"] <= 0
        if bad.any():
            out.loc[bad, "risk_amount"] = np.nan
            notes.append(f"{int(bad.sum())} non-positive risk values set to missing")

    # Trade ids.
    if "trade_id" in mapping:
        out["trade_id"] = get("trade_id").astype("string").str.strip()
    else:
        out["trade_id"] = [f"J{i + 1:05d}" for i in range(len(out))]
        source["trade_id"] = "generated"
        notes.append("no id column: trade ids generated")

    # ------------------------------------------------------------- row checks
    missing_fields = [f for f in REQUIRED_COLUMNS if f not in out.columns]
    if missing_fields:
        result = ConversionResult(
            out,
            source,
            fee_cols,
            [c for c in columns if c not in used],
            notes,
            pd.DataFrame(columns=["line", "problem"]),
            len(raw),
        )
        raise JournalConversionError(
            f"could not find or derive required fields {missing_fields}. "
            f"Columns in file: {columns}. Provide a mapping file (see --write-mapping).",
            result,
        )

    # Problems are reported by file line: header is line 1, first data row line 2.
    problems: list[tuple[int, int, str]] = []

    def flag(mask: pd.Series, text: str) -> None:
        for i in out.index[mask.fillna(True)]:
            problems.append((int(i), int(i) + 2, text))

    flag(out["direction"].isna(), "direction not recognised")
    for f in ("entry_time", "exit_time"):
        flag(out[f].isna(), f"{f} missing or unparseable")
    for f in ("entry_price", "exit_price", "size"):
        flag(~(out[f] > 0), f"{f} missing or not > 0")
    flag(out["pnl"].isna(), "pnl missing or unparseable")
    flag(out["instrument"].isna() | (out["instrument"] == ""), "instrument missing")
    both = out["entry_time"].notna() & out["exit_time"].notna()
    flag(both & (out["exit_time"] < out["entry_time"]), "exit_time before entry_time")
    dup = out["trade_id"].duplicated(keep="first")
    flag(dup, "duplicate trade_id")

    issues = pd.DataFrame(problems, columns=["index", "line", "problem"]).sort_values(
        ["line", "problem"], kind="stable"
    )
    bad_rows = set(issues.pop("index"))
    issues = issues.reset_index(drop=True)

    # Notional (entry price x size x multiplier): the fallback outcome unit when
    # risk is unknown (ADR-0005).
    out["notional"] = out["entry_price"] * out["size"] * opts.multiplier

    order = ["trade_id", *[c for c in REQUIRED_COLUMNS if c != "trade_id"]]
    order += [
        c for c in ("risk_amount", "stop_price", "fees", "notional", "setup") if c in out.columns
    ]
    result = ConversionResult(
        trades=out[order],
        mapping=source,
        fee_columns=fee_cols,
        unmapped_columns=[c for c in columns if c not in used],
        notes=notes,
        row_issues=issues,
        n_input_rows=len(raw),
    )
    if bad_rows and not opts.drop_invalid:
        raise JournalConversionError(
            f"{len(bad_rows)} of {len(raw)} rows have problems; fix them or use drop_invalid",
            result,
        )
    if bad_rows:
        result.trades = out.loc[~out.index.isin(bad_rows), order]
        result.notes.append(f"{len(bad_rows)} invalid rows dropped (listed below)")
    result.trades = result.trades.reset_index(drop=True)
    validate_trades(result.trades)
    return result


def mapping_template(raw: pd.DataFrame) -> dict:
    """A JSON-serialisable mapping pre-filled with the automatic guesses."""
    columns = [str(c).strip() for c in raw.columns]
    guess = auto_map(columns)
    used = set(guess.values())
    return {
        "columns": {
            k: guess.get(k, "") for k in [*REQUIRED_COLUMNS, "risk_amount", "stop_price", "setup"]
        },
        "fees": _find_columns(columns, FEE_ALIASES, used),
        "pnl_is_gross": False,
        "timezone": "UTC",
        "dayfirst": False,
        "time_format": None,
        "multiplier": 1.0,
        "_source_columns": columns,
    }
