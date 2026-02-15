# E2E Test: Workspace Toolchains Multi-language

Este test valida la fase de toolchains en `workspace` con cuatro repositorios locales (fixtures):

1. Rust
2. Node.js + TypeScript
3. Python
4. C

Para cada caso:
- se crea una sesion de workspace desde un repo local incluido en la imagen,
- se descubre el catalogo de tools por API,
- `vLLM` propone el orden de ejecucion,
- se ejecutan tools especificas del lenguaje y meta-tools `repo.*`,
- y se valida que `repo.detect_toolchain` detecte el lenguaje correcto.

## Build y push

```bash
cd e2e/tests/17-workspace-toolchains-multilang
make build-push
```

## Deploy e inspeccion

```bash
make deploy
make status
make logs
make delete
```

## Modo remoto (workspace desplegado en cluster)

Este modo **no** arranca workspace local dentro del job. En su lugar usa un runtime temporal
`workspace-toolchains-e2e` desplegado en el namespace.

```bash
cd e2e/tests/17-workspace-toolchains-multilang
make build-push
make deploy-remote
make status-remote
make logs-remote
make delete-remote
make runtime-down
```

## Variables de entorno

- `WORKSPACE_URL` (default job): `http://127.0.0.1:50053`
- `START_LOCAL_WORKSPACE` (default job): `true`
- `WORKSPACE_BINARY` (default job): `/usr/local/bin/workspace-service`
- `WORKSPACE_PORT` (default job): `50053`
- `FIXTURE_ROOT` (default job): `/app/e2e/tests/17-workspace-toolchains-multilang/fixtures`
- `VLLM_CHAT_URL` (default job): `http://vllm-server-service.swe-ai-fleet.svc.cluster.local:8000/v1/chat/completions`
- `VLLM_MODEL` (default job): `Qwen/Qwen3-0.6B`
- `REQUIRE_VLLM` (`true|false`, default job: `true`)
- `STRICT_VLLM_PLAN` (`true|false`, default job: `false`)
- `EVIDENCE_FILE` (default script): `/tmp/evidence-17.json`

Modo remoto (`job.remote.yaml`):

- `WORKSPACE_URL`: `http://workspace-toolchains-e2e.swe-ai-fleet.svc.cluster.local:50053`
- `START_LOCAL_WORKSPACE`: `false`
- `EVIDENCE_FILE`: `/tmp/evidence-17-remote.json`

## Evidence output

- El test escribe evidencia JSON en `EVIDENCE_FILE`.
- El mismo JSON se imprime en logs entre:
  - `EVIDENCE_JSON_START`
  - `EVIDENCE_JSON_END`
