# E2E Test: Workspace vLLM C TODO Evolution

Caso de integración equivalente al test 16, adaptado a C:

1. Fase 1: crear programa TODO + tests.
2. Fase 2: añadir campo `completed_at` y actualizar tests.
3. En cada fase se descubre catálogo, se planifica con vLLM y se valida ejecución.

## Build y push

```bash
cd e2e/tests/20-workspace-vllm-c-todo-evolution
make build-push
```

## Deploy e inspección

```bash
make deploy
make status
make logs
make delete
```

## Evidence

- `EVIDENCE_FILE` por defecto: `/tmp/evidence-20.json`
- JSON también en logs entre:
  - `EVIDENCE_JSON_START`
  - `EVIDENCE_JSON_END`
