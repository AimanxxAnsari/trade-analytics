"""Command-line interface: check, convert and analyse trade journals.

    trade-journal check   journal.csv              # is it already in canonical form?
    trade-journal convert journal.csv -o out.csv   # map an alien format to canonical
    trade-journal analyse journal.csv -o reports/x # convert if needed, then full report

Run ``trade-journal <command> --help`` for options.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from trade_analytics.ingest import (
    PRESETS,
    ConversionOptions,
    JournalConversionError,
    convert_journal,
    mapping_template,
)
from trade_analytics.schema import REQUIRED_COLUMNS, TradeSchemaError, validate_trades


def _options(args: argparse.Namespace) -> ConversionOptions:
    overrides = {
        "timezone": args.tz,
        "dayfirst": args.dayfirst or None,
        "multiplier": args.multiplier,
        "drop_invalid": args.drop_invalid or None,
        "pnl_is_gross": args.pnl_gross or None,
        "time_format": args.time_format,
    }
    if args.mapping:
        return ConversionOptions.from_json(args.mapping, **overrides)
    if args.preset:
        return ConversionOptions.from_preset(args.preset, **overrides)
    opts = ConversionOptions()
    for k, v in overrides.items():
        if v is not None:
            setattr(opts, k, v)
    return opts


def _read(path: str) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def _read_canonical(path: str) -> pd.DataFrame:
    """Read a journal expected to be canonical; raise TradeSchemaError if it is not."""
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise TradeSchemaError(f"missing required columns: {missing}")
    for col in ("entry_time", "exit_time"):
        df[col] = pd.to_datetime(df[col], errors="coerce", format="ISO8601")
    return validate_trades(df)


def cmd_check(args: argparse.Namespace) -> int:
    try:
        trades = _read_canonical(args.journal)
    except (TradeSchemaError, ValueError) as e:
        print(f"NOT canonical: {e}")
        print("Automatic mapping guess (save with `convert --write-mapping`):")
        print(json.dumps(mapping_template(_read(args.journal))["columns"], indent=2))
        return 1
    print(f"OK: {len(trades)} trades pass the canonical schema")
    return 0


def _convert(args: argparse.Namespace):
    raw = _read(args.journal)
    if args.write_mapping:
        Path(args.write_mapping).write_text(json.dumps(mapping_template(raw), indent=2))
        print(f"mapping template written to {args.write_mapping}; edit it and pass --mapping")
        return None
    return convert_journal(raw, _options(args))


def cmd_convert(args: argparse.Namespace) -> int:
    try:
        result = _convert(args)
    except JournalConversionError as e:
        print(f"conversion failed: {e}")
        if e.result is not None and len(e.result.row_issues):
            print(e.result.row_issues.to_string(index=False))
        return 1
    if result is None:
        return 0
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.trades.to_csv(out, index=False, float_format="%.10g")
    report = out.with_suffix(".conversion.md")
    report.write_text(result.to_markdown())
    print(f"{len(result.trades)} trades written to {out}; report: {report}")
    return 0


def cmd_analyse(args: argparse.Namespace) -> int:
    from trade_analytics.report import build_report

    try:
        trades = _read_canonical(args.journal)
        print("journal is canonical; no conversion needed")
    except (TradeSchemaError, ValueError):
        try:
            result = _convert(args)
        except JournalConversionError as e:
            print(f"conversion failed: {e}")
            return 1
        if result is None:
            return 0
        trades = result.trades
        Path(args.output).mkdir(parents=True, exist_ok=True)
        (Path(args.output) / "conversion.md").write_text(result.to_markdown())
        print(f"converted {len(trades)} trades")
    build_report(trades, args.output, title=args.title)
    print(f"report written to {Path(args.output) / 'REPORT.md'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="trade-journal", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="command", required=True)

    def conversion_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--preset", choices=sorted(PRESETS), help="known export format")
        sp.add_argument("--mapping", help="JSON mapping file (see --write-mapping)")
        sp.add_argument("--write-mapping", help="write a mapping template and stop")
        sp.add_argument("--tz", help="time zone of naive timestamps (default UTC)")
        sp.add_argument("--dayfirst", action="store_true", help="dates are DD/MM/YYYY")
        sp.add_argument("--time-format", help="explicit strftime format for timestamps")
        sp.add_argument("--multiplier", type=float, help="contract multiplier (default 1)")
        sp.add_argument("--pnl-gross", action="store_true", help="P&L column excludes costs")
        sp.add_argument("--drop-invalid", action="store_true", help="drop bad rows, list them")

    c = sub.add_parser("check", help="validate a canonical journal")
    c.add_argument("journal")
    c.set_defaults(func=cmd_check)

    v = sub.add_parser("convert", help="convert any journal to canonical form")
    v.add_argument("journal")
    v.add_argument("-o", "--output", default="data/clean/journal.csv")
    conversion_args(v)
    v.set_defaults(func=cmd_convert)

    a = sub.add_parser("analyse", help="convert if needed, then run the full report")
    a.add_argument("journal")
    a.add_argument("-o", "--output", default="reports/private/journal")
    a.add_argument("--title", default="Trading journal: statistical assessment")
    conversion_args(a)
    a.set_defaults(func=cmd_analyse)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
