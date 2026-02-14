# E2E Test: Workspace vLLM Node TODO Evolution

Caso de integración equivalente al test 16, adaptado a Node.js:

1. Fase 1: crear programa TODO + tests.
2. Fase 2: añadir campo `completedAt` y actualizar tests.
3. En cada fase se descubre catálogo, se planifica con vLLM y se valida ejecución.

## Build y push

```bash
cd e2e/tests/19-workspace-vllm-node-todo-evolution
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

- `EVIDENCE_FILE` por defecto: `/tmp/evidence-19.json`
- JSON también en logs entre:
  - `EVIDENCE_JSON_START`
  - `EVIDENCE_JSON_END`
