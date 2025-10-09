# Análisis de Impacto: Mover Context a bounded_contexts/

## 📋 Propuesta

Mover el bounded context `context` desde:
```
src/swe_ai_fleet/context/
```

Hacia:
```
bounded_contexts/context/
```

## 🔍 Análisis de Dependencias

### Archivos que Importan `swe_ai_fleet.context`

#### 1. **Microservicio Context** (services/context/)
- `services/context/server.py` - **6 imports**
  ```python
  from swe_ai_fleet.context.context_assembler import build_prompt_blocks
  from swe_ai_fleet.context.session_rehydration import SessionRehydrationUseCase, RehydrationRequest
  from swe_ai_fleet.context.domain.scopes.prompt_scope_policy import PromptScopePolicy
  from swe_ai_fleet.context.adapters.neo4j_query_store import Neo4jQueryStore
  from swe_ai_fleet.context.adapters.neo4j_command_store import Neo4jCommandStore
  from swe_ai_fleet.context.adapters.redis_planning_read_adapter import RedisPlanningReadAdapter
  ```

#### 2. **Orchestrator** (src/swe_ai_fleet/orchestrator/)
- `orchestrator/handler/agent_job_worker.py` - **Imports context**

#### 3. **Reports** (src/swe_ai_fleet/reports/)
- `reports/adapters/neo4j_decision_graph_read_adapter.py`
- `reports/adapters/neo4j_graph_analytics_read_adapter.py`

#### 4. **Tests** (~15 archivos)
- `tests/e2e/test_context_assembler_e2e.py`
- `tests/e2e/test_session_rehydration_e2e.py`
- `tests/unit/test_context_*.py` (múltiples archivos)
- `tests/unit/test_projector_*.py`
- `tests/unit/test_neo4j_command_store_unit.py`

#### 5. **Scripts**
- `scripts/seed_context_example.py`

#### 6. **Imports Internos** (dentro del propio context/)
- 12 archivos dentro de `src/swe_ai_fleet/context/` que se importan entre sí

### Total de Archivos Afectados: **~26 archivos**

## 📊 Impacto Detallado

### 🔴 Alto Impacto

#### 1. **Microservicio Context** (services/context/server.py)
**Impacto:** CRÍTICO
- Es el principal consumidor del bounded context
- Requiere actualizar 6 imports
- Requiere actualizar PYTHONPATH en Dockerfile
- Requiere actualizar sys.path en server.py

**Cambios necesarios:**
```python
# Antes
from swe_ai_fleet.context.context_assembler import build_prompt_blocks

# Después
from bounded_contexts.context.context_assembler import build_prompt_blocks
```

#### 2. **Orchestrator**
**Impacto:** ALTO
- Usa context para hidratar prompts de agentes
- Requiere actualizar imports
- Puede romper la ejecución de agentes

#### 3. **Tests (26 archivos)**
**Impacto:** ALTO
- Todos los tests de context necesitan actualización
- Tests E2E que validan el flujo completo
- Tests unitarios de cada componente

### 🟡 Medio Impacto

#### 4. **Reports Module**
**Impacto:** MEDIO
- Usa adaptadores de context (Neo4j)
- Posible duplicación de código
- Considerar si reports también debería moverse

#### 5. **Scripts**
**Impacto:** MEDIO
- Scripts de seed y ejemplos
- Fácil de actualizar pero críticos para demos

### 🟢 Bajo Impacto

#### 6. **Documentación**
**Impacto:** BAJO
- Actualizar referencias en docs
- Actualizar ejemplos de código

## ⚠️ Riesgos Identificados

### 1. **Ruptura del Microservicio Context**
- **Riesgo:** CRÍTICO
- **Probabilidad:** ALTA si no se actualiza correctamente
- **Impacto:** El microservicio no arrancará
- **Mitigación:** 
  - Actualizar Dockerfile con nuevo PYTHONPATH
  - Actualizar sys.path.insert() en server.py
  - Probar build y ejecución local antes de deploy

### 2. **Ruptura de Tests**
- **Riesgo:** ALTO
- **Probabilidad:** 100% (todos los tests fallarán)
- **Impacto:** CI/CD fallará, no se puede hacer merge
- **Mitigación:**
  - Actualizar todos los imports en tests
  - Ejecutar suite completa de tests
  - Verificar coverage no disminuye

### 3. **Ruptura de Orchestrator**
- **Riesgo:** CRÍTICO
- **Probabilidad:** ALTA
- **Impacto:** Agentes no podrán ejecutarse
- **Mitigación:**
  - Actualizar imports en agent_job_worker.py
  - Probar ejecución de agentes end-to-end

### 4. **Imports Circulares**
- **Riesgo:** MEDIO
- **Probabilidad:** BAJA
- **Impacto:** Errores de importación difíciles de debuggear
- **Mitigación:**
  - Revisar dependencias entre bounded contexts
  - Mantener separación clara

### 5. **Deployment y CI/CD**
- **Riesgo:** ALTO
- **Probabilidad:** ALTA
- **Impacto:** Builds fallarán
- **Mitigación:**
  - Actualizar pyproject.toml
  - Actualizar setup.py si existe
  - Actualizar CI/CD workflows

## 🛠️ Cambios Necesarios

### 1. Estructura de Directorios

```
bounded_contexts/
└── context/
    ├── __init__.py
    ├── adapters/
    ├── domain/
    ├── ports/
    ├── usecases/
    ├── context_assembler.py
    ├── session_rehydration.py
    └── utils.py
```

### 2. Actualizar pyproject.toml

```toml
[tool.setuptools.packages.find]
where = ["src", "bounded_contexts"]
namespaces = false
```

### 3. Actualizar Dockerfile del Microservicio

```dockerfile
# Antes
COPY src/ /app/src/
ENV PYTHONPATH=/app/src:/app

# Después
COPY src/ /app/src/
COPY bounded_contexts/ /app/bounded_contexts/
ENV PYTHONPATH=/app/src:/app/bounded_contexts:/app
```

### 4. Actualizar server.py

```python
# Antes
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Después
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../bounded_contexts"))
```

### 5. Actualizar Todos los Imports

**Archivos a modificar: ~26 archivos**

```python
# Antes
from swe_ai_fleet.context.X import Y

# Después  
from bounded_contexts.context.X import Y
```

## 📝 Plan de Migración Sugerido

### Fase 1: Preparación (Sin Romper Nada)
1. ✅ Crear `bounded_contexts/` directory
2. ✅ Copiar (no mover) `context/` a `bounded_contexts/context/`
3. ✅ Actualizar pyproject.toml para incluir ambas ubicaciones
4. ✅ Verificar que tests siguen pasando

### Fase 2: Actualizar Referencias
5. ⚠️ Actualizar imports en `services/context/server.py`
6. ⚠️ Actualizar imports en `orchestrator/`
7. ⚠️ Actualizar imports en `reports/`
8. ⚠️ Actualizar imports en todos los tests
9. ⚠️ Actualizar scripts

### Fase 3: Actualizar Infraestructura
10. ⚠️ Actualizar Dockerfile
11. ⚠️ Actualizar PYTHONPATH en todos los lugares
12. ⚠️ Actualizar CI/CD si aplica

### Fase 4: Validación
13. ✅ Ejecutar todos los tests
14. ✅ Verificar build del microservicio
15. ✅ Probar deployment local
16. ✅ Verificar que orchestrator funciona

### Fase 5: Limpieza
17. ✅ Eliminar `src/swe_ai_fleet/context/` (la ubicación vieja)
18. ✅ Actualizar documentación
19. ✅ Commit y push

## 🎯 Recomendaciones

### ✅ RECOMIENDO HACER EL MOVE SI:

1. **Quieres separación clara** entre bounded contexts y código de aplicación
2. **Planeas agregar más bounded contexts** (planning, workspace, etc.)
3. **Quieres arquitectura hexagonal/DDD más explícita**
4. **Tienes tiempo para actualizar ~26 archivos y probar exhaustivamente**

### ❌ NO RECOMIENDO HACER EL MOVE SI:

1. **Estás en medio de desarrollo activo** de features
2. **No tienes tiempo para probar exhaustivamente**
3. **El CI/CD es frágil** y puede romperse fácilmente
4. **Hay PRs abiertos** que conflictarían

## 🔧 Script de Migración Automática

Puedo crear un script que:
1. Mueva los archivos
2. Actualice todos los imports automáticamente
3. Actualice configuraciones
4. Ejecute tests para validar

## 💡 Alternativa: Organización Híbrida

Mantener la estructura actual pero agregar symlinks o aliases:

```
src/swe_ai_fleet/context/  (mantener aquí)
bounded_contexts/
└── context -> ../src/swe_ai_fleet/context/  (symlink)
```

**Ventajas:**
- No rompe nada existente
- Permite nueva organización conceptual
- Sin cambios en imports

**Desventajas:**
- No es una separación "real"
- Puede confundir

## 📊 Resumen de Impacto

| Componente | Archivos Afectados | Riesgo | Esfuerzo |
|------------|-------------------|--------|----------|
| Microservicio Context | 1 | 🔴 CRÍTICO | 2h |
| Orchestrator | 1 | 🔴 ALTO | 1h |
| Reports | 2 | 🟡 MEDIO | 1h |
| Tests | ~20 | 🔴 ALTO | 3h |
| Scripts | 1 | 🟢 BAJO | 30min |
| Infraestructura | 3 | 🔴 ALTO | 2h |
| Documentación | ~5 | 🟢 BAJO | 1h |
| **TOTAL** | **~33** | **🔴 ALTO** | **~10-12h** |

## 🎬 ¿Qué Quieres Hacer?

### Opción A: **Hacer el Move Ahora** (Recomendado si tienes tiempo)
- Ejecuto migración completa
- Actualizo todos los imports
- Pruebo exhaustivamente
- Tiempo estimado: 10-12 horas

### Opción B: **Hacer el Move Después**
- Dejamos como está por ahora
- Planificamos para un momento con menos cambios activos
- Creamos un issue/ticket para trackear

### Opción C: **Solución Híbrida**
- Creamos `bounded_contexts/` con symlinks
- No rompemos nada
- Migración gradual

### Opción D: **Solo Documentar la Intención**
- Agregamos comentarios indicando que es un bounded context
- Mantenemos estructura actual
- Documentamos en arquitectura

¿Cuál opción prefieres?
