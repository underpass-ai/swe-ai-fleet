# Plan: E2E Tests Con Agentes Reales (vLLM)

## 🎯 Objetivo

E2E tests deben usar agentes REALES con vLLM, no mocks.

**Razón**: E2E debe probar el sistema completo en entorno real.

---

## ✅ Cambios Realizados

### 1. Proto actualizado (orchestrator.proto)

```protobuf
message CouncilConfig {
  int32 deliberation_rounds = 1;
  bool enable_peer_review = 2;
  string model_profile = 3;
  map<string, string> custom_params = 4;
  string agent_type = 5;  // "MOCK", "VLLM", "RAY_VLLM" ✅ NUEVO
}
```

### 2. Orchestrator server.py actualizado

```python
# Por defecto: RAY_VLLM (agentes reales)
requested_agent_type = config.agent_type if (config and config.agent_type) else "RAY_VLLM"

# Map string to AgentType enum
agent_type_map = {
    "MOCK": AgentType.MOCK,      # Solo para unit tests
    "VLLM": AgentType.VLLM,      # vLLM directo
    "RAY_VLLM": AgentType.VLLM,  # vLLM via Ray (E2E)
}
agent_type = agent_type_map.get(requested_agent_type, AgentType.VLLM)
```

**Comportamiento**:
- Sin especificar `agent_type`: usa `RAY_VLLM` (real)
- `agent_type="MOCK"`: usa MockAgent (unit tests)
- `agent_type="RAY_VLLM"`: usa vLLM (E2E)

### 3. setup_all_councils.py actualizado

```python
response = stub.CreateCouncil(orchestrator_pb2.CreateCouncilRequest(
    role=role,
    num_agents=3,
    config=orchestrator_pb2.CouncilConfig(
        deliberation_rounds=1,
        enable_peer_review=False,
        agent_type="RAY_VLLM"  # ✅ EXPLÍCITO para E2E
    )
))
```

---

## 🔄 Próximos Pasos

### Paso 1: Verificar vLLM esté corriendo

```bash
kubectl get pods -n swe-ai-fleet -l app=vllm-server
# Debe estar Running

kubectl logs -n swe-ai-fleet deployment/vllm-server --tail=10
# Verificar que esté listo
```

### Paso 2: Limpiar councils existentes (mocks)

```bash
# Eliminar councils viejos con MockAgents
kubectl port-forward -n swe-ai-fleet svc/orchestrator 50055:50055 &

# Eliminar councils (si el Orchestrator lo soporta)
# O reiniciar Orchestrator para limpiar estado en memoria
kubectl rollout restart -n swe-ai-fleet deployment/orchestrator
```

### Paso 3: Crear councils con agentes reales

```bash
python tests/e2e/setup_all_councils.py
# Ahora creará councils con RAY_VLLM
```

### Paso 4: Ejecutar E2E tests

```bash
python tests/e2e/test_ray_vllm_with_tools_e2e.py
# Tardará 15-45s (vLLM real)
# duration > 0ms ✅
```

### Paso 5: Verificar logs de vLLM

```bash
kubectl logs -f -n swe-ai-fleet deployment/vllm-server
# Debe mostrar:
# POST /v1/chat/completions
# (cada vez que un agente piensa)
```

---

## 📊 Comparación Esperada

### Antes (MockAgent)

```
Test 1: ARCHITECT Code Analysis
   Duration: 0.0s ❌ Mock
   vLLM logs: (vacío)
   Propuestas: Sintéticas (patrón hardcodeado)
```

### Después (RAY_VLLM)

```
Test 1: ARCHITECT Code Analysis
   Duration: 15-45s ✅ Real
   vLLM logs: POST /v1/chat/completions (9 requests)
   Propuestas: Reales (LLM genera)
   Tools ejecutados: files.list_files, files.read_file, etc
```

---

## 🎯 Tests Afectados

Todos los E2E deben usar agentes reales:

1. `test_ray_vllm_with_tools_e2e.py` ✅
2. `test_architect_analysis_e2e.py` ✅
3. `test_orchestrator_cluster.py` (si existe)
4. `test_vllm_orchestrator.py` (si existe)

---

## ⚠️ Consideraciones

### Tiempos de ejecución

- **Antes**: 0.0s (mocks instantáneos)
- **Después**: 15-45s por deliberación (vLLM real)
- **CI/CD**: Los E2E solo corren en `main` (no en PRs)

### Costos

- **Antes**: $0 (mocks gratis)
- **Después**: ~$0.04 por agente (vLLM en cluster propio, no API externa)

### Dependencias

- ✅ vLLM server debe estar corriendo
- ✅ Ray cluster debe estar inicializado
- ✅ Hugging Face token configurado (Secret)
- ✅ Workspace disponible para agents

---

## 🧪 Validación

### Cómo saber si está usando vLLM real

1. **Timing**: `duration > 0ms` (típicamente 5-30s)
2. **Logs vLLM**: `POST /v1/chat/completions` aparece
3. **Propuestas**: Contenido varía entre ejecuciones (no determinista)
4. **Tools**: Operaciones reales ejecutadas (files, git, etc)

### Cómo forzar uso de mocks (si necesario)

```python
# Para tests que DEBEN ser rápidos
response = stub.CreateCouncil(orchestrator_pb2.CreateCouncilRequest(
    role=role,
    num_agents=3,
    config=orchestrator_pb2.CouncilConfig(
        agent_type="MOCK"  # Explícito
    )
))
```

---

## 📝 Documentación a Actualizar

1. `CLUSTER_EXECUTION_EVIDENCE.md`: Cambiar "MockAgent" a "vLLM real"
2. `MOCK_VS_REAL_AGENTS.md`: Aclarar que E2E usa real por defecto
3. `tests/e2e/README.md`: Documentar timing esperado (15-45s)

---

## ✅ Checklist Final

- [x] Proto actualizado con `agent_type` field
- [x] Protobuf regenerado
- [x] Orchestrator usa `RAY_VLLM` por defecto
- [x] `setup_all_councils.py` especifica `RAY_VLLM`
- [ ] Limpiar councils existentes (mocks)
- [ ] Recrear councils con vLLM
- [ ] Ejecutar E2E y verificar timing > 0ms
- [ ] Verificar logs de vLLM muestran requests
- [ ] Actualizar documentación

---

**Status**: 🟡 **IN PROGRESS** - Código listo, pendiente recrear councils y ejecutar tests

