# Context Service - Integration Roadmap ✅ COMPLETED

## 🎯 Executive Summary

**✅ INTEGRACIÓN COMPLETA** - Todos los use cases del Context Service han sido exitosamente integrados en `server.py` y funcionando en producción.

**Estado actual (2025-10-14)**:
- ✅ Use cases implementados: 6/6 (100%)
- ✅ Tests unitarios: 38 tests (100% passing)
- ✅ Tests E2E: **34 passing** (all enabled!)
- ✅ Integración en server.py: **6/6 use cases (100%) - COMPLETO**

---

## 📋 Use Cases Implementados vs Integrados

| Use Case | Implementado | Integrado en server.py | Tests E2E | Estado |
|----------|--------------|------------------------|-----------|---------|
| ProjectDecisionUseCase | ✅ | ✅ | ✅ 2 passing | 🟢 **DONE** |
| UpdateSubtaskStatusUseCase | ✅ | ✅ (consumers) | ✅ Indirect | 🟢 **DONE** |
| ProjectCaseUseCase | ✅ | ✅ | ✅ 2 passing | 🟢 **DONE** |
| ProjectSubtaskUseCase | ✅ | ✅ | ✅ 2 passing | 🟢 **DONE** |
| ProjectPlanVersionUseCase | ✅ | ✅ | ✅ 2 passing | 🟢 **DONE** |
| ProjectorCoordinator | ✅ | ✅ (implicit) | ✅ 1 passing | 🟢 **DONE** |

---

## ✅ Implementaciones Completadas (2025-10-11)

### 1. ProjectCaseUseCase - Proyectar Cases a Neo4j

**Archivo**: `src/swe_ai_fleet/context/usecases/project_case.py`

**¿Qué hace?**
- Proyecta entidades de tipo CASE a Neo4j
- Crea nodos `Case` con propiedades del caso
- Actualiza casos existentes

**¿Dónde integrarlo?**
`services/context/server.py` → método `_process_context_change()`

**Código a agregar**:
```python
# En _process_context_change(), dentro del switch por entity_type

elif entity_type == "CASE":
    # Usar ProjectCaseUseCase
    from swe_ai_fleet.context.usecases.project_case import ProjectCaseUseCase
    
    case_use_case = ProjectCaseUseCase(writer=self.graph_command)
    
    payload_dict = json.loads(change.payload) if change.payload else {}
    
    case_use_case.execute({
        "case_id": change.entity_id,
        "title": payload_dict.get("title"),
        "description": payload_dict.get("description"),
        "status": payload_dict.get("status"),
        "created_by": payload_dict.get("created_by"),
        "created_at": payload_dict.get("created_at"),
        # ... otros campos según necesites
    })
    
    logger.info(f"Projected CASE: {change.entity_id}")
```

**Tests que se habilitarán**:
- ✅ `test_project_case_e2e.py::TestProjectCaseE2E::test_create_case_node`
- ✅ `test_project_case_e2e.py::TestProjectCaseE2E::test_update_case_node`

---

### 2. ProjectSubtaskUseCase - Proyectar Subtasks a Neo4j

**Archivo**: `src/swe_ai_fleet/context/usecases/project_subtask.py`

**¿Qué hace?**
- Proyecta entidades de tipo SUBTASK a Neo4j
- Crea nodos `Subtask` con propiedades
- Vincula subtasks a cases (BELONGS_TO relationship)

**¿Dónde integrarlo?**
`services/context/server.py` → método `_process_context_change()`

**Código a agregar**:
```python
# En _process_context_change(), dentro del switch por entity_type

elif entity_type == "SUBTASK":
    # Usar ProjectSubtaskUseCase
    from swe_ai_fleet.context.usecases.project_subtask import ProjectSubtaskUseCase
    
    subtask_use_case = ProjectSubtaskUseCase(writer=self.graph_command)
    
    payload_dict = json.loads(change.payload) if change.payload else {}
    
    subtask_use_case.execute({
        "sub_id": change.entity_id,
        "description": payload_dict.get("description"),
        "role": payload_dict.get("role"),
        "status": payload_dict.get("status"),
        "priority": payload_dict.get("priority"),
        "case_id": payload_dict.get("case_id") or request.story_id,  # Link to case
        # ... otros campos
    })
    
    logger.info(f"Projected SUBTASK: {change.entity_id}")
```

**Tests que se habilitarán**:
- ✅ `test_project_subtask_e2e.py::TestProjectSubtaskE2E::test_create_subtask_node`
- ✅ `test_project_subtask_e2e.py::TestProjectSubtaskE2E::test_update_subtask_status`

---

### 3. ProjectPlanVersionUseCase - Proyectar Plans a Neo4j

**Archivo**: `src/swe_ai_fleet/context/usecases/project_plan_version.py`

**¿Qué hace?**
- Proyecta entidades de tipo PLAN a Neo4j
- Crea nodos `Plan` con versiones
- Mantiene historial de versiones de planes

**¿Dónde integrarlo?**
`services/context/server.py` → método `_process_context_change()`

**Código a agregar**:
```python
# En _process_context_change(), dentro del switch por entity_type

elif entity_type == "PLAN":
    # Usar ProjectPlanVersionUseCase
    from swe_ai_fleet.context.usecases.project_plan_version import ProjectPlanVersionUseCase
    
    plan_use_case = ProjectPlanVersionUseCase(writer=self.graph_command)
    
    payload_dict = json.loads(change.payload) if change.payload else {}
    
    plan_use_case.execute({
        "plan_id": change.entity_id,
        "version": payload_dict.get("version", 1),
        "status": payload_dict.get("status"),
        "total_subtasks": payload_dict.get("total_subtasks", 0),
        "completed_subtasks": payload_dict.get("completed_subtasks", 0),
        "created_by": payload_dict.get("created_by"),
        "created_at": payload_dict.get("created_at"),
        # ... otros campos
    })
    
    logger.info(f"Projected PLAN: {change.entity_id} (version {payload_dict.get('version', 1)})")
```

**Tests que se habilitarán**:
- ✅ `test_project_plan_e2e.py::TestProjectPlanVersionE2E::test_create_plan_node`
- ✅ `test_project_plan_e2e.py::TestProjectPlanVersionE2E::test_track_plan_versions`

---

### 4. ProjectorCoordinator - Orquestar Múltiples Proyecciones

**Archivo**: `src/swe_ai_fleet/context/usecases/projector_coordinator.py`

**¿Qué hace?**
- Coordina la ejecución de múltiples use cases de proyección
- Rutea cada tipo de entidad al use case correcto
- Maneja errores individuales sin fallar todo el batch

**¿Dónde integrarlo?**
`services/context/server.py` → método `UpdateContext()`

**Opción 1: Refactorizar para usar Coordinator** (Recomendado)
```python
# En UpdateContext(), reemplazar el loop manual por:

from swe_ai_fleet.context.usecases.projector_coordinator import ProjectorCoordinator

# Inicializar coordinator
coordinator = ProjectorCoordinator(
    case_projector=ProjectCaseUseCase(writer=self.graph_command),
    subtask_projector=ProjectSubtaskUseCase(writer=self.graph_command),
    plan_projector=ProjectPlanVersionUseCase(writer=self.graph_command),
    decision_projector=ProjectDecisionUseCase(writer=self.graph_command),
)

# Procesar todos los cambios
for change in request.changes:
    try:
        coordinator.process_change(
            entity_type=change.entity_type,
            entity_id=change.entity_id,
            payload=json.loads(change.payload) if change.payload else {},
            story_id=request.story_id,
        )
    except Exception as e:
        logger.error(f"Error processing {change.entity_type}: {e}")
        # Continuar con los demás cambios
```

**Opción 2: Usar directamente los use cases** (Más simple)
```python
# Mantener el enfoque actual pero agregar los casos faltantes
# en _process_context_change() como se mostró arriba
```

**Tests que se habilitarán**:
- ✅ `test_projector_coordinator_e2e.py::TestProjectorCoordinatorE2E::test_handle_multiple_entity_types_in_one_request`

---

## 📝 Paso a Paso para Implementar

### Paso 1: Backup del server.py actual
```bash
cp services/context/server.py services/context/server.py.backup
```

### Paso 2: Agregar imports al inicio de server.py
```python
# En la sección de imports, agregar:
from swe_ai_fleet.context.usecases.project_case import ProjectCaseUseCase
from swe_ai_fleet.context.usecases.project_subtask import ProjectSubtaskUseCase
from swe_ai_fleet.context.usecases.project_plan_version import ProjectPlanVersionUseCase
# Opcional: from swe_ai_fleet.context.usecases.projector_coordinator import ProjectorCoordinator
```

### Paso 3: Extender el método `_process_context_change()`

**Ubicación actual**: `services/context/server.py` línea ~430

**Estado actual**:
```python
def _process_context_change(self, change, request):
    """Process a single context change."""
    entity_type = change.entity_type
    
    if entity_type == "DECISION":
        # ... código existente para decisions ...
    
    elif entity_type == "SUBTASK":
        # ... código existente para subtask status ...
    
    elif entity_type == "MILESTONE":
        # ... código existente para milestones ...
    
    # ❌ AQUÍ FALTAN: CASE, PLAN, y otros
```

**Estado deseado**:
```python
def _process_context_change(self, change, request):
    """Process a single context change."""
    entity_type = change.entity_type
    
    if entity_type == "DECISION":
        # ... código existente ...
    
    elif entity_type == "CASE":
        # ✅ AGREGAR: Proyección de cases
        self._persist_case_change(change, request)
    
    elif entity_type == "SUBTASK":
        # Extender: Proyección completa de subtasks (no solo status)
        self._persist_subtask_change(change, request)
    
    elif entity_type == "PLAN":
        # ✅ AGREGAR: Proyección de planes
        self._persist_plan_change(change, request)
    
    elif entity_type == "MILESTONE":
        # ... código existente ...
```

### Paso 4: Implementar los métodos helper

```python
def _persist_case_change(self, change, request):
    """Persist CASE entity to Neo4j."""
    try:
        case_use_case = ProjectCaseUseCase(writer=self.graph_command)
        payload = json.loads(change.payload) if change.payload else {}
        
        case_use_case.execute({
            "case_id": change.entity_id,
            **payload  # Spread all payload fields
        })
        
        logger.info(f"✓ Projected CASE: {change.entity_id}")
    except Exception as e:
        logger.error(f"Failed to project CASE {change.entity_id}: {e}")
        raise

def _persist_subtask_change(self, change, request):
    """Persist SUBTASK entity to Neo4j (complete projection, not just status)."""
    try:
        # Si solo es update de status, usar UpdateSubtaskStatusUseCase (existente)
        payload = json.loads(change.payload) if change.payload else {}
        
        if change.operation == "UPDATE" and "status" in payload and len(payload) == 1:
            # Solo actualización de status (código existente)
            self.update_subtask_status_use_case.execute({
                "sub_id": change.entity_id,
                "status": payload["status"]
            })
        else:
            # Proyección completa del subtask
            subtask_use_case = ProjectSubtaskUseCase(writer=self.graph_command)
            subtask_use_case.execute({
                "sub_id": change.entity_id,
                "case_id": request.story_id,  # Link to parent case
                **payload
            })
        
        logger.info(f"✓ Projected SUBTASK: {change.entity_id}")
    except Exception as e:
        logger.error(f"Failed to project SUBTASK {change.entity_id}: {e}")
        raise

def _persist_plan_change(self, change, request):
    """Persist PLAN entity to Neo4j."""
    try:
        plan_use_case = ProjectPlanVersionUseCase(writer=self.graph_command)
        payload = json.loads(change.payload) if change.payload else {}
        
        plan_use_case.execute({
            "plan_id": change.entity_id,
            **payload
        })
        
        logger.info(f"✓ Projected PLAN: {change.entity_id}")
    except Exception as e:
        logger.error(f"Failed to project PLAN {change.entity_id}: {e}")
        raise
```

### Paso 5: Remover `@pytest.mark.skip` de los tests

Una vez implementado, editar los archivos de test y remover:

```python
# ANTES:
@pytest.mark.skip(reason="ProjectCaseUseCase not yet integrated in UpdateContext server")
def test_create_case_node(self, context_stub, neo4j_client):

# DESPUÉS:
def test_create_case_node(self, context_stub, neo4j_client):
```

**Archivos a editar**:
- `tests/e2e/services/context/test_project_case_e2e.py` (2 decorators)
- `tests/e2e/services/context/test_project_subtask_e2e.py` (2 decorators)
- `tests/e2e/services/context/test_project_plan_e2e.py` (2 decorators)
- `tests/e2e/services/context/test_projector_coordinator_e2e.py` (1 decorator)

### Paso 6: Ejecutar tests E2E

```bash
cd /home/tirso/ai/developents/swe-ai-fleet
bash tests/e2e/services/context/run-e2e.sh
```

**Resultado esperado**:
```
============================== 34 passed in 18s ==============================
```

---

## ✅ Checklist de Implementación

- [x] Backup de `server.py`
- [x] Agregar imports de use cases faltantes
- [x] Implementar `_persist_case_change()`
- [x] Implementar `_persist_plan_change()`
- [x] Extender `_persist_subtask_change()` para proyección completa
- [x] Actualizar `_process_context_change()` con nuevos casos
- [x] Remover `@pytest.mark.skip` de 7 tests
- [x] Ejecutar tests E2E
- [x] Verificar 34 tests passing
- [x] Build y push nueva imagen del Context Service
- [x] Deploy a Kubernetes
- [x] Ejecutar smoke tests en K8s

---

## 🎯 Beneficios de Completar la Integración

1. **Visibilidad completa**: Todos los cambios de contexto se proyectan a Neo4j
2. **Queries más ricas**: Se pueden hacer consultas complejas sobre cases, plans, subtasks
3. **Debugging mejorado**: Ver el estado completo en Neo4j Browser
4. **Event sourcing**: Base para reconstruir estado desde eventos
5. **Tests E2E completos**: 100% de cobertura de use cases

---

## 📊 Impacto Estimado

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| Use cases integrados | 2/6 (33%) | 6/6 (100%) | +200% |
| Tests E2E passing | 27 | 34 | +26% |
| Entidades proyectadas | 2 tipos | 5 tipos | +150% |
| Tiempo implementación | - | ~2-3 horas | - |

---

## 🚀 Próximos Pasos Después de la Integración

1. **Crear índices en Neo4j** para mejorar performance
2. **Agregar constraints** para integridad de datos
3. **Implementar cleanup de datos antiguos**
4. **Agregar métricas** de proyección exitosa/fallida
5. **Documentar el schema de Neo4j** resultante

---

## 📚 Referencias

- **Use Cases**: `src/swe_ai_fleet/context/usecases/`
- **Server actual**: `services/context/server.py`
- **Tests E2E**: `tests/e2e/services/context/test_project_*.py`
- **Unit tests**: `tests/unit/context/usecases/` (todos passing ✅)

---

## ❓ FAQ

**Q: ¿Por qué no están integrados si ya están implementados?**  
A: Se priorizó primero la funcionalidad de decisions y consumers para el flujo crítico.

**Q: ¿Puedo implementar solo algunos use cases?**  
A: Sí, puedes hacerlo incremental. Cada use case es independiente.

**Q: ¿Qué pasa si un use case falla?**  
A: El error se loguea pero no rompe el procesamiento de otros cambios.

**Q: ¿Necesito rebuild del container?**  
A: Sí, después de modificar `server.py` necesitas rebuild y redeploy.

**Q: ¿Los tests E2E corren en CI?**  
A: Sí, una vez que pasan localmente, correrán en CI automáticamente.

---

**Última actualización**: 2025-10-14  
**Autor**: SWE AI Fleet Team  
**Status**: 🟢 **COMPLETED** - All use cases integrated and tested

