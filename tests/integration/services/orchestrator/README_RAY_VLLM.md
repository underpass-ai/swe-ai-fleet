# E2E Tests con Ray + vLLM

## Overview

Tests end-to-end para validar la integración completa de Ray + vLLM con el Orchestrator Service.

---

## 🏗️ Arquitectura de Testing

```
┌─────────────────────────────────────────────────────────┐
│  Docker Compose Environment                              │
│                                                          │
│  ┌────────────┐   ┌──────────┐   ┌────────────────┐   │
│  │ Ray Head   │   │  vLLM    │   │ Orchestrator   │   │
│  │ (mini      │   │  Server  │   │ Service        │   │
│  │  cluster)  │   │          │   │                │   │
│  │            │   │  Tiny    │   │  - Deliberate  │   │
│  │  Port:     │   │  Llama   │   │  - GetResult   │   │
│  │  10001     │   │  1.1B    │   │                │   │
│  └────────────┘   └──────────┘   └────────────────┘   │
│         │              │                  │             │
│         └──────────────┴──────────────────┘             │
│                        │                                │
│                   ┌────┴─────┐                         │
│                   │   NATS   │                         │
│                   │ JetStream│                         │
│                   └──────────┘                         │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  E2E Tests Container                           │    │
│  │  - test_deliberate_e2e.py                      │    │
│  │  - test_orchestrate_e2e.py                     │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Ejecutar Tests

### Opción 1: Script Automático (Recomendado)
```bash
cd tests/integration/services/orchestrator
bash run-e2e-ray-vllm.sh
```

**Duración**: ~3-4 minutos
- Ray head: ~30s
- vLLM model download/load: ~90s
- Orchestrator: ~30s
- Tests: ~30-60s

### Opción 2: Manual (Para Debugging)

#### 1. Start services
```bash
cd tests/integration/services/orchestrator

# Cleanup previous
podman-compose -f docker-compose.ray-vllm.yml down -v

# Build
podman-compose -f docker-compose.ray-vllm.yml build

# Start infrastructure
podman-compose -f docker-compose.ray-vllm.yml up -d ray-head nats redis

# Wait for Ray
podman exec orchestrator-e2e-ray-head ray status

# Start vLLM (takes ~90s)
podman-compose -f docker-compose.ray-vllm.yml up -d vllm

# Wait for vLLM
curl http://localhost:28000/health

# Start Orchestrator
podman-compose -f docker-compose.ray-vllm.yml up -d orchestrator

# Check all healthy
podman ps --filter "name=orchestrator-e2e"
```

#### 2. Run tests
```bash
podman-compose -f docker-compose.ray-vllm.yml run --rm tests
```

#### 3. Cleanup
```bash
podman-compose -f docker-compose.ray-vllm.yml down -v
```

---

## 🧪 Tests Incluidos

### test_deliberate_e2e.py
- `test_deliberate_basic` - Deliberación básica con 3 agents
- `test_deliberate_multiple_rounds` - Múltiples rondas
- `test_deliberate_different_roles` - DEV, QA, ARCHITECT
- `test_deliberate_empty_task` - Edge case
- `test_deliberate_invalid_role` - Error handling
- `test_deliberate_with_constraints` - Constraints complejos

### test_orchestrate_e2e.py
- `test_orchestrate_basic` - Workflow completo
- `test_orchestrate_with_context` - Integración Context Service
- `test_orchestrate_with_options` - Opciones de orchestration
- `test_orchestrate_multiple_roles` - Múltiples roles
- `test_orchestrate_error_handling` - Manejo de errores

---

## 🐛 Troubleshooting

### vLLM tarda mucho en iniciar
**Normal**: Primera vez descarga el modelo (~500MB)

**Solución**: Esperar pacientemente o usar modelo más pequeño

```yaml
# En docker-compose.ray-vllm.yml, cambiar:
command: >
  --model facebook/opt-125m  # Más pequeño, más rápido
```

### Ray no se conecta
**Check logs**:
```bash
podman logs orchestrator-e2e-ray-head
```

**Solución común**: Esperar más tiempo (start_period)

### Orchestrator falla al importar Ray
**Check**: Ray debe estar en requirements.txt

**Verify**:
```bash
podman exec orchestrator-e2e-service python -c "import ray; print(ray.__version__)"
```

### Tests timeout
**Incrementar timeout** en docker-compose:
```yaml
healthcheck:
  start_period: 120s  # Más tiempo para vLLM
```

---

## 📊 Recursos Requeridos

### Mínimos (sin GPU)
- CPU: 4 cores
- RAM: 8GB
- Disk: 5GB (para modelo TinyLlama)
- Tiempo: ~3-4 minutos

### Recomendados
- CPU: 8 cores
- RAM: 16GB
- Disk: 10GB
- GPU: Opcional (acelera vLLM 10x)

---

## 🔧 Configuración

### Variables de Entorno
```bash
# Opcional: Hugging Face token para modelos privados
export HF_TOKEN="hf_..."

# Ejecutar tests
bash run-e2e-ray-vllm.sh
```

### Puertos Usados
```
26379  - Ray GCS
28265  - Ray Dashboard
28000  - vLLM API
24222  - NATS
50055  - Orchestrator gRPC
```

---

## ✅ Expected Output

```
🧪 Orchestrator E2E Tests with Ray + vLLM
==========================================

🧹 Cleaning up previous containers...
🏗️  Building containers...
🚀 Starting infrastructure services...
✅ Ray head ready
✅ vLLM server ready
✅ Orchestrator ready

🔌 Testing connectivity...
  Ray (26379): ✅
  vLLM (28000): ✅
  NATS (24222): ✅
  Orchestrator (50055): ✅

🧪 Running E2E tests with Ray + vLLM...
==============================

collected 14 items

test_deliberate_e2e.py::test_deliberate_basic PASSED
test_deliberate_e2e.py::test_deliberate_multiple_rounds PASSED
test_deliberate_e2e.py::test_deliberate_different_roles PASSED
...

✅ All tests passed!
```

---

## 📝 Notas

- **vLLM en CPU**: Tests E2E usan CPU (sin GPU), es más lento pero funciona
- **TinyLlama**: Modelo pequeño (1.1B) para tests rápidos
- **Ray mini cluster**: Solo head + 1 worker para E2E
- **Cleanup automático**: Containers se eliminan después de tests

---

**Próximo paso**: Ejecutar `bash run-e2e-ray-vllm.sh` 🚀

