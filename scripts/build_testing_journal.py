"""Build the public testing journal from the Hyperliquid fills dataset.

Usage:
    uv run python scripts/build_testing_journal.py <path/to/historical_data.csv>

The source CSV (~47 MB) is not committed. Get it from Kaggle
("Historical Trade Data", pradeepjswl, CC0 1.0) and pass its path.
Output: data/testing_journal/testing_journal.csv + provenance.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from trade_analytics.loaders import load_fills, reconstruct_trades
from trade_analytics.schema import validate_trades

# Selection: the account whose BTC/ETH perpetual fills reconstruct into the most
# complete round trips with the fewest data gaps (see ADR-0004).
ACCOUNT = "0x4f93fead39b70a1824f981a54d4e55b278e9f760"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "testing_journal"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(src: str) -> None:
    src_path = Path(src)
    fills = load_fills(src_path, account=ACCOUNT)
    trades, diag = reconstruct_trades(fills)
    validate_trades(trades)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    trades.to_csv(OUT_DIR / "testing_journal.csv", index=False, float_format="%.10g")
    provenance = {
        "source": "Kaggle: 'Historical Trade Data' (pradeepjswl) — Hyperliquid fills",
        "license": "CC0 1.0 Universal (public domain)",
        "source_sha256": sha256(src_path),
        "account": ACCOUNT,
        "instruments": sorted(trades["instrument"].unique().tolist()),
        "period_utc": [str(trades["entry_time"].min()), str(trades["exit_time"].max())],
        "diagnostics": diag,
    }
    (OUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2))
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
