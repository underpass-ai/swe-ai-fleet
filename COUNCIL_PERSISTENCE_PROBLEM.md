# 🔴 PROBLEMA CRÍTICO: Councils No Persistidos

**Fecha**: 20 de Octubre de 2025  
**Severidad**: 🔴 **CRÍTICA** - Pérdida de datos en cada restart  
**Estado**: 📝 DOCUMENTADO - Requiere Arquitectura Fix  

---

## 🎯 Problema

### Comportamiento Actual (ERRÓNEO):

```
1. Orchestrator pod arranca
2. CouncilRegistry inicializado vacío (en memoria)
3. Job orchestrator-init-councils crea 5 councils
4. Councils almacenados en CouncilRegistry (RAM)
5. Pod reinicia (por upgrade, crash, scale to 0, etc.)
6. CouncilRegistry vacío de nuevo ❌
7. Necesitas ejecutar orchestrator-init-councils de nuevo
```

**Resultado**: **Pérdida de datos en cada restart**

---

## 🔍 Root Cause

### Ubicación del Código

**Archivo**: `services/orchestrator/server.py`  
**Líneas**: ~130-150

```python
class OrchestratorServiceServicer:
    def __init__(self, ...):
        # Council registry en memoria (RAM)
        self.council_registry = CouncilRegistry()  # ← Solo RAM, NO persistido
        self.stats = OrchestratorStatistics()
```

**Archivo**: `services/orchestrator/domain/entities/council_registry.py`

```python
class CouncilRegistry:
    """In-memory registry of councils."""  # ← "In-memory" = problema
    
    def __init__(self):
        self._councils: dict[str, Any] = {}  # ← Solo dict en RAM
        self._agents: dict[str, list[Any]] = {}
```

---

## 🚨 Impacto del Problema

### ❌ Qué NO Funciona

1. **Pod restart** → Councils perdidos
2. **Deployment update** → Councils perdidos
3. **Scale to 0 and back** → Councils perdidos
4. **Pod crash** → Councils perdidos
5. **Node failure** → Councils perdidos

### 💰 Costo Operacional

Cada restart del orchestrator requiere:

1. Ejecutar `orchestrator-init-councils` job
2. Esperar ~30 segundos para creación
3. Verificar que councils fueron creados
4. **Downtime** durante el cual no hay councils

**En producción esto es INACEPTABLE.**

---

## ✅ Soluciones Propuestas

### Solución 1: Persistir en Valkey/Redis (RECOMENDADA)

**Concepto**: Usar Valkey como backing store para CouncilRegistry

#### Arquitectura

```
CouncilRegistry (Domain Entity)
    ↓ usa
CouncilPersistencePort (Domain Port)
    ↓ implementado por
ValkeyCoun cilAdapter (Infrastructure Adapter)
    ↓ conecta a
Valkey (Infrastructure)
```

#### Implementación

**1. Crear Port**:
```python
# services/orchestrator/domain/ports/council_persistence_port.py

class CouncilPersistencePort(ABC):
    @abstractmethod
    async def save_council(self, role: str, council_data: dict) -> None:
        pass
    
    @abstractmethod
    async def load_council(self, role: str) -> dict | None:
        pass
    
    @abstractmethod
    async def list_councils(self) -> list[str]:
        pass
    
    @abstractmethod
    async def delete_council(self, role: str) -> None:
        pass
```

**2. Crear Adapter**:
```python
# services/orchestrator/infrastructure/adapters/valkey_council_adapter.py

import json
import valkey

class ValkeyCouncilAdapter(CouncilPersistencePort):
    def __init__(self, valkey_client):
        self._client = valkey_client
        self._prefix = "orchestrator:councils:"
    
    async def save_council(self, role: str, council_data: dict) -> None:
        key = f"{self._prefix}{role}"
        await self._client.set(key, json.dumps(council_data))
    
    async def load_council(self, role: str) -> dict | None:
        key = f"{self._prefix}{role}"
        data = await self._client.get(key)
        return json.loads(data) if data else None
    
    async def list_councils(self) -> list[str]:
        keys = await self._client.keys(f"{self._prefix}*")
        return [k.replace(self._prefix, "") for k in keys]
    
    async def delete_council(self, role: str) -> None:
        key = f"{self._prefix}{role}"
        await self._client.delete(key)
```

**3. Actualizar CouncilRegistry**:
```python
# services/orchestrator/domain/entities/council_registry.py

class CouncilRegistry:
    def __init__(self, persistence: CouncilPersistencePort | None = None):
        self._councils: dict[str, Any] = {}
        self._agents: dict[str, list[Any]] = {}
        self._persistence = persistence
    
    async def add_council(self, role: str, council: Any, agents: list[Any]):
        self._councils[role] = council
        self._agents[role] = agents
        
        # Persist if available
        if self._persistence:
            council_data = self._serialize_council(role, council, agents)
            await self._persistence.save_council(role, council_data)
    
    async def restore_from_persistence(self):
        """Restore councils from persistence on startup."""
        if not self._persistence:
            return
        
        roles = await self._persistence.list_councils()
        for role in roles:
            council_data = await self._persistence.load_council(role)
            if council_data:
                council, agents = self._deserialize_council(council_data)
                self._councils[role] = council
                self._agents[role] = agents
```

**4. Actualizar server.py Startup**:
```python
# services/orchestrator/server.py

async def serve_async():
    # Create Valkey adapter
    valkey_client = await create_valkey_client()
    council_persistence = ValkeyCouncilAdapter(valkey_client)
    
    # Create registry with persistence
    council_registry = CouncilRegistry(persistence=council_persistence)
    
    # Restore councils from Valkey on startup
    await council_registry.restore_from_persistence()
    logger.info(f"✅ Restored {len(council_registry.list_roles())} councils from Valkey")
```

#### Ventajas

- ✅ **Survive restarts** - Councils persisten entre pods
- ✅ **Fast startup** - Restore desde Valkey en ~100ms
- ✅ **Hexagonal preserved** - Port/Adapter pattern
- ✅ **Ya tenemos Valkey** - No nueva infra
- ✅ **Simple** - Key/value natural para councils

#### Desventajas

- ⚠️ Necesita serializar/deserializar councils
- ⚠️ Agentes con state complejo pueden ser difíciles de serializar

#### Estimación

**3-4 horas** de desarrollo + testing

---

### Solución 2: Persistir en Neo4j

**Concepto**: Usar Neo4j para almacenar councils como grafo

#### Ventajas

- ✅ Model más rico (grafo de agentes y councils)
- ✅ Queries complejas posibles
- ✅ Ya tenemos Neo4j
- ✅ Schema natural para councils/agents

#### Desventajas

- ⚠️ Más complejo que key/value
- ⚠️ Overhead para operaciones simples
- ⚠️ Neo4j está planeado para context, no councils

#### Estimación

**5-6 horas** de desarrollo + testing

---

### Solución 3: Init Councils on Startup (Quick Fix)

**Concepto**: Ejecutar init_councils.py DENTRO del server.py en startup

#### Implementación

```python
# services/orchestrator/server.py

async def serve_async():
    # ... (setup adapters) ...
    
    # Initialize councils on startup if empty
    if len(council_registry.list_roles()) == 0:
        logger.info("📋 No councils found, initializing defaults...")
        await init_default_councils(
            servicer=servicer,
            roles=["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]
        )
        logger.info("✅ Default councils initialized")
```

#### Ventajas

- ✅ **Simple** - Sin persistence layer
- ✅ **Rápido** - 30 minutos implementación
- ✅ **Funciona** - Councils siempre disponibles

#### Desventajas

- ⚠️ **Councils recreados** en cada restart (no restore state)
- ⚠️ **No persistence** - Estado perdido
- ⚠️ **Configuración hardcoded** - No flexible

#### Estimación

**30 minutos** - Quick fix temporal

---

## 🎯 Recomendación

### Short-term (AHORA): **Solución 3**

Para desbloquear testing inmediato:
- Implementar init on startup
- 30 minutos
- Permite continuar con E2E testing

### Long-term (Próxima Iteración): **Solución 1**

Para producción:
- Valkey persistence
- 3-4 horas
- Production-ready

---

## 📋 Plan de Acción Inmediata

### Paso 1: Quick Fix (30 min)

```python
# services/orchestrator/server.py

async def init_default_councils_if_empty(servicer):
    """Initialize default councils if registry is empty."""
    if len(servicer.council_registry.list_roles()) > 0:
        logger.info(f"✅ Found {len(servicer.council_registry.list_roles())} existing councils")
        return
    
    logger.info("📋 No councils found, initializing defaults...")
    
    roles = ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]
    vllm_url = os.getenv("VLLM_URL", "http://vllm.swe-ai-fleet.svc.cluster.local:8000")
    
    for role in roles:
        # Create 3 agents per role
        agents = []
        for i in range(3):
            agent = VLLMAgentFactoryAdapter.create_agent(
                agent_id=f"{role.lower()}-agent-{i+1}",
                role=role,
                vllm_url=vllm_url,
                model="Qwen/Qwen2.5-0.5B-Instruct",
            )
            agents.append(agent)
        
        # Add to registry
        council = Deliberate(agents, ScoringTooling(), rounds=1)
        servicer.council_registry.add_council(role, council, agents)
        logger.info(f"✅ Initialized council for {role} with {len(agents)} agents")
    
    logger.info(f"✅ Initialized {len(roles)} councils")

# En serve_async():
async def serve_async():
    # ... (create servicer) ...
    
    # Initialize councils if empty
    await init_default_councils_if_empty(servicer)
    
    # ... (start server) ...
```

### Paso 2: Deploy & Test (15 min)

```bash
# Rebuild con init on startup
podman build -f services/orchestrator/Dockerfile \
  -t registry.underpassai.com/swe-fleet/orchestrator:v2.9.0-councils-auto-init .

# Push
podman push registry.underpassai.com/swe-fleet/orchestrator:v2.9.0-councils-auto-init

# Deploy
kubectl set image -n swe-ai-fleet deployment/orchestrator \
  orchestrator=registry.underpassai.com/swe-fleet/orchestrator:v2.9.0-councils-auto-init

# Scale to force restart
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=0
sleep 5
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=1

# Verify councils auto-initialized
kubectl logs -n swe-ai-fleet -l app=orchestrator | grep "Initialized council"

# Test auto-dispatch
kubectl apply -f deploy/k8s/98-test-auto-dispatch-job.yaml
```

---

## 🎓 Lecciones Aprendidas

### 1. In-Memory State is Ephemeral

**Problema**: CouncilRegistry solo en RAM

**Aprendizaje**: En Kubernetes, TODO lo que está solo en RAM se pierde en restarts

**Solución**: Persistir state crítico

---

### 2. Stateful Services Necesitan Persistence

**Problema**: Orchestrator es stateful (tiene councils) pero no persiste

**Aprendizaje**: Servicios stateful en K8s necesitan:
- Persistence layer (DB, cache, filesystem)
- O initialization automática
- O StatefulSet con volumes

**Solución**: Agregar persistence layer

---

### 3. Init Jobs No Son Suficientes

**Problema**: Dependency externa (job) para funcionar

**Aprendizaje**: Servicios deben ser **self-contained**

**Solución**: Init on startup o persistence

---

## 📊 Comparación de Soluciones

| Aspecto | In-Memory (Actual) | Init on Startup | Valkey Persistence |
|---------|-------------------|-----------------|-------------------|
| **Survive restarts** | ❌ No | ❌ No | ✅ Sí |
| **Complexity** | Simple | Simple | Medio |
| **Startup time** | Rápido | Medio (+5s) | Rápido (+0.1s) |
| **Production-ready** | ❌ No | ⚠️ Temporal | ✅ Sí |
| **State preserved** | ❌ No | ❌ No | ✅ Sí |
| **Implementation** | 0 min | 30 min | 3-4 horas |

---

## 🎯 Decisión

### Implementar Ambas:

1. **AHORA**: Init on startup (quick fix, 30 min)
2. **PRÓXIMA ITERACIÓN**: Valkey persistence (production, 3-4 horas)

### Razón:

- Quick fix desbloquea testing AHORA
- Persistence layer se hace bien con tiempo
- No bloqueamos progreso mientras implementamos la solución correcta

---

## ⚡ Workaround Actual

**Mientras implementamos el fix**:

```bash
# Script para reiniciar orchestrator con councils
./scripts/restart-orchestrator-with-councils.sh

# Contenido:
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=0
sleep 5
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=1
kubectl wait --for=condition=ready pod -l app=orchestrator -n swe-ai-fleet
kubectl delete job -n swe-ai-fleet orchestrator-init-councils
kubectl apply -f deploy/k8s/11b-orchestrator-init-councils.yaml
kubectl wait --for=condition=complete job/orchestrator-init-councils -n swe-ai-fleet
echo "✅ Orchestrator restarted with councils"
```

**Este script es una banda temporal** hasta tener persistence.

---

## 📅 Roadmap

### Fase 1: Quick Fix (HOY - 1 hora)
- [ ] Implementar init_default_councils_if_empty()
- [ ] Integrar en server.py startup
- [ ] Testing
- [ ] Deploy

### Fase 2: Valkey Persistence (Próxima Iteración - 4 horas)
- [ ] Crear CouncilPersistencePort
- [ ] Implementar ValkeyCouncilAdapter
- [ ] Actualizar CouncilRegistry con persistence
- [ ] Serialization/deserialization de councils
- [ ] Testing (unit + integration)
- [ ] Deploy

### Fase 3: Migration (Cuando tengamos Fase 2)
- [ ] Exportar councils actuales
- [ ] Importar a Valkey
- [ ] Deploy nueva versión
- [ ] Verificar restore desde Valkey
- [ ] Eliminar init jobs

---

## ✍️ Notas del Arquitecto

Este problema es un ejemplo perfecto de:

1. **State management en microservicios** - No es trivial
2. **Trade-offs arquitectónicos** - Simplicidad vs Robustez
3. **Evolutivo** - Empezar simple, mejorar con tiempo

**La solución temporal (init on startup) es aceptable para desarrollo.**  
**La solución permanente (Valkey) es requerida para producción.**

No es un bug, es una **decisión arquitectónica que necesita evolucionar**.

---

## 📖 Referencias

- **12-Factor App**: https://12factor.net/ (Factor VI: Processes - Stateless)
- **Kubernetes StatefulSets**: Para servicios stateful
- **Valkey Persistence Patterns**: Key design para state
- **Event Sourcing**: Alternativa avanzada (rebuild state from events)

---

## 🔄 Estado Actual

- ❌ Councils se pierden en cada restart
- ⚠️ Workaround: Manual init job después de restart
- 📋 Quick fix planeado (init on startup)
- 📋 Production fix planeado (Valkey persistence)

**Este es el último bloqueador arquitectónico identificado!** 🎯


