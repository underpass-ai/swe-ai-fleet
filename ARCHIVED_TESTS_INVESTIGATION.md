# Investigación: Tests Archived

**Fecha**: 2025-10-12  
**Objetivo**: Verificar si los tests archived deben estar archivados o pueden rescatarse

---

## 📋 Tests Investigados (6 total)

### 1. test_context_assembler_e2e.py

**Import roto**:
```python
from swe_ai_fleet.memory.redis_store import RedisKvPort  # ❌ Ruta incorrecta
```

**Ruta correcta**:
```python
from swe_ai_fleet.memory.adapters.redis_store import RedisKvPort  # ✅
```

**¿Qué testea?**:
- `build_prompt_blocks()` end-to-end
- ✅ **Secret redaction** (passwords, Bearer tokens)
- Scope policies application
- Session rehydration completa

**Veredicto**: 🟡 **RESCATABLE**
- Solo necesita arreglar import
- Funcionalidad importante (secret redaction)
- Test valioso para seguridad

**Acción**: Arreglar import y mover a tests activos

---

### 2. test_redis_store_e2e.py

**Código**:
```python
def test_save_to_redis_e2e():
    store = RedisStore(...)
    store.save_llm_call(dto)
    # Test básico de guardado
```

**Problema**:
- Requiere Redis con password específico
- Test muy básico (solo save)
- Ya cubierto por unit tests

**Veredicto**: ❌ **MANTENER ARCHIVED**
- Test demasiado simple
- Ya cubierto por tests unitarios
- No aporta valor adicional

**Acción**: Mantener archived

---

### 3. test_session_rehydration_e2e.py

**Import roto**:
```python
from swe_ai_fleet.memory.redis_store import RedisKvPort  # ❌
```

**¿Qué testea?**:
- `SessionRehydrationUseCase` con múltiples roles
- Handoff bundles con TTL
- Decision relevance filtering por role
- Timeline event ordering

**Veredicto**: 🟡 **RESCATABLE**
- Funcionalidad importante
- Test complejo y valioso
- Solo necesita arreglar import

**Acción**: Arreglar import y mover a tests activos

---

### 4. test_decision_enriched_report_e2e.py

**Imports**: ✅ Todos correctos

**¿Qué testea?**:
- DecisionEnrichedReportUseCase
- Reports con decisions, dependencies, impacts
- Markdown-formatted reports

**Veredicto**: 🟢 **RESCATABLE**
- Imports correctos
- Funcionalidad valiosa (reports)
- Solo necesita Redis

**Acción**: Mover a tests activos

---

### 5. test_report_usecase_e2e.py

**Imports**: ✅ Todos correctos

**¿Qué testea?**:
- ImplementationReportUseCase con **graph analytics**
- Critical decisions (by indegree score)
- Cycle detection in decision graphs
- Topological layers
- Analytics con empty results (edge case)

**Veredicto**: 🟢 **RESCATABLE**
- Imports correctos
- Funcionalidad crítica (graph analytics es diferenciador)
- Test complejo y valioso

**Acción**: Mover a tests activos

---

### 6. test_persistence_integration.py

**Problema**:
- Requiere `services.context.server` (existe pero es Go, no Python)
- Requiere fixture `neo4j_connection` no definida
- Tests de scope detection fallan

**Veredicto**: ❌ **MANTENER ARCHIVED**
- Desactualizado (arquitectura vieja)
- Requiere refactoring completo
- Ya cubierto por test_persistence_e2e.py

**Acción**: Mantener archived

---

## 📊 Resumen Final

| Test | Import OK | Rescatable | Prioridad |
|------|-----------|------------|-----------|
| test_context_assembler_e2e.py | ❌ | 🟡 Sí | Alta (security) |
| test_session_rehydration_e2e.py | ❌ | 🟡 Sí | Alta (core feature) |
| test_decision_enriched_report_e2e.py | ✅ | 🟢 Sí | Media (reports) |
| test_report_usecase_e2e.py | ✅ | 🟢 Sí | Alta (analytics) |
| test_redis_store_e2e.py | ❌ | ❌ No | Baja (trivial) |
| test_persistence_integration.py | ⚠️ | ❌ No | Baja (obsoleto) |

---

## 🎯 Plan de Rescate

### Prioridad Alta (2 tests)

#### 1. test_context_assembler_e2e.py
```python
# Arreglar import:
from swe_ai_fleet.memory.adapters.redis_store import RedisKvPort  # ✅
```
- Test de secret redaction (crítico para seguridad)
- Requiere: Redis con password

#### 2. test_session_rehydration_e2e.py
```python
# Arreglar import:
from swe_ai_fleet.memory.adapters.redis_store import RedisKvPort  # ✅
```
- Test de session rehydration completa
- Requiere: Redis con password

### Prioridad Media-Alta (2 tests)

#### 3. test_report_usecase_e2e.py
- ✅ Imports correctos
- Test de graph analytics (diferenciador del proyecto)
- Requiere: Redis + Neo4j (para analytics)

#### 4. test_decision_enriched_report_e2e.py
- ✅ Imports correctos
- Test de reports enriquecidos
- Requiere: Redis

### Mantener Archived (2 tests)

#### 5. test_redis_store_e2e.py
- Test trivial (solo save)
- Ya cubierto por unit tests

#### 6. test_persistence_integration.py
- Arquitectura obsoleta
- Ya cubierto por test_persistence_e2e.py

---

## ✅ Acción Recomendada

1. **Arreglar imports** en 2 tests (context_assembler, session_rehydration)
2. **Mover 4 tests** de archived → integration
3. **Mantener 2 tests** en archived (redis_store, persistence_integration)
4. **Actualizar archived/README.md** con razones claras

