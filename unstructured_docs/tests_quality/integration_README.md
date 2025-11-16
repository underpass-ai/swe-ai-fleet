# Integration Tests

## 🎯 Propósito

Tests de integración que requieren **servicios reales corriendo en Docker/Podman**.

## 📋 Qué son Integration Tests

Tests que validan la integración entre componentes con servicios reales:
- ✅ Neo4j, Redis, NATS corriendo en containers
- ✅ Servicios reales (no mocks)
- ✅ Más lentos que unit tests (10s-60s)
- ✅ Requieren Docker/Podman

## 🚀 Ejecución Rápida

### Opción 1: Script Automático (Recomendado)

```bash
# Levanta servicios, ejecuta tests, limpia
./tests/integration/run-integration-tests.sh
```

### Opción 2: Manual

```bash
# 1. Levantar servicios
podman-compose -f tests/integration/docker-compose.integration.yml up -d

# 2. Esperar a que estén ready (30s aprox)
sleep 30

# 3. Ejecutar tests
pytest tests/integration -m integration

# 4. Limpiar
podman-compose -f tests/integration/docker-compose.integration.yml down -v
```

## 📦 Servicios Incluidos

### Neo4j (Graph Database)
- **Puerto**: 7687 (Bolt), 7474 (HTTP)
- **Auth**: neo4j/testpassword
- **Plugins**: APOC
- **Uso**: Context Service persistence

### Redis (Key-Value Store)
- **Puerto**: 6379
- **Persistencia**: AOF enabled
- **Uso**: Caching, session storage

### NATS JetStream (Message Broker)
- **Puerto**: 4222 (client), 8222 (monitoring)
- **Modo**: JetStream enabled
- **Uso**: Async messaging entre servicios

## 🧪 Tests Actuales

### Orchestrator
- `orchestrator/test_vllm_agent_e2e.py` - Requiere vLLM + NATS
- `services/orchestrator/test_grpc_integration.py` - Usa testcontainers
- `services/orchestrator/test_grpc_simple_e2e.py` - Requiere servicio real

### Context Service
- `services/context/test_persistence_integration.py` - Requiere Neo4j + Redis

## ⚙️ Configuración

### Variables de Entorno

El script `run-integration-tests.sh` configura automáticamente:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=testpassword
REDIS_HOST=localhost
REDIS_PORT=6379
NATS_URL=nats://localhost:4222
```

### Personalizar

Puedes sobrescribir antes de ejecutar tests:

```bash
export NEO4J_PASSWORD=mypassword
pytest tests/integration -m integration
```

## 🔧 Troubleshooting

### Error: "Neo4j not available"

```bash
# Verificar que Neo4j está corriendo
podman ps | grep neo4j

# Ver logs
podman logs neo4j-integration-test

# Verificar conexión
podman exec -it neo4j-integration-test cypher-shell -u neo4j -p testpassword
```

### Error: "Redis not available"

```bash
# Verificar Redis
podman ps | grep redis

# Test conexión
podman exec -it redis-integration-test redis-cli ping
```

### Error: "Port already in use"

```bash
# Limpiar servicios previos
podman-compose -f tests/integration/docker-compose.integration.yml down -v

# Verificar puertos libres
ss -tlnp | grep -E ":(6379|7687|4222)"
```

### Tests muy lentos

```bash
# Ejecutar solo un test específico
pytest tests/integration/orchestrator/test_vllm_agent_e2e.py::test_specific -v

# Ejecutar con menos verbosidad
pytest tests/integration -m integration -q
```

## 📊 Diferencia con Otros Tests

| Aspecto | Unit Tests | Integration Tests (aquí) | E2E Tests |
|---------|------------|--------------------------|-----------|
| **Servicios** | ❌ Mocks | ✅ Docker/Podman | ✅ Cluster K8s |
| **Velocidad** | ⚡ <1s | 🐢 10-60s | 🐌 30s-5min |
| **Setup** | Ninguno | Docker compose | kubectl port-forward |
| **CI** | ✅ Siempre | ⚠️ Solo en main | ❌ Manual |
| **Marca pytest** | (default) | `@pytest.mark.integration` | `@pytest.mark.e2e` |

## 📚 Ver También

- `tests/unit/` - Tests unitarios con mocks
- `tests/e2e/` - Tests contra cluster Kubernetes real
- `TESTING_LEVELS.md` - Documentación completa de niveles de testing
- `INTEGRATION_TESTS_AUDIT.md` - Auditoría de clasificación de tests

## 🎯 Cuándo Añadir Tests Aquí

✅ **SÍ añadir**:
- Tests que requieren Neo4j, Redis, NATS, etc.
- Tests que validan persistencia real
- Tests que validan integración entre servicios
- Tests con testcontainers

❌ **NO añadir**:
- Tests con mocks → van a `tests/unit/`
- Tests contra cluster K8s → van a `tests/e2e/`

