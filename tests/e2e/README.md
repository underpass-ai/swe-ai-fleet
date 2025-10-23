# End-to-End Tests (E2E)

## 🎯 Propósito

Tests E2E ejecutados **contra el cluster Kubernetes REAL** en producción.

## ⚠️ IMPORTANTE: Tests E2E se ejecutan DENTRO del cluster

**Los tests E2E DEBEN ejecutarse como Jobs de Kubernetes**, no desde tu máquina local.

**Razón**: 
- Los tests necesitan acceder a servicios internos del cluster (`*.swe-ai-fleet.svc.cluster.local`)
- No requieren port-forward ni configuración de red
- Los protos se generan durante el build de la imagen Docker
- Ejecución aislada y reproducible

## 📋 Diferencia con Integration Tests

| Aspecto | Integration Tests | E2E Tests (aquí) |
|---------|-------------------|------------------|
| **Entorno** | Docker/Podman | Cluster Kubernetes real |
| **Servicios** | Containers locales | Producción (namespace swe-ai-fleet) |
| **GPUs** | No (CPU only) | Sí (RTX 3090 reales) |
| **Ray** | Local mode | Cluster real (ray namespace) |
| **vLLM** | CPU mode | GPU mode con modelos reales |
| **Datos** | Mock/test data | Datos de producción |
| **Ejecución** | Desde tu máquina | **Job en Kubernetes** |

## 🚀 Cómo Ejecutar Tests E2E

### Opción 1: Ejecutar test específico (Recomendado)

```bash
# Ejecutar test de arquitectura
make test-e2e-architecture

# O manualmente:
kubectl delete job test-architecture-e2e -n swe-ai-fleet 2>/dev/null || true
kubectl apply -f deploy/k8s/99-test-architecture-e2e.yaml
kubectl wait --for=condition=complete --timeout=180s job/test-architecture-e2e -n swe-ai-fleet
kubectl logs -n swe-ai-fleet job/test-architecture-e2e
```

### Opción 2: Ejecutar todos los tests E2E

```bash
# Ejecutar todos los tests E2E via Jobs
./scripts/test/e2e.sh
```

## 📝 Anatomía de un Test E2E

### 1. Test Python (`tests/e2e/test_*.py`)

```python
@pytest.mark.e2e
def test_full_architecture_deliberation():
    """Test que verifica arquitectura completa."""
    import os
    from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc
    
    # Conectar a servicio interno (DNS del cluster)
    host = os.getenv("ORCHESTRATOR_HOST", "orchestrator.swe-ai-fleet.svc.cluster.local")
    channel = grpc.insecure_channel(f"{host}:50055")
    
    # ... test logic ...
```

### 2. Dockerfile (`tests/e2e/Dockerfile.{test-name}`)

```dockerfile
FROM python:3.13-slim

# Instalar dependencias
RUN pip install --no-cache-dir -e ".[grpc,dev]"

# Copiar specs y GENERAR protos durante build
COPY specs/ /workspace/specs/
RUN python -m grpc_tools.protoc \
    --python_out=services/orchestrator/gen \
    --grpc_python_out=services/orchestrator/gen \
    --proto_path=specs/fleet/orchestrator/v1 \
    specs/fleet/orchestrator/v1/orchestrator.proto

# Copiar test
COPY tests/e2e/test_*.py /workspace/tests/e2e/

# Ejecutar test
CMD ["pytest", "tests/e2e/test_*.py", "-v", "-s"]
```

### 3. Kubernetes Job (`deploy/k8s/99-test-*.yaml`)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: test-{name}-e2e
  namespace: swe-ai-fleet
spec:
  ttlSecondsAfterFinished: 600  # Auto-delete
  template:
    spec:
      containers:
      - name: test-runner
        image: registry.underpassai.com/swe-ai-fleet/{test-name}:latest
        env:
        - name: ORCHESTRATOR_HOST
          value: "orchestrator.swe-ai-fleet.svc.cluster.local"
```

## 📚 Tests E2E Disponibles

| Test | Archivo | Job | Descripción |
|------|---------|-----|-------------|
| **Arquitectura** | `test_architecture_e2e.py` | `99-test-architecture-e2e.yaml` | Verifica flujo completo con vLLM |

## 🔧 Crear un Nuevo Test E2E

### Paso 1: Crear test Python

```bash
# tests/e2e/test_my_feature_e2e.py
@pytest.mark.e2e
def test_my_feature():
    # Test conectándose a servicios internos del cluster
    pass
```

### Paso 2: Crear Dockerfile

```bash
# tests/e2e/Dockerfile.my-feature-test
FROM python:3.13-slim
# ... (ver ejemplo arriba)
```

### Paso 3: Crear Job YAML

```bash
# deploy/k8s/99-test-my-feature-e2e.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: test-my-feature-e2e
  namespace: swe-ai-fleet
# ... (ver ejemplo arriba)
```

### Paso 4: Build y Push

```bash
podman build -f tests/e2e/Dockerfile.my-feature-test \
  -t registry.underpassai.com/swe-ai-fleet/my-feature-test:latest .
podman push registry.underpassai.com/swe-ai-fleet/my-feature-test:latest
```

### Paso 5: Ejecutar

```bash
kubectl delete job test-my-feature-e2e -n swe-ai-fleet 2>/dev/null || true
kubectl apply -f deploy/k8s/99-test-my-feature-e2e.yaml
kubectl logs -n swe-ai-fleet job/test-my-feature-e2e -f
```

## ⏱️ Características

- **Lentos**: 30s-5min por test (servicios reales con vLLM)
- **Costosos**: Usan GPUs y recursos reales
- **Críticos**: Validan que producción funciona
- **Automatizados**: Se ejecutan via Jobs, no manual

## 🎯 Cuándo Añadir Tests Aquí

✅ **SÍ añadir**:
- Tests que validan integración completa en producción
- Tests que requieren GPUs reales (vLLM deliberations)
- Tests que validan Ray cluster real
- Tests de performance/carga contra cluster

❌ **NO añadir**:
- Tests con Docker/Podman → van a `tests/integration/`
- Tests con mocks → van a `tests/unit/`
- Tests rápidos (<10s) → probablemente unit o integration
- Tests desde tu máquina local → **NO FUNCIONARÁN**

## 🐛 Troubleshooting

### Error: "Cannot connect to orchestrator"

**Causa**: Intentaste ejecutar el test desde tu máquina local

**Solución**: Ejecuta el test via Job de Kubernetes (ver arriba)

### Error: "No module named 'services.orchestrator.gen'"

**Causa**: Los protos no se generaron durante el build

**Solución**: Verifica que el Dockerfile tenga el paso `RUN python -m grpc_tools.protoc...`

### Job no completa después de 3 minutos

**Causa**: Deliberación con vLLM toma tiempo (esperado 30-90s)

**Solución**: Aumenta timeout del Job o espera más tiempo

```bash
# Ver logs en tiempo real
kubectl logs -n swe-ai-fleet job/test-architecture-e2e -f

# Ver estado del pod
kubectl get pods -n swe-ai-fleet -l component=architecture-e2e
```

## 📚 Ver También

- `tests/integration/` - Tests con Docker/Podman
- `tests/unit/` - Tests con mocks
- `docs/TESTING_ARCHITECTURE.md` - Documentación completa de testing
- `docs/operations/DEPLOYMENT.md` - Procedimientos de deployment

---

**Estado**: Tests E2E ejecutándose via Jobs de Kubernetes desde build del cluster
