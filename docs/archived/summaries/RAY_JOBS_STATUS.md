# 📊 Estado de Ray Jobs en el Sistema

**Fecha**: 16 de Octubre de 2025, 22:15  
**Monitor**: `/home/tirso/ai/developents/swe-ai-fleet/tests/e2e/monitor_ray_jobs.sh` (activo)

---

## 🔍 ESTADO ACTUAL

### ❌ Ray NO está activo

```
RayCluster: NO desplegado
RayJobs: 0
Ray Head: NO existe
Ray Workers: NO existen
```

### ✅ Configuración presente

**Orchestrator** tiene configuración de Ray:
```bash
RAY_ADDRESS=ray://kuberay-head-svc.swe-ai-fleet.svc.cluster.local:10001
VLLM_URL=http://vllm-server-service.swe-ai-fleet.svc.cluster.local:8000
VLLM_MODEL=Qwen/Qwen3-0.6B
```

**Código** tiene soporte para Ray:
- `DeliberateAsync` usecase (usa Ray para ejecutar deliberaciones)
- RPC `Deliberate()` implementado
- RPC `GetDeliberationResult()` para consultar status

---

## 🚫 POR QUÉ NO SE CREAN RAY JOBS

### 1. No hay RayCluster desplegado

**Archivo de deployment**: No existe `deploy/k8s/09-kuberay-cluster.yaml`

**Solución**:
```bash
# Crear archivo de deployment de RayCluster
# O aplicar manifiestos de KubeRay operator si existen
kubectl get crd rayclusters.ray.io
```

---

### 2. No hay councils configurados

**Log de Orchestrator**:
```
⚠️  No agents configured - councils are empty. 
    Agents must be registered separately.
```

**Razón**: Councils están vacíos al arrancar
```python
# services/orchestrator/server.py:60
self.councils: dict[str, list[Agent]] = {
    "DEV": [],
    "QA": [],
    "ARCHITECT": [],
    "DEVOPS": [],
    "DATA": []
}
```

**Solución**: Llamar RPC `CreateCouncil` para cada rol:
```python
# Ejemplo (desde cliente gRPC):
stub.CreateCouncil(CreateCouncilRequest(
    role="DEV",
    num_agents=3,
    config=CouncilConfig(
        agent_type="RAY_VLLM",  # Agents reales con vLLM
        deliberation_rounds=2
    )
))
```

---

### 3. Evento `plan.approved` NO dispara deliberación

**Handler actual** (`services/orchestrator/consumers/planning_consumer.py:169`):

```python
async def _handle_plan_approved(self, msg):
    """Handle plan approval events."""
    event = json.loads(msg.data.decode())
    story_id = event.get("story_id")
    roles = event.get("roles", [])
    
    logger.info(f"Plan approved: {plan_id} for story {story_id}")
    logger.info(f"Roles required for {story_id}: {', '.join(roles)}")
    
    # TODO: Implementar derivación de subtasks y dispatching
    # - Derive subtasks from plan
    # - Create councils for roles if not exist
    # - Submit deliberation jobs to Ray
    
    await msg.ack()  # ← SOLO LOGGEA Y ACK
```

**Problema**: El handler NO llama a `Deliberate()`, por lo que NO se crea ningún RayJob.

**Flujo que falta**:
```
plan.approved → Orchestrator consumer → CreateCouncil → Deliberate → Ray Job
```

---

## 🎯 PLAN PARA ACTIVAR RAY JOBS

### Fase 1: Desplegar RayCluster ⏳

1. **Verificar KubeRay Operator**:
   ```bash
   kubectl get crd rayclusters.ray.io
   kubectl get pods -n kuberay-operator-system
   ```

2. **Crear RayCluster manifest** (`deploy/k8s/09-kuberay-cluster.yaml`):
   ```yaml
   apiVersion: ray.io/v1
   kind: RayCluster
   metadata:
     name: kuberay
     namespace: swe-ai-fleet
   spec:
     rayVersion: '2.9.0'
     headGroupSpec:
       rayStartParams:
         dashboard-host: '0.0.0.0'
       template:
         spec:
           containers:
           - name: ray-head
             image: rayproject/ray:2.9.0-py310
             resources:
               limits:
                 cpu: 2
                 memory: 4Gi
     workerGroupSpecs:
     - replicas: 2
       minReplicas: 1
       maxReplicas: 5
       groupName: workers
       rayStartParams: {}
       template:
         spec:
           containers:
           - name: ray-worker
             image: rayproject/ray:2.9.0-py310
             resources:
               limits:
                 cpu: 2
                 memory: 4Gi
   ```

3. **Desplegar**:
   ```bash
   kubectl apply -f deploy/k8s/09-kuberay-cluster.yaml
   kubectl get raycluster -n swe-ai-fleet
   ```

---

### Fase 2: Inicializar Councils 📋

**Script de inicialización** (ya existe: `tests/e2e/setup_all_councils.py`):
```bash
cd tests/e2e
python setup_all_councils.py
```

Esto crea councils para todos los roles (DEV, QA, ARCHITECT, DEVOPS, DATA).

---

### Fase 3: Implementar Auto-Dispatching 🚀

**Modificar** `services/orchestrator/consumers/planning_consumer.py`:

```python
async def _handle_plan_approved(self, msg):
    """Handle plan approval events."""
    event = json.loads(msg.data.decode())
    story_id = event.get("story_id")
    roles = event.get("roles", [])
    
    logger.info(f"Plan approved: {plan_id} for story {story_id}")
    
    # 1. Crear councils si no existen
    for role in roles:
        if role not in self.orchestrator_service.councils or \
           len(self.orchestrator_service.councils[role]) == 0:
            logger.info(f"Creating council for role {role}...")
            await self._create_council_for_role(role)
    
    # 2. Derivar subtasks (llamar a Planning Service)
    subtasks = await self._derive_subtasks(story_id, plan_id)
    
    # 3. Dispatch deliberations a Ray
    for subtask in subtasks:
        logger.info(f"Dispatching deliberation for subtask {subtask.id}...")
        deliberation_id = await self.orchestrator_service.deliberate_async.submit(
            task=subtask,
            role=subtask.role,
            council=self.orchestrator_service.councils[subtask.role]
        )
        logger.info(f"✓ Deliberation submitted to Ray: {deliberation_id}")
    
    await msg.ack()
```

---

## 📊 MONITOREO ACTUAL

**Script activo**: `tests/e2e/monitor_ray_jobs.sh`

**Output en tiempo real**:
```
[2025-10-16 22:14:36] ⏱️  Monitoring... (Jobs: 0)
```

El monitor detectará automáticamente cuando:
- Se cree un RayJob
- Se desplieguen Ray Workers
- Cambien los status de los jobs

**Uso**:
```bash
# Ver logs del monitor
tail -f /tmp/ray_monitor.log

# Detener monitor
kill <PID del monitor>
```

---

## 🎯 ESTADO DESEADO

```
✅ RayCluster: 1 head + 2 workers
✅ Councils: 5 roles x 3 agents = 15 agents
✅ Auto-dispatch: plan.approved → derive → deliberate → Ray Job
✅ Ray Jobs: Creándose para cada subtask
✅ Monitor: Mostrando jobs en tiempo real
```

---

## 📝 PRÓXIMOS PASOS

1. ⏳ **Desplegar RayCluster** (requiere operator de KubeRay)
2. ⏳ **Ejecutar `setup_all_councils.py`** para crear agents
3. ⏳ **Implementar auto-dispatching** en planning_consumer
4. ✅ **Monitor activo** (ya funcionando)

---

**Nota**: Actualmente el sistema funciona sin Ray porque:
- Los eventos se procesan y guardan en Neo4j ✅
- Pero NO se ejecutan deliberaciones con agents ❌
- Es un pipeline básico de eventos, no un sistema multi-agent activo

**Para activar el sistema multi-agent completo, se necesita Ray.**

