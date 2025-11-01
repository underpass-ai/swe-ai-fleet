# Ray Executor Service

**Responsabilidad única**: Ejecutar deliberaciones de agentes en el Ray cluster.

## 🎯 Arquitectura

Este microservicio desacopla la lógica de ejecución de Ray del Orchestrator, siguiendo el principio de responsabilidad única:

- **Orchestrator**: Orquestación, coordinación de agentes, gRPC APIs
- **Ray Executor**: Ejecución distribuida de deliberaciones en Ray workers

```
┌─────────────────┐        gRPC        ┌─────────────────┐
│                 │ ──────────────────> │                 │
│  Orchestrator   │                     │  Ray Executor   │
│                 │ <────────────────── │                 │
└─────────────────┘                     └────────┬────────┘
                                                 │
                                                 │ Ray Client
                                                 │
                                        ┌────────▼────────┐
                                        │   Ray Cluster   │
                                        │  (GPU Workers)  │
                                        └─────────────────┘
```

## 🔧 Compatibilidad de Versiones

**Crítico**: Ray Executor debe usar la **misma versión de Python** que el Ray Cluster.

- **Ray Cluster**: Python 3.9.23 (imagen base de KubeRay)
- **Ray Executor**: Python 3.9 (Dockerfile usa `python:3.9-slim`)
- **Ray Version**: 2.49.2 (fija en `requirements.txt`)

### ¿Por qué Python 3.9 y no 3.13?

Ray no permite conexiones entre diferentes versiones de Python. El cluster usa Python 3.9, por lo tanto el cliente (Ray Executor) también debe usar Python 3.9.

## 📋 API gRPC

### `ExecuteDeliberation`

Ejecuta una deliberación en el Ray cluster.

**Request**:
```protobuf
message ExecuteDeliberationRequest {
  string task_id = 1;
  string task_description = 2;
  string role = 3;
  TaskConstraints constraints = 4;
  repeated Agent agents = 5;
  string vllm_url = 6;
  string vllm_model = 7;
}
```

**Response**:
```protobuf
message ExecuteDeliberationResponse {
  string deliberation_id = 1;
  string status = 2;
  string message = 3;
}
```

### `GetDeliberationStatus`

Obtiene el estado de una deliberación en ejecución.

**Request**:
```protobuf
message GetDeliberationStatusRequest {
  string deliberation_id = 1;
}
```

**Response**:
```protobuf
message GetDeliberationStatusResponse {
  string status = 1;  // "running", "completed", "failed"
  DeliberationResult result = 2;
  string error_message = 3;
}
```

### `GetStatus`

Health check y estadísticas del servicio.

## 🚀 Deployment

### Variables de Entorno

- `RAY_ADDRESS`: Dirección del Ray cluster (default: `ray://ray-gpu-head-svc.ray.svc.cluster.local:10001`)
- `NATS_URL`: URL de NATS para publicar resultados (default: `nats://nats.swe-ai-fleet.svc.cluster.local:4222`)
- `GRPC_PORT`: Puerto gRPC (default: `50056`)

### Kubernetes

```bash
kubectl apply -f deploy/k8s/14-ray_executor.yaml
```

## 🏗️ Build

```bash
# Build
podman build -t registry.underpassai.com/swe-fleet/ray_executor:v1.0.3 \
  -f services/ray_executor/Dockerfile .

# Push
podman push registry.underpassai.com/swe-fleet/ray_executor:v1.0.3
```

### Nota sobre gRPC Code Generation

El código gRPC se genera **durante el build del Dockerfile**, no se versiona en Git:

```dockerfile
RUN mkdir -p /app/ray-executor/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/app/specs \
    --python_out=/app/ray-executor/gen \
    --grpc_python_out=/app/ray-executor/gen \
    ray_executor.proto
```

## 🔍 Monitoring

```bash
# Ver logs
kubectl logs -n swe-ai-fleet -l app=ray_executor -f

# Ver estado
kubectl get pods -n swe-ai-fleet -l app=ray_executor

# Ver estadísticas
grpcurl -plaintext ray_executor.swe-ai-fleet.svc.cluster.local:50056 \
  ray_executor.v1.RayExecutorService/GetStatus
```

## 📊 Métricas

El servicio mantiene métricas internas:

- `total_deliberations`: Total de deliberaciones ejecutadas
- `active_deliberations`: Deliberaciones en ejecución
- `completed_deliberations`: Deliberaciones completadas
- `failed_deliberations`: Deliberaciones fallidas
- `average_execution_time_ms`: Tiempo promedio de ejecución

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit/ray_executor/

# Integration tests (requiere Ray cluster)
pytest tests/integration/ray_executor/
```

## 🔄 Flujo de Ejecución

1. **Orchestrator** recibe una solicitud de deliberación (via NATS o gRPC)
2. **Orchestrator** llama a `RayExecutorService.ExecuteDeliberation()`
3. **Ray Executor** crea un `VLLMAgentJob` y lo envía al Ray cluster
4. **Ray Worker** ejecuta el job, llamando a vLLM para inferencia
5. **Ray Worker** publica el resultado en NATS (`orchestration.deliberation.completed`)
6. **Orchestrator** consume el resultado y continúa la orquestación

## 🛡️ Principios de Diseño

- **Single Responsibility**: Solo se encarga de ejecutar jobs en Ray
- **Stateless**: No mantiene estado persistente
- **Fault Tolerant**: Ray maneja reintentos y failovers
- **Decoupled**: Comunicación via gRPC, sin dependencias directas con Orchestrator

## 📝 TODO

- [ ] Implementar reintentos con backoff exponencial
- [ ] Agregar métricas de Prometheus
- [ ] Implementar cancelación de deliberaciones
- [ ] Agregar soporte para múltiples Ray clusters
- [ ] Implementar rate limiting para proteger el cluster
