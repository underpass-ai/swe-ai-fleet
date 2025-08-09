# Formatting & Editor Guide (Local-only)

This guide helps you set up your editor locally. Do not commit workspace settings.

## Ruff configuration
Ruff is configured via `pyproject.toml`:

- `line-length = 100`
- `target-version = py311`
- `src = ["src"]`
- Lint rules: `F, E, I, UP, B`
- Per-file ignore: `src/edgecrew/__init__.py: F401`

## VS Code / Cursor (local)
1. Install the Ruff extension.
2. In your User Settings (not workspace), enable:
   - Run Ruff on save
   - Code actions on save: fixAll + organizeImports (Ruff)
   - Optional: format on save with Ruff

Suggested user settings (copy to your personal settings.json):

```json
{
  "ruff.enable": true,
  "ruff.lint.run": "onSave",
  "editor.codeActionsOnSave": {
    "source.fixAll.ruff": true,
    "source.organizeImports.ruff": true
  },
  "editor.formatOnSave": true,
  "python.formatting.provider": "none",
  "editor.rulers": [100]
}
```

> Note: do not commit `.vscode/` to the repository.

## Pre-commit hooks
We run Ruff via pre-commit:

```bash
pre-commit install
pre-commit run --all-files
```

## Typical issues
- F401 (unused import): remove the symbol or prefix with `_` if intentional.
- E501 (line too long): use literal concatenation within parentheses.
- Import order: Ruff (I) will organize imports automatically on save with the extension.


