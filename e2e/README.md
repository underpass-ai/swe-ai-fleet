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

Para ejecutar todos los tests E2E de forma secuencial (01-06), usa el script runner:

```bash
# Desde la raíz del proyecto
./e2e/run-e2e-tests.sh

# Opciones útiles:
./e2e/run-e2e-tests.sh --start-from 05          # Empezar desde test 05
./e2e/run-e2e-tests.sh --skip-build              # Saltar build (usar imágenes existentes)
./e2e/run-e2e-tests.sh --cleanup                 # Limpiar jobs después de ejecución
./e2e/run-e2e-tests.sh --timeout 1800            # Timeout de 30 minutos por test
```

El script:
- ✅ Ejecuta tests secuencialmente (01-06)
- ✅ Espera a que cada test termine antes de continuar
- ✅ Maneja tests asíncronos (como el 05) monitoreando logs
- ✅ Muestra resumen final con estadísticas
- ✅ Detiene ejecución si un test falla

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
- [Backlog Review Flow](../../services/backlog_review_processor/BACKLOG_REVIEW_FLOW_NO_STYLES.md) - Diagrama de flujo arquitectónico

---

**Última actualización**: 2025-01-XX
**Mantenido por**: Equipo de Desarrollo SWE AI Fleet
