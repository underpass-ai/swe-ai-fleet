# E2E Test: Workspace vLLM Go TODO Evolution

Este test valida un caso de uso SWE real en dos fases sobre un repositorio Go semilla:

1. Crear un programa TODO en Go con tests y verificar que pasan.
2. Aplicar una modificacion funcional agregando fecha de completado y volver a verificar.

El agente (`vLLM`) primero descubre el catalogo de tools desde la API de `workspace` y devuelve un plan por fase.

## Que verifica

1. Bootstrap de sesion de workspace desde repositorio local empaquetado en la imagen.
2. Descubrimiento dinamico del catalogo (`tools.list`) y resolucion de aliases `fs.*`.
3. Planificacion por fase via `vLLM` (JSON estricto con `ordered_tools`).
4. Fase 1:
   - escritura de `main.go` y `main_test.go`,
   - validacion con `repo.run_tests` (y `repo.build`/`repo.detect_project_type` si disponibles).
5. Fase 2:
   - evolucion de modelo con `CompletedAt *time.Time`,
   - actualizacion de tests,
   - nueva validacion con `repo.run_tests`.
6. Evidencia estructurada completa (pasos, planes, invocaciones y resultado final).

## Build y push

```bash
cd e2e/tests/16-workspace-vllm-go-todo-evolution
make build-push
```

## Deploy e inspeccion

```bash
make deploy
make status
make logs
make delete
```

## Variables de entorno

- `WORKSPACE_URL` (default job): `http://127.0.0.1:50053`
- `START_LOCAL_WORKSPACE` (default job): `true`
- `WORKSPACE_BINARY` (default job): `/usr/local/bin/workspace-service`
- `SOURCE_REPO_PATH` (default job): `/app/e2e/tests/16-workspace-vllm-go-todo-evolution/fixtures/todo-go-repo`
- `VLLM_CHAT_URL` (default job): `http://vllm-server-service.swe-ai-fleet.svc.cluster.local:8000/v1/chat/completions`
- `VLLM_MODEL` (default job): `Qwen/Qwen3-0.6B`
- `REQUIRE_VLLM` (`true|false`, default job: `true`)
- `STRICT_VLLM_PLAN` (`true|false`, default job: `false`)
- `EVIDENCE_FILE` (default script): `/tmp/evidence-16.json`

## Evidence output

- El test escribe evidencia JSON en `EVIDENCE_FILE`.
- El mismo JSON se imprime en logs entre:
  - `EVIDENCE_JSON_START`
  - `EVIDENCE_JSON_END`
