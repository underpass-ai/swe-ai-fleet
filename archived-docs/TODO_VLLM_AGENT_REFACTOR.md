# TODO: Refactor VLLMAgentJobBase - Separar Variantes

**Fecha**: 2025-10-11  
**Prioridad**: Media  
**Estado**: Pendiente

---

## 🎯 Problema Actual

`VLLMAgentJobBase` tiene una dependencia condicional de Ray que causa problemas en CI:

**Problema adicional descubierto**: Hay un directorio `tests/ray/` que crea un namespace package
que entra en conflicto con el módulo `ray` real, causando:
```
AttributeError: <module 'ray' (namespace) from ['/home/runner/.../tests/ray']> 
                does not have the attribute 'init'
```

**Solución temporal aplicada**: 
- Skip de `test_deliberate_async_usecase.py` cuando Ray no está disponible
- Verificación de `hasattr(ray, 'remote')` antes de usar Ray

```python
# Actual implementación
try:
    import ray
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    ray = None

# Después...
if RAY_AVAILABLE:
    @ray.remote(num_cpus=1, max_restarts=2)
    class VLLMAgentJob(VLLMAgentJobBase):
        pass
else:
    class VLLMAgentJob(VLLMAgentJobBase):  # Fallback
        pass
```

**Problemas**:
1. Lógica condicional compleja
2. Diferentes comportamientos según si Ray está disponible
3. Confusión sobre cuándo usar cada variante
4. Tests difíciles de mantener

---

## 💡 Solución Propuesta

### Opción A: Dos Clases Separadas (RECOMENDADO)

Crear dos implementaciones explícitas:

```python
# 1. Base class (sin Ray)
class VLLMAgentBase:
    """Base implementation for vLLM agents (no Ray dependency)."""
    
    def __init__(self, agent_id, role, vllm_url, model, ...):
        self.agent_id = agent_id
        self.role = role
        # ...
    
    async def execute(self, task_id, task, constraints, diversity):
        """Execute agent and return result."""
        # Implementation
        pass

# 2. Ray Actor (con Ray)
@ray.remote(num_cpus=1, max_restarts=2)
class VLLMAgentJob(VLLMAgentBase):
    """Ray remote actor for distributed execution."""
    
    def __init__(self, agent_id, role, vllm_url, model, nats_url, ...):
        super().__init__(agent_id, role, vllm_url, model, ...)
        self.nats_url = nats_url
        # Ray-specific setup
    
    async def run_async(self, task_id, task, constraints, diversity):
        """Execute and publish to NATS."""
        result = await self.execute(task_id, task, constraints, diversity)
        await self._publish_to_nats(result)
        return result
```

**Beneficios**:
- ✅ Separación clara de responsabilidades
- ✅ Tests más simples (VLLMAgentBase sin Ray)
- ✅ Ray opcional solo para producción
- ✅ Más fácil de mantener

---

## 📁 Estructura Propuesta

```
src/swe_ai_fleet/orchestrator/
├── agents/
│   ├── vllm_agent_base.py        # Base implementation (no Ray)
│   └── vllm_agent_ray.py         # Ray actor wrapper
└── ray_jobs/
    └── __init__.py               # Re-exports

tests/unit/
├── test_vllm_agent_base_unit.py  # Tests sin Ray
└── ray_jobs/
    └── test_vllm_agent_job_unit.py  # Tests con Ray (skipped si no disponible)
```

---

## 🔄 Plan de Migración

### Fase 1: Crear `VLLMAgentBase` (sin Ray)
1. Mover lógica core a nueva clase base
2. Sin dependencia de NATS
3. Solo lógica de vLLM API
4. Tests unitarios completos

### Fase 2: Refactorizar `VLLMAgentJob` (con Ray)
1. Heredar de `VLLMAgentBase`
2. Añadir lógica de NATS
3. Decorador `@ray.remote` siempre aplicado
4. Import condicional del módulo completo

### Fase 3: Actualizar Tests
1. Tests de `VLLMAgentBase`: Sin Ray, sin NATS
2. Tests de `VLLMAgentJob`: Con Ray (skipped si no disponible)
3. Tests de integración: Con vLLM real (opcional)

### Fase 4: Actualizar Use Cases
1. `DeliberateAsync`: Usar `VLLMAgentJob.remote()`
2. Tests: Usar `VLLMAgentBase` directamente
3. Documentación actualizada

---

## 🎯 Código Ejemplo

### vllm_agent_base.py
```python
"""Base vLLM agent implementation (no external dependencies)."""
import asyncio
import aiohttp
from typing import Any, Dict

class VLLMAgentBase:
    """Base implementation for vLLM agents."""
    
    def __init__(
        self,
        agent_id: str,
        role: str,
        vllm_url: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        self.agent_id = agent_id
        self.role = role
        self.vllm_url = vllm_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    async def generate_proposal(
        self,
        task: str,
        constraints: Dict[str, Any],
        diversity: bool = False
    ) -> Dict[str, Any]:
        """Generate proposal using vLLM API."""
        # Current implementation from VLLMAgentJobBase
        pass
    
    def _build_prompt(self, task: str, constraints: Dict[str, Any]) -> str:
        """Build prompt for vLLM."""
        pass
```

### vllm_agent_ray.py
```python
"""Ray actor wrapper for VLLMAgentBase."""
try:
    import ray
    from .vllm_agent_base import VLLMAgentBase
    
    @ray.remote(num_cpus=1, max_restarts=2)
    class VLLMAgentJob(VLLMAgentBase):
        """Ray remote actor for distributed vLLM execution."""
        
        def __init__(self, nats_url: str, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.nats_url = nats_url
            self.nc = None  # NATS connection
        
        async def run_async(
            self,
            task_id: str,
            task: str,
            constraints: Dict[str, Any],
            diversity: bool = False
        ):
            """Execute and publish result to NATS."""
            result = await self.generate_proposal(task, constraints, diversity)
            await self._publish_to_nats(task_id, result)
            return result
        
        async def _publish_to_nats(self, task_id: str, result: Dict[str, Any]):
            """Publish result to NATS."""
            pass

except ImportError:
    # Ray not available
    VLLMAgentJob = None
```

---

## 📊 Impacto

### Tests
- **Antes**: 3 tests fallando en CI (sin Ray)
- **Después**: Todos los tests pasando (VLLMAgentBase testeable sin Ray)

### Complejidad
- **Antes**: Lógica condicional en imports y decoradores
- **Después**: Dos clases claras y separadas

### Mantenibilidad
- **Antes**: Confuso cuándo usar cada variante
- **Después**: Claro: Base para tests, Job para producción

---

## ✅ Checklist de Implementación

- [ ] Crear `vllm_agent_base.py` con lógica core
- [ ] Mover tests a `test_vllm_agent_base_unit.py`
- [ ] Crear `vllm_agent_ray.py` con Ray actor
- [ ] Actualizar `DeliberateAsync` para usar nueva estructura
- [ ] Actualizar tests de integración
- [ ] Actualizar documentación
- [ ] Verificar CI pasa sin Ray
- [ ] Verificar producción funciona con Ray

---

## 🔗 Referencias

- Archivo actual: `src/swe_ai_fleet/orchestrator/ray_jobs/vllm_agent_job.py`
- Tests: `tests/unit/ray_jobs/test_vllm_agent_job_unit.py`
- Use case: `src/swe_ai_fleet/orchestrator/usecases/deliberate_async_usecase.py`
- Issue CI: AttributeError: module 'ray' has no attribute 'remote'

---

## 💭 Notas

- La solución actual (condicional) funciona pero es temporal
- Refactor mejorará la testabilidad y claridad
- No es urgente (workaround funciona)
- Prioridad media - cuando tengamos tiempo

---

**Creado**: 2025-10-11  
**Para revisar**: 2025-10-12  
**Estimación**: 2-3 horas de trabajo

