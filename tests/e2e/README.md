# End-to-End Tests (E2E)

## 🎯 Propósito

Tests E2E ejecutados **contra el cluster Kubernetes REAL** en producción.

## ⚠️ Importante

**NO usar Docker/Podman aquí**. Los tests E2E deben conectarse al cluster real mediante:
- `kubectl port-forward`
- Servicios expuestos vía Ingress (*.underpassai.com)
- Configuración con KUBECONFIG

## 📋 Diferencia con Integration Tests

| Aspecto | Integration Tests | E2E Tests (aquí) |
|---------|-------------------|------------------|
| **Entorno** | Docker/Podman | Cluster Kubernetes real |
| **Servicios** | Containers locales | Producción (namespace swe-ai-fleet) |
| **GPUs** | No (CPU only) | Sí (RTX 3090 reales) |
| **Ray** | Local mode | Cluster real (ray namespace) |
| **vLLM** | CPU mode | GPU mode con modelos reales |
| **Datos** | Mock/test data | Datos de producción |
| **Cuándo** | Después de merge a main | Manual o scheduled |

## 🚀 Estructura Esperada

```
tests/e2e/
├── README.md (este archivo)
├── conftest.py           # Fixtures para conectar al cluster
├── test_orchestrator_cluster.py
├── test_context_cluster.py
└── test_complete_workflow_cluster.py
```

## 📝 Ejemplo de Test E2E

```python
import grpc
import pytest

@pytest.mark.e2e
def test_orchestrator_in_production():
    """Test Orchestrator service in production cluster."""
    # Connect via kubectl port-forward or ingress
    channel = grpc.insecure_channel("localhost:50055")  # port-forwarded
    stub = OrchestratorServiceStub(channel)
    
    # Call real service in cluster
    response = stub.CreateCouncil(...)
    assert response.council_id
```

## 🔧 Setup

### Prerequisitos
- Acceso al cluster Kubernetes
- KUBECONFIG configurado
- `kubectl` instalado

### Ejecutar Tests

```bash
# 1. Port-forward al servicio
kubectl port-forward -n swe-ai-fleet svc/orchestrator 50055:50055 &

# 2. Ejecutar tests E2E
pytest tests/e2e -m e2e

# 3. Cleanup
pkill -f "kubectl port-forward"
```

### Alternativa: Sin Port-Forward

Si los servicios están expuestos vía Ingress:

```bash
# Tests se conectan directamente a *.underpassai.com
export ORCHESTRATOR_URL="https://orchestrator.underpassai.com"
pytest tests/e2e -m e2e
```

## ⏱️ Características

- **Lentos**: 30s-5min por test (servicios reales)
- **Costosos**: Usan GPUs y recursos reales
- **Críticos**: Validan que producción funciona
- **Manuales**: No se ejecutan en PRs automáticamente

## 🎯 Cuándo Añadir Tests Aquí

✅ **SÍ añadir**:
- Tests que validan integración completa en producción
- Tests que requieren GPUs reales
- Tests que validan Ray cluster real
- Tests de performance/carga contra cluster

❌ **NO añadir**:
- Tests con Docker/Podman → van a `tests/integration/`
- Tests con mocks → van a `tests/unit/`
- Tests rápidos (<10s) → probablemente unit o integration

## 📚 Ver También

- `tests/integration/` - Tests con Docker/Podman
- `tests/unit/` - Tests con mocks
- `TESTING_LEVELS.md` - Documentación completa de niveles de testing

---

**Estado actual**: Carpeta vacía, preparada para futuros tests contra cluster K8s real.

