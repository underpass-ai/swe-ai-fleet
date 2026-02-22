# E2E Tests

Este directorio contiene los tests end-to-end (E2E) del proyecto SWE AI Fleet.

## Visión General

Los tests E2E verifican el comportamiento completo del sistema en un entorno real (cluster de Kubernetes). A diferencia de los tests unitarios, los tests E2E:

- Se ejecutan en el cluster de Kubernetes
- Acceden a los servicios desplegados a través de la red interna
- No requieren port forwarding
- Verifican flujos completos entre múltiples servicios

## Estructura

```
e2e/
├── README.md                    # Este archivo
├── PROCEDURE.md                 # Guía detallada para crear nuevos tests
├── run-e2e-tests.sh             # Script para ejecutar tests secuencialmente
├── E2E_TEST_RUNNER_IMPROVEMENTS.md  # Mejoras propuestas para el runner
├── WORKSPACE_E2E_MAINTENANCE_PLAN.md  # Plan de mantenibilidad para workspace E2E
└── tests/
    ├── 01-planning-ui-get-node-relations/  # Test ejemplo
    │   ├── test_get_node_relations.py
    │   ├── Dockerfile
    │   ├── job.yaml
    │   ├── Makefile
    │   └── README.md
    └── NN-test-name/            # Otros tests (numerados secuencialmente)
        └── ...
```

## Tests Disponibles

### 01-planning-ui-get-node-relations

Verifica que Planning UI puede llamar a Context Service `GetGraphRelationships` para obtener relaciones de nodos desde Neo4j.

**Ver**: [README del test](tests/01-planning-ui-get-node-relations/README.md)

### 13-task-derivation-planning-service-grpc

Valida el contrato gRPC real entre Task Derivation y Planning y además
el flujo asíncrono `planning.plan.approved -> task derivation -> tareas derivadas`
con persistencia en Planning.

**Ver**: [README del test](tests/13-task-derivation-planning-service-grpc/README.md)

### 14-workspace-tool-execution

Valida el microservicio `workspace` end-to-end:
- catálogo de tools por sesión,
- ejecución real de tool desde la API (`fs.write`/`fs.read`),
- aislamiento multiagente (workspaces independientes),
- y flujo guiado por prompt hacia `vLLM`.

**Ver**: [README del test](tests/14-workspace-tool-execution/README.md)

### 15-workspace-vllm-tool-orchestration

Valida un flujo más complejo `workspace + vLLM`:
- descubrimiento dinámico del catálogo de tools desde la API,
- planificación de orden de ejecución generada por `vLLM`,
- ejecución coverage-oriented para todos los tools disponibles,
- y validación estricta de `fs.*` con validación environment-aware para `git/repo.*`.

**Ver**: [README del test](tests/15-workspace-vllm-tool-orchestration/README.md)

### 16-workspace-vllm-go-todo-evolution

Valida un caso SWE real de evolución funcional sobre un repositorio Go:
- fase 1: creación de app TODO + tests y verificación,
- fase 2: modificación para incluir fecha de completado + actualización de tests,
- planificación por fase generada por `vLLM` a partir del catálogo de tools,
- y evidencias estructuradas para evaluación del caso de uso completo.

**Ver**: [README del test](tests/16-workspace-vllm-go-todo-evolution/README.md)

### 17-workspace-toolchains-multilang

Valida la fase multi-lenguaje de `workspace` con toolchains reales:
- Rust (`rust.build/test/clippy/format`)
- Node + TypeScript (`node.install/build/typecheck/lint/test`)
- Python (`python.install_deps/validate/test`)
- C (`c.build/test`)
- y meta-tools `repo.detect_toolchain`, `repo.build`, `repo.test`, `repo.validate`.

El flujo se ejecuta como `Job` en Kubernetes, levantando `workspace` local dentro del contenedor de test y dejando evidencia estructurada.

También dispone de variante remota (`17R`) usando runtime temporal `workspace-toolchains-e2e` y job remoto.

**Ver**: [README del test](tests/17-workspace-toolchains-multilang/README.md)

### 18-workspace-vllm-rust-todo-evolution

Versión del caso de integración tipo 16 para Rust:
- fase 1: crea TODO + tests,
- fase 2: añade `completed_at`,
- plan por fase desde vLLM con catálogo descubierto por API.

**Ver**: [README del test](tests/18-workspace-vllm-rust-todo-evolution/README.md)

### 19-workspace-vllm-node-todo-evolution

Versión del caso de integración tipo 16 para Node:
- fase 1: crea TODO + tests,
- fase 2: añade `completedAt`,
- plan por fase desde vLLM con catálogo descubierto por API.

**Ver**: [README del test](tests/19-workspace-vllm-node-todo-evolution/README.md)

### 20-workspace-vllm-c-todo-evolution

Versión del caso de integración tipo 16 para C:
- fase 1: crea TODO + tests,
- fase 2: añade `completed_at`,
- plan por fase desde vLLM con catálogo descubierto por API.

**Ver**: [README del test](tests/20-workspace-vllm-c-todo-evolution/README.md)

## Crear un Nuevo Test

Sigue el procedimiento detallado en [PROCEDURE.md](PROCEDURE.md) para crear nuevos tests E2E.

**Resumen rápido**:

1. Crea el directorio: `e2e/tests/NN-test-name/`
2. Crea los archivos necesarios:
   - `test_*.py` - Script de test
   - `Dockerfile` - Imagen del container
   - `job.yaml` - Kubernetes Job
   - `Makefile` - Build y deploy
   - `README.md` - Documentación
3. Build y deploy:
   ```bash
   cd e2e/tests/NN-test-name
   make build-push
   make deploy
   make logs
   ```

## Ejecutar Tests

### Ejecución Secuencial (Recomendado)

Para ejecutar todos los tests E2E de forma secuencial (01-43), usa el script runner:

```bash
# Desde la raíz del proyecto
./e2e/run-e2e-tests.sh

# Opciones útiles:
./e2e/run-e2e-tests.sh --start-from 05          # Empezar desde test 05
./e2e/run-e2e-tests.sh --skip-build              # Saltar build (usar imágenes existentes)
./e2e/run-e2e-tests.sh --cleanup                 # Limpiar jobs después de ejecución
./e2e/run-e2e-tests.sh --timeout 1800            # Timeout de 30 minutos por test
./e2e/run-e2e-tests.sh --workspace-only          # Ejecutar solo tests workspace (14-43)
./e2e/run-e2e-tests.sh --workspace-only --tier smoke
./e2e/run-e2e-tests.sh --workspace17-remote      # Ejecutar también 17R (variante remota)
./e2e/run-e2e-tests.sh --no-minio-evidence       # Desactivar upload de evidence a MinIO
./e2e/run-e2e-tests.sh --minio-evidence-prefix e2e/workspace/nightly
```

El script:
- ✅ Ejecuta tests secuencialmente (01-43)
- ✅ Espera a que cada test termine antes de continuar
- ✅ Maneja tests asíncronos (como el 05) monitoreando logs
- ✅ Extrae evidence JSON de tests workspace y la guarda localmente en `e2e/evidence/`
- ✅ Puede subir evidence a MinIO (`swe-workspaces-meta`) de forma best-effort
- ✅ Muestra resumen final con estadísticas
- ✅ Detiene ejecución si un test falla

Catálogo declarativo workspace:
- `e2e/tests/workspace_tests.yaml` define `id`, `name`, `job_name`, `requires_ephemeral_deps`, `tier`, `kind`, `timeout_override`, `tags`.

**Ver**: [E2E Test Runner Improvements](E2E_TEST_RUNNER_IMPROVEMENTS.md) para más detalles y mejoras propuestas.

### Desde el Directorio del Test

Para ejecutar un test individual:

```bash
cd e2e/tests/01-planning-ui-get-node-relations

# Build
make build

# Deploy
make deploy

# Ver logs
make logs

# Ver status
make status

# Limpiar
make delete
```

### Desde la Raíz del Proyecto

```bash
# Build
cd e2e/tests/01-planning-ui-get-node-relations && make build

# Deploy
kubectl apply -f e2e/tests/01-planning-ui-get-node-relations/job.yaml

# Ver logs
kubectl logs -n swe-ai-fleet -l app=e2e-planning-ui-get-node-relations -f
```

## Prerrequisitos

- Kubernetes cluster con servicios desplegados
- Acceso al namespace `swe-ai-fleet`
- Docker/Podman para construir imágenes
- kubectl configurado
- Acceso al registry de imágenes

## Convenciones

- **Numeración**: Tests numerados secuencialmente (01, 02, 03, ...)
- **Nombres**: Descriptivos y en kebab-case
- **Estructura**: Cada test en su propio directorio con todos los archivos necesarios
- **Documentación**: Cada test debe tener su propio README.md

## Troubleshooting

Ver [PROCEDURE.md](PROCEDURE.md#troubleshooting) para troubleshooting detallado.

### Problemas Comunes

1. **Test falla con "Connection refused"**
   - Verifica que los servicios estén desplegados
   - Verifica DNS interno del cluster

2. **Test falla con "Node not found"**
   - Verifica que los datos de prueba existan en Neo4j
   - Crea datos de prueba si es necesario

3. **ImagePullBackOff**
   - Verifica que la imagen esté en el registry
   - Rebuild y push: `make build-push`

4. **Backlog Review Processor / BRP logs: "Missing required EventEnvelope field: 'event_type'"**
   - Los consumers esperan mensajes en **EventEnvelope** (event_type, payload, idempotency_key, etc.).
   - Si hay mensajes antiguos en el stream (publicados antes del cambio de formato), purgar el stream AGENT_RESPONSES y redesplegar el publicador (Ray workers) con la versión que envuelve en EventEnvelope.
   - Ver: [Purge AGENT_RESPONSES only](../../deploy/k8s/20-streams/README.md#purge-agent_responses-only-clear-old-messages).

### Vaciar streams NATS con el CLI (interactivo)

Para inspeccionar o vaciar mensajes de los streams NATS desde dentro del cluster (por ejemplo antes o después de una batería E2E):

**1. Crear un pod temporal con el cliente NATS (nats-box):**

```bash
kubectl run nats-cli -n swe-ai-fleet --rm -it --restart=Never \
  --image=docker.io/natsio/nats-box:latest -- sleep 3600
```

**2. En otra terminal, abrir shell en el pod:**

```bash
kubectl exec -it nats-cli -n swe-ai-fleet -- /bin/sh
```

**3. Dentro del pod:**

```bash
export NATS_SERVER="nats://nats.swe-ai-fleet.svc.cluster.local:4222"

# Ver streams y cantidad de mensajes
nats stream ls --server "$NATS_SERVER"

# Vaciar un stream (solo mensajes; el stream sigue existiendo)
nats stream purge AGENT_RESPONSES -f --server "$NATS_SERVER"

# Vaciar los streams que suelen tener datos (dejar todo a 0)
nats stream purge AGENT_RESPONSES -f --server "$NATS_SERVER"
nats stream purge CONTEXT -f --server "$NATS_SERVER"
nats stream purge PLANNING_EVENTS -f --server "$NATS_SERVER"

# Comprobar
nats stream ls --server "$NATS_SERVER"
```

**4. Salir:** `exit`. Si usaste `--rm`, el pod se borra solo; si no: `kubectl delete pod nats-cli -n swe-ai-fleet`.

Más opciones (job de purge, borrar streams por completo): [20-streams README](../../deploy/k8s/20-streams/README.md).

## Referencias

- [Procedimiento Detallado](PROCEDURE.md) - Guía completa para crear tests E2E
- [E2E Test Runner Improvements](E2E_TEST_RUNNER_IMPROVEMENTS.md) - Mejoras implementadas y propuestas
- [Workspace E2E Maintenance Plan](WORKSPACE_E2E_MAINTENANCE_PLAN.md) - Plan de mantenibilidad para suite workspace
- [Backlog Review Flow](../../services/backlog_review_processor/BACKLOG_REVIEW_FLOW_NO_STYLES.md) - Diagrama de flujo arquitectónico

---

**Última actualización**: 2026-02-22
**Mantenido por**: Equipo de Desarrollo SWE AI Fleet
