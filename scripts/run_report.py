"""Run the Pillar 1 analysis on a trade journal.

Usage:
    uv run python scripts/run_report.py [journal.csv] [output_dir]

Defaults to the public testing journal and reports/testing_journal/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from trade_analytics.report import build_report
from trade_analytics.schema import validate_trades

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    journal = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else ROOT / "data/testing_journal/testing_journal.csv"
    )
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "reports/testing_journal"
    trades = pd.read_csv(journal, parse_dates=["entry_time", "exit_time"])
    validate_trades(trades)
    summary = build_report(trades, out_dir, title="Testing journal: statistical assessment")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(f"report written to {out_dir / 'REPORT.md'}")


if __name__ == "__main__":
    main()
