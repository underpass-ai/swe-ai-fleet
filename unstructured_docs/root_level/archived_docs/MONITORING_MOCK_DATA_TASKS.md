# 📋 Plan de Acción - Eliminar Mock Data del Monitoring Dashboard

**Fecha**: 2025-10-17  
**Versión Actual**: v1.5.1  
**Objetivo**: Eliminar todos los placeholders y conectar con datos reales

---

## 🎯 Tareas Organizadas por Prioridad

### 🔴 ALTA PRIORIDAD - COMPLETADO ✅

- [x] **Task 1.1**: Eliminar `deliberation_source.py` (225 líneas de mock)
  - Estado: ✅ COMPLETADO
  - Archivo no se usaba en server.py
  - Eliminado exitosamente

---

### 🟡 MEDIA PRIORIDAD - Ray Executor Proto Extensions

#### **Task 2.1**: Implementar GetClusterStats RPC

**Objetivo**: Obtener estadísticas reales del Ray Cluster en lugar de valores hardcodeados

**Archivos a modificar**:
1. `specs/ray_executor.proto`
2. `services/ray-executor/server.py`
3. `services/monitoring/sources/ray_source.py`

**Pasos**:

##### 2.1.1: Actualizar `specs/ray_executor.proto`

```protobuf
// Agregar al service RayExecutorService
rpc GetClusterStats(GetClusterStatsRequest) returns (GetClusterStatsResponse);

// Agregar mensajes
message GetClusterStatsRequest {}

message GetClusterStatsResponse {
  string python_version = 1;
  string ray_version = 2;
  int32 total_nodes = 3;
  int32 alive_nodes = 4;
  ClusterResource cpus = 5;
  ClusterResource gpus = 6;
  ClusterResource memory_gb = 7;
  int32 active_jobs = 8;
  int32 completed_jobs = 9;
  int32 failed_jobs = 10;
}

message ClusterResource {
  double total = 1;
  double used = 2;
  double available = 3;
}
```

##### 2.1.2: Implementar en `services/ray-executor/server.py`

```python
async def GetClusterStats(self, request, context):
    """Get Ray Cluster statistics."""
    if not ray.is_initialized():
        context.set_code(grpc.StatusCode.UNAVAILABLE)
        context.set_details("Ray not initialized")
        return ray_executor_pb2.GetClusterStatsResponse()
    
    try:
        # Get cluster resources
        cluster_resources = ray.cluster_resources()
        available_resources = ray.available_resources()
        
        # Calculate CPU stats
        total_cpus = cluster_resources.get("CPU", 0.0)
        available_cpus = available_resources.get("CPU", 0.0)
        used_cpus = total_cpus - available_cpus
        
        # Calculate GPU stats
        total_gpus = cluster_resources.get("GPU", 0.0)
        available_gpus = available_resources.get("GPU", 0.0)
        used_gpus = total_gpus - available_gpus
        
        # Calculate Memory stats (bytes to GB)
        total_memory = cluster_resources.get("memory", 0.0) / (1024**3)
        available_memory = available_resources.get("memory", 0.0) / (1024**3)
        used_memory = total_memory - available_memory
        
        # Count nodes
        nodes = ray.nodes()
        total_nodes = len(nodes)
        alive_nodes = len([n for n in nodes if n["Alive"]])
        
        # Get Python and Ray versions
        python_version = sys.version.split()[0]
        ray_version = ray.__version__
        
        return ray_executor_pb2.GetClusterStatsResponse(
            python_version=python_version,
            ray_version=ray_version,
            total_nodes=total_nodes,
            alive_nodes=alive_nodes,
            cpus=ray_executor_pb2.ClusterResource(
                total=total_cpus,
                used=used_cpus,
                available=available_cpus
            ),
            gpus=ray_executor_pb2.ClusterResource(
                total=total_gpus,
                used=used_gpus,
                available=available_gpus
            ),
            memory_gb=ray_executor_pb2.ClusterResource(
                total=total_memory,
                used=used_memory,
                available=available_memory
            ),
            active_jobs=0,  # TODO: Implement job tracking
            completed_jobs=0,
            failed_jobs=0
        )
    except Exception as e:
        logger.error(f"Error getting cluster stats: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        context.set_details(str(e))
        return ray_executor_pb2.GetClusterStatsResponse()
```

##### 2.1.3: Actualizar `services/monitoring/sources/ray_source.py`

```python
async def get_cluster_stats(self) -> Dict[str, Any]:
    """Get Ray Cluster statistics."""
    if not self.stub:
        return {
            "connected": False,
            "error": "Ray Executor not connected"
        }
        
    try:
        from gen import ray_executor_pb2
        
        request = ray_executor_pb2.GetClusterStatsRequest()
        response = await self.stub.GetClusterStats(request)
        
        return {
            "connected": True,
            "status": "healthy",
            "python_version": response.python_version,
            "ray_version": response.ray_version,
            "nodes": {
                "total": response.total_nodes,
                "alive": response.alive_nodes
            },
            "resources": {
                "cpus": {
                    "total": response.cpus.total,
                    "used": response.cpus.used,
                    "available": response.cpus.available
                },
                "gpus": {
                    "total": response.gpus.total,
                    "used": response.gpus.used,
                    "available": response.gpus.available
                },
                "memory_gb": {
                    "total": response.memory_gb.total,
                    "used": response.memory_gb.used,
                    "available": response.memory_gb.available
                }
            },
            "jobs": {
                "active": response.active_jobs,
                "completed": response.completed_jobs,
                "failed": response.failed_jobs
            }
        }
    except Exception as e:
        logger.error(f"❌ Failed to get Ray Cluster stats: {e}")
        return {
            "connected": False,
            "error": str(e)
        }
```

**Estimación**: 2-3 horas  
**Dependencias**: Ninguna  
**Testing**: Unit tests + Integration tests

---

#### **Task 2.2**: Implementar GetActiveJobs RPC

**Objetivo**: Obtener lista real de Ray Jobs activos

**Archivos a modificar**:
1. `specs/ray_executor.proto`
2. `services/ray-executor/server.py`
3. `services/monitoring/sources/ray_source.py`

**Pasos**:

##### 2.2.1: Actualizar `specs/ray_executor.proto`

```protobuf
// Agregar al service RayExecutorService
rpc GetActiveJobs(GetActiveJobsRequest) returns (GetActiveJobsResponse);

// Agregar mensajes
message GetActiveJobsRequest {}

message GetActiveJobsResponse {
  repeated JobInfo jobs = 1;
}

message JobInfo {
  string job_id = 1;
  string name = 2;
  string status = 3;
  string submission_id = 4;
  string role = 5;
  string task_id = 6;
  google.protobuf.Timestamp start_time = 7;
  google.protobuf.Timestamp end_time = 8;
  string runtime = 9;
}
```

##### 2.2.2: Implementar tracking de jobs en `services/ray-executor/server.py`

```python
class RayExecutorServiceServicer(ray_executor_pb2_grpc.RayExecutorServiceServicer):
    def __init__(self):
        self.start_time = time.time()
        self.deliberations: Dict[str, Dict] = {}  # Ya existe
        self.active_jobs: Dict[str, Dict] = {}    # NUEVO: Track active jobs
        # ... resto del init

    async def ExecuteDeliberation(self, request, context):
        # ... código existente ...
        
        # AGREGAR: Track job info
        job_info = {
            'job_id': deliberation_id,
            'name': f"vllm-agent-job-{deliberation_id}",
            'status': 'RUNNING',
            'submission_id': deliberation_id,
            'role': request.role,
            'task_id': request.task_id,
            'start_time': time.time(),
            'end_time': None,
            'runtime_seconds': 0
        }
        self.active_jobs[deliberation_id] = job_info
        
        # ... resto del código ...

    async def GetActiveJobs(self, request, context):
        """Get list of active Ray jobs."""
        try:
            jobs = []
            current_time = time.time()
            
            for job_id, job_info in self.active_jobs.items():
                # Calculate runtime
                runtime_seconds = int(current_time - job_info['start_time'])
                minutes = runtime_seconds // 60
                seconds = runtime_seconds % 60
                runtime_str = f"{minutes}m {seconds}s"
                
                # Create JobInfo message
                start_timestamp = Timestamp()
                start_timestamp.FromSeconds(int(job_info['start_time']))
                
                job_pb = ray_executor_pb2.JobInfo(
                    job_id=job_info['job_id'],
                    name=job_info['name'],
                    status=job_info['status'],
                    submission_id=job_info['submission_id'],
                    role=job_info['role'],
                    task_id=job_info['task_id'],
                    start_time=start_timestamp,
                    runtime=runtime_str
                )
                
                jobs.append(job_pb)
            
            return ray_executor_pb2.GetActiveJobsResponse(jobs=jobs)
            
        except Exception as e:
            logger.error(f"Error getting active jobs: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            return ray_executor_pb2.GetActiveJobsResponse()
```

##### 2.2.3: Actualizar `services/monitoring/sources/ray_source.py`

```python
async def get_active_jobs(self) -> Dict[str, Any]:
    """Get list of active Ray jobs."""
    if not self.stub:
        return {
            "connected": False,
            "error": "Ray Executor not connected",
            "active_jobs": [],
            "total_active": 0
        }
        
    try:
        from gen import ray_executor_pb2
        
        request = ray_executor_pb2.GetActiveJobsRequest()
        response = await self.stub.GetActiveJobs(request)
        
        jobs = []
        for job_pb in response.jobs:
            start_dt = job_pb.start_time.ToDatetime() if job_pb.HasField("start_time") else None
            end_dt = job_pb.end_time.ToDatetime() if job_pb.HasField("end_time") else None
            
            jobs.append({
                "job_id": job_pb.job_id,
                "name": job_pb.name,
                "status": job_pb.status,
                "submission_id": job_pb.submission_id,
                "role": job_pb.role,
                "task_id": job_pb.task_id,
                "start_time": start_dt.isoformat() if start_dt else None,
                "end_time": end_dt.isoformat() if end_dt else None,
                "runtime": job_pb.runtime
            })
        
        return {
            "connected": True,
            "active_jobs": jobs,
            "total_active": len(jobs)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get active Ray jobs: {e}")
        return {
            "connected": False,
            "error": str(e),
            "active_jobs": [],
            "total_active": 0
        }
```

**Estimación**: 2-3 horas  
**Dependencias**: Ninguna  
**Testing**: Unit tests + Integration tests

---

#### **Task 2.3**: Extender Orchestrator ListCouncils RPC

**Objetivo**: Incluir agent_ids reales y modelo en lugar de mock

**Archivos a modificar**:
1. `specs/orchestrator.proto`
2. `services/orchestrator/server.py`
3. `services/monitoring/sources/orchestrator_source.py`

**Pasos**:

##### 2.3.1: Actualizar `specs/orchestrator.proto`

```protobuf
message CouncilInfo {
  string council_id = 1;
  string role = 2;
  int32 num_agents = 3;
  string status = 4;
  repeated string agent_ids = 5;  // NUEVO: IDs reales de agentes
  string model = 6;                // NUEVO: Modelo usado por el council
}
```

##### 2.3.2: Actualizar `services/orchestrator/server.py`

```python
async def ListCouncils(self, request, context):
    """List all active councils."""
    try:
        councils = []
        for role, _council in self.councils.items():
            # Get actual agents from council_agents
            agents = self.council_agents.get(role, [])
            agent_ids = [agent.id for agent in agents]
            
            # Get model from first agent (all agents in council use same model)
            model = agents[0].model if agents else "unknown"
            
            council_info = orchestrator_pb2.CouncilInfo(
                council_id=f"council-{role.lower()}",
                role=role,
                num_agents=len(agents),
                status="active" if len(agents) > 0 else "idle",
                agent_ids=agent_ids,  # NUEVO
                model=model           # NUEVO
            )
            councils.append(council_info)
        
        return orchestrator_pb2.ListCouncilsResponse(councils=councils)
    except Exception as e:
        logger.error(f"ListCouncils error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return orchestrator_pb2.ListCouncilsResponse()
```

##### 2.3.3: Actualizar `services/monitoring/sources/orchestrator_source.py`

```python
async def get_councils(self) -> Dict:
    """Get active councils and their agents."""
    if not self.channel:
        return {
            "connected": False,
            "error": "Orchestrator not connected"
        }
    
    try:
        from gen import orchestrator_pb2_grpc, orchestrator_pb2
        
        stub = orchestrator_pb2_grpc.OrchestratorServiceStub(self.channel)
        request = orchestrator_pb2.ListCouncilsRequest()
        response = await stub.ListCouncils(request)
        
        councils_data = []
        for council_info in response.councils:
            role_emojis = {
                "DEV": "🧑‍💻",
                "QA": "🧪", 
                "ARCHITECT": "🏗️",
                "DEVOPS": "⚙️",
                "DATA": "📊"
            }
            
            # Usar agent_ids REALES del proto
            agents = []
            for agent_id in council_info.agent_ids:
                agents.append({
                    "id": agent_id,
                    "status": "idle"  # TODO: Get real status from agent
                })
            
            councils_data.append({
                "role": council_info.role,
                "emoji": role_emojis.get(council_info.role, "🤖"),
                "agents": agents,
                "status": "active" if council_info.status == "active" else "idle",
                "model": council_info.model,  # Usar modelo REAL del proto
                "total_agents": council_info.num_agents
            })
        
        return {
            "connected": True,
            "councils": councils_data,
            "total_councils": len(councils_data),
            "total_agents": sum(c["total_agents"] for c in councils_data)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get councils: {e}")
        return {
            "connected": False,
            "error": str(e)
        }
```

**Estimación**: 1-2 horas  
**Dependencias**: Ninguna  
**Testing**: Unit tests + Integration tests

---

### 🟢 BAJA PRIORIDAD - Opcional

#### **Task 3.1**: Decidir sobre ValKey Mock Fallback

**Opciones**:

**Opción A**: Mantener mock fallback (RECOMENDADO)
- ✅ Útil para desarrollo local sin ValKey
- ✅ Frontend indica claramente "Mock Data"
- ✅ No afecta producción si ValKey está disponible

**Opción B**: Remover mock y solo error state
- ✅ Más estricto para producción
- ❌ Menos útil para desarrollo
- ❌ Requiere ValKey siempre disponible

**Recomendación**: **Mantener con feature flag**

```python
# En valkey_source.py
ENABLE_MOCK_FALLBACK = os.getenv("VALKEY_MOCK_FALLBACK", "true").lower() == "true"

async def get_cache_stats(self) -> Dict:
    if not self.client:
        if ENABLE_MOCK_FALLBACK:
            return self._mock_stats()
        else:
            return {
                "connected": False,
                "error": "ValKey not connected and mock fallback disabled"
            }
    # ... resto del código
```

**Estimación**: 30 minutos  
**Dependencias**: Ninguna

---

## 📊 Resumen de Tareas

| Task | Prioridad | Estimación | Estado |
|------|-----------|------------|--------|
| 1.1 - Eliminar deliberation_source.py | 🔴 Alta | 15 min | ✅ COMPLETADO |
| 2.1 - GetClusterStats RPC | 🟡 Media | 2-3h | ⏳ Pendiente |
| 2.2 - GetActiveJobs RPC | 🟡 Media | 2-3h | ⏳ Pendiente |
| 2.3 - Extender ListCouncils | 🟡 Media | 1-2h | ⏳ Pendiente |
| 3.1 - ValKey Mock Decision | 🟢 Baja | 30min | ⏳ Pendiente |

**Total Estimado**: 6-9 horas

---

## 🚀 Plan de Ejecución Recomendado

### Sprint 1 (Semana actual)
1. ✅ Task 1.1 - COMPLETADO
2. ⏳ Task 2.3 - Extender ListCouncils (más fácil, rápido win)

### Sprint 2 (Próxima semana)
3. ⏳ Task 2.1 - GetClusterStats RPC
4. ⏳ Task 2.2 - GetActiveJobs RPC

### Sprint 3 (Cuando haya tiempo)
5. ⏳ Task 3.1 - ValKey Mock Decision (opcional)

---

## ✅ Criterios de Aceptación

Para cada task:
- [ ] Código implementado y funcionando
- [ ] Proto regenerado (si aplica)
- [ ] Unit tests escritos y pasando
- [ ] Integration tests verificados
- [ ] Build de Docker exitoso
- [ ] Deploy a Kubernetes exitoso
- [ ] Dashboard muestra datos reales
- [ ] No hay errores en logs
- [ ] Documentación actualizada

---

## 📝 Notas Importantes

1. **Regenerar protos**: Después de cada cambio en `.proto`:
   ```bash
   # En Ray Executor
   cd services/ray_executor
   python -m grpc_tools.protoc --proto_path=../../specs \
       --python_out=gen --grpc_python_out=gen --pyi_out=gen \
       ray_executor.proto
   
   # En Orchestrator
   cd services/orchestrator
   python -m grpc_tools.protoc --proto_path=../../specs \
       --python_out=gen --grpc_python_out=gen --pyi_out=gen \
       orchestrator.proto
   ```

2. **Build y Deploy**:
   ```bash
   # Ray Executor
   podman build -t registry.underpassai.com/swe-fleet/ray_executor:vX.X.X \
       -f services/ray_executor/Dockerfile .
   podman push registry.underpassai.com/swe-fleet/ray_executor:vX.X.X
   kubectl set image deployment/ray_executor \
       ray_executor=registry.underpassai.com/swe-fleet/ray_executor:vX.X.X \
       -n swe-ai-fleet
   
   # Monitoring
   podman build -t registry.underpassai.com/swe-fleet/monitoring:vX.X.X \
       -f services/monitoring/Dockerfile .
   podman push registry.underpassai.com/swe-fleet/monitoring:vX.X.X
   kubectl set image deployment/monitoring-dashboard \
       monitoring=registry.underpassai.com/swe-fleet/monitoring:vX.X.X \
       -n swe-ai-fleet
   ```

3. **Testing Workflow**:
   - Primero: Unit tests locales
   - Segundo: Build Docker local
   - Tercero: Deploy a K8s dev
   - Cuarto: Verificar en dashboard
   - Quinto: Logs y métricas
   - Sexto: Deploy a producción

---

**Creado por**: AI Assistant  
**Aprobación pendiente**: Tirso (Lead Architect)  
**Última actualización**: 2025-10-17

