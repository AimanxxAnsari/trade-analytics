# data/

Raw trade exports go here **locally only**. Everything in this folder except this README is
git-ignored (see `docs/decisions/ADR-0001-private-trade-data.md`).

Expected layout:

```
data/
  raw/        original journal/broker export, never edited
  clean/      canonical trade table produced by the loader
```
