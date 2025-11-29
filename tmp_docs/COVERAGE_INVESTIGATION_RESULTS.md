# Investigación de Cobertura - Resultados

## Problema Identificado

El `coverage.json` de la raíz del proyecto muestra baja cobertura (32%) para los archivos implementados, pero cuando se ejecutan los tests individualmente con coverage específico, muestran buena cobertura.

## Hallazgos

### ✅ Archivos con BUENA cobertura cuando se ejecutan individualmente:

1. **`list_projects_usecase.py`**: **87.5%** (14/16 líneas)
   - Solo faltan 2 líneas (56-57): bloque defensivo `if projects is None`
   - Path en coverage.json: `application/usecases/list_projects_usecase.py`

2. **`project_neo4j_mapper.py`**: **100%** (30/30 líneas)
   - Cobertura completa
   - Path en coverage.json: `infrastructure/mappers/project_neo4j_mapper.py`

3. **`valkey_adapter.py`**: **35.14%** cuando se ejecuta con coverage específico
   - El código SÍ se está ejecutando
   - Path esperado: `infrastructure/adapters/valkey_adapter.py`

### ❌ Archivos NO encontrados en coverage.json general:

1. **`list_projects_handler.py`**: No aparece
   - Los tests ejecutan el handler pero mockean el use case
   - Debería ejecutar código del handler

2. **`neo4j_adapter.py`** (métodos de Project): No aparece en coverage.json
   - Los tests instancian Neo4jAdapter REAL con driver mockeado
   - Debería ejecutar código real

3. **`storage_adapter.py`** (métodos de Project): No aparece o tiene baja cobertura
   - Los tests instancian StorageAdapter REAL con adapters internos mockeados
   - Debería ejecutar código real

## Causa Raíz Identificada

**Warning de Coverage:**
```
Module planning was previously imported, but not measured (module-not-measured)
```

El módulo `planning` se importa **antes** de que coverage comience a medir, lo que causa que:
1. Los archivos no se rastreen correctamente en el coverage.json general
2. El coverage.json puede ser de una ejecución anterior o parcial
3. Los paths en coverage.json pueden no coincidir con los esperados

## Solución

### Opción 1: Ejecutar tests específicos con coverage para verificar cobertura real

```bash
# Para list_projects_usecase
pytest tests/unit/application/test_list_projects_usecase.py \
  --cov=application/usecases/list_projects_usecase \
  --cov-report=term-missing

# Para project_neo4j_mapper
pytest tests/unit/infrastructure/mappers/test_project_neo4j_mapper.py \
  --cov=infrastructure/mappers/project_neo4j_mapper \
  --cov-report=term-missing

# Para valkey_adapter (métodos de Project)
pytest tests/unit/infrastructure/test_valkey_adapter_projects.py \
  --cov=infrastructure/adapters/valkey_adapter \
  --cov-report=term-missing

# Para neo4j_adapter (métodos de Project)
pytest tests/unit/infrastructure/test_neo4j_adapter_projects.py \
  --cov=infrastructure/adapters/neo4j_adapter \
  --cov-report=term-missing

# Para storage_adapter
pytest tests/unit/infrastructure/test_storage_adapter.py \
  --cov=infrastructure/adapters/storage_adapter \
  --cov-report=term-missing

# Para list_projects_handler
pytest tests/unit/infrastructure/grpc/handlers/test_list_projects_handler.py \
  --cov=infrastructure/grpc/handlers/list_projects_handler \
  --cov-report=term-missing
```

### Opción 2: Ajustar la configuración de coverage para rastrear correctamente

El problema puede estar en que:
1. El módulo `planning` se importa antes de que coverage comience
2. Los paths en coverage.json no coinciden con los esperados
3. Necesitamos asegurar que coverage comience a medir antes de cualquier import

## Cobertura Real Estimada (basada en tests individuales)

| Archivo | Cobertura Real | Objetivo | Estado |
|---------|---------------|----------|--------|
| `list_projects_usecase.py` | 87.5% | 80-90% | ✅ CUMPLE |
| `project_neo4j_mapper.py` | 100% | 80-90% | ✅ CUMPLE |
| `valkey_adapter.py` (Project methods) | ~35%* | 80-90% | ❌ BAJO |
| `neo4j_adapter.py` (Project methods) | ? | 80-90% | ⚠️ DESCONOCIDO |
| `storage_adapter.py` (Project methods) | ? | 80-90% | ⚠️ DESCONOCIDO |
| `list_projects_handler.py` | ? | 80-90% | ⚠️ DESCONOCIDO |

*Cobertura cuando se ejecuta con coverage específico. Incluye todo el archivo, no solo métodos de Project.

## Próximos Pasos

1. ✅ Verificar que `list_projects_usecase.py` tiene buena cobertura (87.5%)
2. ✅ Verificar que `project_neo4j_mapper.py` tiene 100% cobertura
3. ⏳ Ejecutar tests individuales con coverage para obtener cobertura real de los otros archivos
4. ⏳ Identificar qué líneas faltan en cada archivo
5. ⏳ Agregar tests para cubrir las líneas faltantes


