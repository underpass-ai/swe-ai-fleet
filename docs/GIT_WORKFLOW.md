# Git Workflow & Contribution Guide

This repository follows a lightweight, contributor-friendly workflow based on forks and Pull Requests.

## Branching model
- `main` is **protected**: only PRs are merged.
- Use short-lived branches:
  - `feat/<scope>` for features
  - `fix/<scope>` for bugfixes
  - `chore/<scope>` for tooling/infra
  - `docs/<scope>` for documentation

Prefer **rebasing** your branch on top of `main` before opening a PR:
```bash
git fetch origin
git rebase origin/main
```

## Commit conventions
We use **Conventional Commits**:
- `feat: ...` new capability
- `fix: ...` bug fix
- `docs: ...` docs only
- `style: ...` formatting, no logic changes (e.g., Ruff formatting)
- `refactor: ...` code change without behavior change
- `test: ...` add or update tests
- `chore: ...` tooling, CI, build, deps, etc.

Keep commits atomic; avoid mixing formatting with logic changes.

## Pull Requests
- Target: `main`
- Keep PRs focused (small, reviewable).
- Required checks: CI must be green (lint + unit tests).
- If your PR touches runtime logic, include tests (unit or integration).
- Use the PR template and fill the “Summary” and “Tests” sections.
- Squash merge is recommended to keep linear history.

## Linting & Formatting
- We use **Ruff** for linting and formatting. Run locally:
```bash
ruff check . --fix
ruff format .
```
- Pre-commit is available:
```bash
pre-commit install
pre-commit run --all-files
```

## Test strategy
- `tests/unit`: fast, hermetic.
- `tests/integration`: adapters/services wired (no external binaries by default).
- `tests/e2e`: end-to-end scenarios; may be skipped in CI unless explicitly triggered.

Run locally:
```bash
pytest -q                     # unit only by default (recommended)
pytest -m integration -q      # integration
pytest -m e2e -q              # e2e (may require extra deps)
```

## Issue triage & labels
Use labels to scope and prioritize:
- `kind/bug`, `kind/feature`, `kind/chore`, `kind/docs`
- `prio/high|med|low`
- `area/agents|models|orchestrator|tools|helm|docs`

## Release model
- **SemVer** with tags `vX.Y.Z`.
- Changelogs are generated from merged PRs following Conventional Commits.

## Security & disclosure
Please see `SECURITY.md`. Do **not** disclose vulnerabilities publicly before coordinated resolution.
