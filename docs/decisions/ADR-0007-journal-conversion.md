# ADR-0007: Converting journals in other formats

- **Date:** 2026-11-24
- **Status:** accepted

## Context
The analysis needs the canonical schema, but every broker and journaling tool exports something
different. Users (including the personal-journal use case) should not have to reshape files by
hand, and a conversion that silently guesses would undermine trust in every downstream number.

## Options considered
1. **Manual reshaping in a spreadsheet.** No code, but error-prone, undocumented, not repeatable.
2. **One loader per format** (like `loaders.hyperliquid`). Precise, but does not scale to
   arbitrary spreadsheets.
3. **Generic converter:** alias-based column matching + explicit overrides (presets, JSON
   mapping) + derivations + row-level validation + a written conversion report.

## Decision
Option 3 for round-trip journals, keeping dedicated loaders (option 2) only where trades must be
reconstructed from fills.

Specific choices:
- **Explicit beats automatic:** a preset or JSON mapping always overrides alias guesses.
- **Fail by default** on invalid rows; dropping requires `--drop-invalid` and is reported line
  by line.
- **Cost sign convention inferred** (any negative value => signed cash flows) and stated in the
  report.
- **JSON** for mapping files rather than YAML, to avoid a new dependency.
- Exposed as a console command `trade-journal` (`check`, `convert`, `analyse`).

## Consequences
- Any reasonable CSV journal can be analysed in one command, with an audit trail.
- The alias table needs maintenance as new formats appear; new presets can be added in
  `ingest.PRESETS`.
- A single contract multiplier per file is a known limitation (see design doc).
