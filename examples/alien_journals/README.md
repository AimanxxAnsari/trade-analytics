# Example journals in other formats

Synthetic files (not real trades) used to demonstrate and test `trade-journal convert`.

| File | Format | Command |
|---|---|---|
| `mt4_export.csv` | MetaTrader 4/5 account-history export: duplicate `Price` columns, gross `Profit`, signed `Commission`/`Swap`, a non-trade `balance` row | `uv run trade-journal convert examples/alien_journals/mt4_export.csv --preset mt4 --multiplier 100000 --drop-invalid -o out/mt4.csv` |
| `generic_journal.csv` | Spreadsheet journal: day-first dates, `$1,250.00` and `(320.50)` numbers, an `R` column, a bad `Flat` side | `uv run trade-journal convert examples/alien_journals/generic_journal.csv --dayfirst --drop-invalid -o out/generic.csv` |

Each conversion writes the canonical CSV plus a `.conversion.md` report listing the column
mapping, every derivation and every dropped row.
