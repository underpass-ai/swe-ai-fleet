# 🔧 REFACTOR URGENTE: Orchestrator Server → Arquitectura Hexagonal

**Fecha**: 16 de Octubre de 2025  
**Prioridad**: 🔴 ALTA  
**Componente**: `services/orchestrator/server.py`

---

## 🚨 PROBLEMA ACTUAL

El archivo `services/orchestrator/server.py` tiene **1078 líneas** y mezcla múltiples responsabilidades:

### Anti-Patterns Identificados

1. **Servicer con lógica de negocio embebida** ❌
   - Métodos gRPC con lógica compleja (100+ líneas)
   - Creación de agents directamente en el servicer
   - Inicialización de councils mezclada con setup del servidor

2. **Función `serve_async()` hace demasiado** ❌
   - Inicializa NATS handlers
   - Crea consumers
   - Auto-inicializa councils
   - Configura servidor gRPC
   - **400+ líneas** en una sola función

3. **Dependencias hardcodeadas** ❌
   - `VLLMConfig.from_env()` llamado directamente
   - `AgentFactory` instanciado inline
   - No hay inyección de dependencias

4. **Testing difícil** ❌
   - Imposible testear auto-inicialización sin servidor gRPC
   - Mocks complicados por acoplamiento
   - Setup complejo en cada test

---

## ✅ ARQUITECTURA HEXAGONAL TARGET

### Estructura Propuesta

```
services/orchestrator/
├── server.py                    # 50 líneas - Solo setup gRPC
├── application/
│   ├── __init__.py
│   ├── orchestrator_service.py  # Application Service (lógica de negocio)
│   └── council_initializer.py   # Auto-init logic separado
├── ports/
│   ├── inbound/
│   │   └── orchestrator_port.py # Interface para gRPC servicer
│   └── outbound/
│       ├── agent_repository_port.py
│       ├── council_repository_port.py
│       └── event_publisher_port.py
├── adapters/
│   ├── inbound/
│   │   └── grpc_servicer.py     # Thin wrapper sobre gRPC
│   └── outbound/
│       ├── nats_event_publisher.py
│       ├── in_memory_council_repository.py
│       └── agent_factory_adapter.py
└── domain/
    └── (ya existe - mantener)
```

---

## 🎯 BENEFICIOS DEL REFACTOR

### 1. Separación de Concerns ✅
```python
# ANTES (server.py - todo mezclado):
class OrchestratorServiceServicer:
    def Deliberate(self, request, context):
        # 100 líneas de lógica
        agents = AgentFactory.create_agent(...)  # ← Acoplamiento
        result = deliberate_usecase.execute(...)
        nats_handler.publish(...)  # ← Más acoplamiento

# DESPUÉS (hexagonal):
class OrchestratorApplicationService:
    def __init__(self, 
                 agent_repo: AgentRepositoryPort,
                 event_publisher: EventPublisherPort):
        self.agents = agent_repo
        self.events = event_publisher
    
    async def deliberate(self, task_id, task, role):
        agents = await self.agents.get_council(role)
        result = await self.deliberate_usecase.execute(...)
        await self.events.publish("deliberation.completed", result)
```

### 2. Testing Simplificado ✅
```python
# Antes: Necesitas todo el servidor gRPC
def test_deliberate():
    server = setup_full_grpc_server()  # Complejo
    stub = create_stub()
    response = stub.Deliberate(...)

# Después: Solo testeas application service
def test_deliberate():
    mock_agents = Mock(AgentRepositoryPort)
    mock_events = Mock(EventPublisherPort)
    
    service = OrchestratorApplicationService(mock_agents, mock_events)
    result = await service.deliberate(...)
    
    assert result.status == "completed"
```

### 3. Inyección de Dependencias ✅
```python
# application/container.py
class Container:
    def __init__(self, config: SystemConfig):
        # Repositories
        self.agent_repo = InMemoryAgentRepository()
        self.council_repo = InMemoryCouncilRepository()
        
        # Adapters
        self.vllm_client = VLLMClient(config.vllm_url)
        self.nats_publisher = NATSEventPublisher(config.nats_url)
        
        # Application Services
        self.orchestrator_service = OrchestratorApplicationService(
            agent_repo=self.agent_repo,
            event_publisher=self.nats_publisher,
            vllm_client=self.vllm_client,
        )
```

### 4. Auto-Init como Port ✅
```python
# ports/outbound/council_initializer_port.py
class CouncilInitializerPort(ABC):
    @abstractmethod
    async def initialize_all(self, roles: list[RoleConfig]) -> dict[str, list[Agent]]:
        pass

# adapters/outbound/vllm_council_initializer.py
class VLLMCouncilInitializer(CouncilInitializerPort):
    async def initialize_all(self, roles):
        councils = {}
        for role in roles:
            councils[role.name] = await self._create_council(role)
        return councils
```

---

## 📋 PLAN DE REFACTOR

### Fase 1: Extraer Application Service (2-3 días)
- [ ] Crear `application/orchestrator_service.py`
- [ ] Mover lógica de `Deliberate()` → `deliberate()`
- [ ] Mover lógica de `CreateCouncil()` → `create_council()`
- [ ] Definir ports
- [ ] Tests del application service

### Fase 2: Separar Adapters (2 días)
- [ ] Crear `adapters/inbound/grpc_servicer.py`
- [ ] Thin wrapper sobre gRPC (solo conversión proto ↔ domain)
- [ ] Crear `adapters/outbound/nats_event_publisher.py`
- [ ] Implementar repositories

### Fase 3: Dependency Injection (1 día)
- [ ] Crear `application/container.py`
- [ ] Refactor `serve_async()` para usar container
- [ ] Reducir `server.py` a < 100 líneas

### Fase 4: Migrar Auto-Init (1 día)
- [ ] Extraer a `application/council_initializer.py`
- [ ] Port + Adapter pattern
- [ ] Tests de auto-init aislados

---

## ⚠️ RIESGOS SI NO SE REFACTORIZA

1. **Deuda técnica creciente** ❌
   - Archivo seguirá creciendo (ya 1078 líneas)
   - Cada feature nueva agrega complejidad

2. **Dificultad para onboarding** ❌
   - Nuevos desarrolladores tardan días en entender el flujo
   - Código no sigue principios SOLID

3. **Testing frágil** ❌
   - Tests acoplados al servidor gRPC
   - Mocks complejos y frágiles
   - Coverage difícil de mantener

4. **Evolución bloqueada** ❌
   - Difícil agregar nuevos tipos de agents
   - Difícil cambiar estrategias de deliberación
   - No se puede intercambiar componentes

---

## 🎯 BENEFICIOS ESPERADOS POST-REFACTOR

| Métrica | Actual | Target |
|---------|--------|--------|
| Líneas en server.py | 1078 | < 100 |
| Cobertura de tests | ~60% | > 90% |
| Complejidad ciclomática | Alta | Baja |
| Tiempo setup test | ~5s | < 0.5s |
| Onboarding time | 3+ días | 1 día |

---

## 📚 REFERENCIAS

- **Clean Architecture**: Robert C. Martin
- **Hexagonal Architecture**: Alistair Cockburn
- **DDD**: Eric Evans

---

**Fecha de creación**: 2025-10-16  
**Owner**: Tirso (Architect)  
**Status**: 🔴 PENDIENTE (documentado, no iniciado)

