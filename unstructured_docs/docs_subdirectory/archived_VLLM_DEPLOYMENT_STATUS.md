# vLLM Deployment Status

## ✅ Deployment Completado

### 1. vLLM Server
- **Estado**: Running (1/1)
- **Modelo**: Qwen/Qwen3-0.6B
- **GPU**: 1x nvidia.com/gpu (time-sliced across 4x RTX 3090)
- **Memoria**: 8Gi request, 16Gi limit
- **CPU**: 2 cores request, 4 cores limit
- **Service**: `vllm-server-service.swe-ai-fleet.svc.cluster.local:8000`
- **Health**: ✓ Passing (200 OK)

### 2. Orchestrator Service
- **Estado**: Running (2/2 replicas)
- **Configuración**:
  - `AGENT_TYPE=vllm`
  - `VLLM_URL=http://vllm-server-service:8000`
  - `VLLM_MODEL=Qwen/Qwen3-0.6B`
- **NATS**: ✓ Connected
- **Consumers**: ✓ All started

### 3. Configuración
- **Hugging Face Token**: ✓ Configured (secret: `huggingface-token`)
- **Storage**: ✓ PVC created (50Gi, local-path)
- **Namespace**: swe-ai-fleet
- **Registry**: registry.underpassai.com

### 4. Ray Cluster (Scaled Down)
- **Workers**: 4 (down from 8 to free GPUs for vLLM)
- **Head**: 1
- **GPUs**: 5/8 in use

## 🧪 Siguientes Pasos

### E2E Tests con vLLM
1. Crear councils con vLLM agents
2. Ejecutar deliberation con LLM real
3. Ejecutar orchestration completa
4. Validar responses y calidad

### Comandos de Prueba

#### Test de vLLM API directamente
```bash
kubectl run -n swe-ai-fleet test-vllm --image=curlimages/curl:latest --rm -it --restart=Never -- \
  curl -X POST http://vllm-server-service:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen3-0.6B", "prompt": "Write a Python function to", "max_tokens": 50}'
```

#### Test de Orchestrator gRPC
```bash
# Port-forward
kubectl port-forward -n swe-ai-fleet svc/orchestrator 50055:50055

# Desde otro terminal, ejecutar E2E tests
cd tests/e2e/services/orchestrator
pytest test_deliberate_e2e.py -v
```

## 📊 Recursos Utilizados

| Servicio      | CPU Request | CPU Limit | Memory Request | Memory Limit | GPU |
|---------------|-------------|-----------|----------------|--------------|-----|
| vLLM Server   | 2 cores     | 4 cores   | 8Gi            | 16Gi         | 1   |
| Orchestrator  | 500m        | 2 cores   | 1Gi            | 2Gi          | 0   |
| Ray (scaled)  | 15 cores    | 60 cores  | 280Gi          | 320Gi        | 5   |
| **Total**     | ~17.5 cores | ~66 cores | ~289Gi         | ~338Gi       | 6/8 |

## 🔧 Troubleshooting

### Ver logs de vLLM
```bash
kubectl logs -n swe-ai-fleet -l app=vllm-server --tail=100 -f
```

### Ver logs de Orchestrator
```bash
kubectl logs -n swe-ai-fleet -l app=orchestrator --tail=100 -f
```

### Verificar health de vLLM
```bash
kubectl exec -n swe-ai-fleet -it $(kubectl get pod -n swe-ai-fleet -l app=vllm-server -o name | head -1) -- \
  curl http://localhost:8000/health
```

### Reiniciar vLLM
```bash
kubectl rollout restart deployment vllm-server -n swe-ai-fleet
```

### Escalar Ray workers
```bash
# Volver a 8 workers
kubectl patch raycluster ray-gpu -n ray --type='merge' -p='{"spec":{"workerGroupSpecs":[{"replicas":8}]}}'

# O reducir a 4 workers
kubectl patch raycluster ray-gpu -n ray --type='merge' -p='{"spec":{"workerGroupSpecs":[{"replicas":4}]}}'
```

## ✅ Checklist de Deployment

- [x] GPU operator configurado y funcionando
- [x] KuberRay instalado
- [x] vLLM server deployado y healthy
- [x] Hugging Face token configurado
- [x] Modelo Qwen3-0.6B cargado
- [x] Service vLLM accessible en cluster
- [x] Orchestrator Service actualizado con variables de vLLM
- [x] Orchestrator conectado a NATS
- [ ] E2E tests ejecutados con vLLM agents
- [ ] Validación de calidad de respuestas LLM
- [ ] Performance testing

## 📝 Notas

- **Modelo seleccionado**: Qwen3-0.6B es un modelo pequeño (~600M parámetros) ideal para testing
- **Time-slicing**: Configurado para usar las 4 GPUs simultáneamente con `VLLM_TENSOR_PARALLEL_SIZE=4`
- **Ray scaling**: Reducidos workers de Ray de 8 a 4 para liberar GPUs para vLLM
- **Próximos modelos**: Una vez validado, se pueden usar modelos más grandes como:
  - `deepseek-coder:33b` (Developer)
  - `mistralai/Mistral-7B-Instruct-v0.3` (QA)
  - `databricks/dbrx-instruct` (Architect)
  - `Qwen/Qwen2.5-Coder-14B-Instruct` (DevOps)
  - `deepseek-ai/deepseek-coder-6.7b-instruct` (Data)

