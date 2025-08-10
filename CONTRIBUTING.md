# Contributing to SWE AI Fleet

- Fork and create feature branches.
- Open an RFC for substantial changes (`/docs/RFC-XXXX.md`).
- Add unit tests for new behavior.
- Keep code clean, SOLID, and testable. Minimal, essential comments only

## Git Workflow

Please read the [Git Workflow &amp; Contribution Guide](docs/GIT_WORKFLOW.md) for branching,
commit conventions, PR requirements, and the release process.

## Formatting & Linting (Ruff) — Local-first

We use Ruff for linting/formatting. Keep your local editor configured, but do not commit editor/workspace settings.

### One-time setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . ruff pre-commit
pre-commit install
```

### Run locally

```bash
# Lint only
ruff check .

# Auto-fix safe issues (imports, simple refactors)
ruff check . --fix

# Format (optional, if using Ruff as formatter)
ruff format .
```

### CI

CI runs `ruff check` on every PR. Fix locally before pushing.

### Long lines (E501)

Prefer implicit literal concatenation:

```py
content = (
    f"# plan for: {task}\n"
    "---\n"
    "apiVersion: v1\n"
    "kind: ConfigMap\n"
    "metadata:\n"
    "  name: demo"
)
```

Avoid `# noqa: E501` unless strictly necessary.

### Pre-commit

We use pre-commit to ensure consistent formatting before commit.

```bash
pre-commit run --all-files
```

### Editor (VS Code / Cursor)

Install the Ruff extension locally and enable format-on-save + fixAll in your User Settings.
Do not commit `.vscode/`.
See `docs/FORMATTING.md` for suggested local settings.
