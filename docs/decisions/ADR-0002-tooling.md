# ADR-0002: Tooling and project layout

- **Date:** 2026-11-24
- **Status:** accepted

## Context
Need a reproducible, lightweight Python setup that CI can run and that reviewers recognise.

## Options considered
| Option | Pros | Cons |
|---|---|---|
| pip + requirements.txt | universal | no lockfile by default, slower |
| conda | good for scientific stacks | heavy; environment drift |
| Poetry | lockfile, mature | slower; extra tool |
| **uv** | fast, lockfile (`uv.lock`), manages Python versions | newer |

Layout: flat `trade_analytics/` vs **`src/` layout**. The `src/` layout forces tests to run against
the installed package, catching import-path mistakes.

## Decision
- **uv** with `uv.lock` committed; **Python 3.12**.
- **`src/` layout.**
- **pytest** + **Hypothesis** (property-based tests for statistical identities).
- **ruff** for linting and formatting.
- **GitHub Actions** CI: lint, format check, tests on every push.
- Dependencies kept minimal: numpy, pandas, scipy.

## Consequences
- Anyone can reproduce the environment with `uv sync --all-groups`.
- Adding a heavy dependency (e.g. PyMC) later requires a new ADR.
