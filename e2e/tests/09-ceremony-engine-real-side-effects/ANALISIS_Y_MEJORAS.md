# Análisis del Test E2E: Ceremony Engine Real Side-Effects

## Estado Actual del Test

### ¿Qué hace el test actualmente?

El test `09-ceremony-engine-real-side-effects` valida que el motor de ceremonias produce efectos secundarios reales en un entorno Kubernetes desplegado:

1. **Inicia una ceremonia** vía gRPC (`StartPlanningCeremony`)
2. **Verifica mensajes NATS** publicados en JetStream
3. **Verifica persistencia en Valkey** (instancia de ceremonia)
4. **Verifica persistencia en Neo4j** (nodo de instancia)

### ¿Contempla tareas en el backlog?

**❌ NO.** El test actual:

- Usa `dummy_ceremony.yaml`, una ceremonia mínima que:
  - Solo tiene un step de tipo `aggregation_step`
  - No requiere datos del backlog (stories, tasks, etc.)
  - No ejecuta pasos que necesiten contexto del Planning Service
  - No valida flujos de planificación reales

- El `dummy_ceremony` es puramente sintético:
  ```yaml
  steps:
    - id: process_step
      state: STARTED
      handler: aggregation_step
      config:
        sources:
          - input_data  # Solo agrega datos de entrada, no del backlog
        aggregation_type: merge
  ```

### ¿Puebla las bases de datos con datos necesarios?

**❌ NO.** El test actual:

- **NO crea datos previos** en Valkey o Neo4j
- **NO crea proyectos, épicas, o stories** en el Planning Service
- **NO crea tareas** en el backlog
- Solo **verifica** que la instancia de ceremonia se persiste después de iniciarla

- El test asume que:
  - Las bases de datos están vacías o tienen datos no relacionados
  - La ceremonia puede ejecutarse sin datos previos
  - No necesita contexto del Planning Service

## Limitaciones del Test Actual

### 1. **Ceremonia no realista**

El `dummy_ceremony` es demasiado simple y no representa un caso de uso real:

- No ejecuta pasos que requieran datos del backlog
- No valida integración con Planning Service
- No prueba flujos de planificación completos
- No verifica que los steps puedan acceder a datos externos

### 2. **Falta de datos de prueba**

El test no prepara el entorno con datos necesarios:

- **Planning Service**: No hay proyectos, épicas, o stories
- **Neo4j**: No hay nodos de `Story`, `Task`, o `Project`
- **Valkey**: No hay datos de contexto previos
- **Context Service**: No hay contexto rehidratado

### 3. **No valida flujos completos**

El test solo valida efectos secundarios básicos:

- ✅ Persistencia de instancia
- ✅ Publicación de mensajes NATS
- ❌ **NO valida** que los steps puedan leer datos del backlog
- ❌ **NO valida** que los steps puedan crear tareas
- ❌ **NO valida** que los steps puedan acceder a contexto

## Propuestas de Mejora

### Opción 1: Preparar datos antes del test (Recomendado)

**Enfoque**: El test debe preparar datos necesarios antes de ejecutar la ceremonia.

#### Implementación sugerida:

1. **Crear datos de prueba** (similar a `02-create-test-data`):
   ```python
   async def prepare_test_data(self) -> bool:
       """Prepare test data: project, epic, stories."""
       # 1. Crear proyecto vía Planning Service gRPC
       # 2. Crear épica
       # 3. Crear stories
       # 4. Verificar que existen en Neo4j
   ```

2. **Usar una ceremonia más realista**:
   - Crear `planning_ceremony.yaml` que:
     - Requiera `story_id` en inputs
     - Ejecute steps que lean datos del backlog
     - Valide que puede acceder a Planning Service

3. **Verificar acceso a datos**:
   ```python
   async def test_step_verify_backlog_access(self) -> bool:
       """Verify ceremony can access backlog data."""
       # Query Neo4j para verificar stories existen
       # Query Planning Service para verificar stories
   ```

#### Ventajas:
- ✅ Valida flujo completo de planificación
- ✅ Prueba integración real con Planning Service
- ✅ Verifica que los steps pueden acceder a datos externos
- ✅ Más realista y útil para detectar problemas

#### Desventajas:
- ⚠️ Test más complejo y lento
- ⚠️ Requiere Planning Service desplegado
- ⚠️ Necesita limpieza de datos después del test

### Opción 2: Test separado para flujos completos

**Enfoque**: Mantener el test actual simple y crear un nuevo test para flujos completos.

#### Implementación sugerida:

1. **Mantener `09-ceremony-engine-real-side-effects`** como está:
   - Valida efectos secundarios básicos
   - Usa `dummy_ceremony` simple
   - Rápido y enfocado

2. **Crear `11-ceremony-engine-planning-integration`**:
   - Prepara datos de prueba
   - Usa ceremonia realista
   - Valida acceso a backlog
   - Valida creación de tareas

#### Ventajas:
- ✅ Separación de responsabilidades
- ✅ Test básico sigue siendo rápido
- ✅ Test completo valida flujos reales

#### Desventajas:
- ⚠️ Más tests para mantener
- ⚠️ Duplicación de código de setup

### Opción 3: Hacer el test opcionalmente dependiente de datos

**Enfoque**: El test puede funcionar con o sin datos previos.

#### Implementación sugerida:

1. **Detección automática de datos**:
   ```python
   async def check_test_data_exists(self) -> bool:
       """Check if test data exists in Planning Service."""
       # Query Planning Service para proyecto "Test de swe fleet"
       return exists
   ```

2. **Crear datos si no existen**:
   ```python
   async def ensure_test_data(self) -> bool:
       """Ensure test data exists, create if needed."""
       if not await self.check_test_data_exists():
           return await self.create_test_data()
       return True
   ```

3. **Usar ceremonia apropiada**:
   - Si hay datos: usar `planning_ceremony.yaml` (realista)
   - Si no hay datos: usar `dummy_ceremony.yaml` (básico)

#### Ventajas:
- ✅ Flexible: funciona con o sin datos
- ✅ Puede reutilizar datos de otros tests
- ✅ No requiere limpieza si datos ya existen

#### Desventajas:
- ⚠️ Lógica más compleja
- ⚠️ Puede ser menos predecible

## Recomendación

**Recomendamos la Opción 1** (Preparar datos antes del test) porque:

1. **Valida flujos reales**: El test verifica que el motor de ceremonias puede trabajar con datos reales del backlog
2. **Detecta problemas de integración**: Puede encontrar problemas que el test básico no detectaría
3. **Más útil para CI/CD**: Un test que valida flujos completos es más valioso en pipelines

### Plan de Implementación

1. **Fase 1: Preparación de datos**
   - Agregar método `prepare_test_data()` que cree proyecto, épica, y stories
   - Reutilizar lógica de `02-create-test-data` si es posible

2. **Fase 2: Ceremonia realista**
   - Crear `planning_ceremony.yaml` que requiera `story_id`
   - Agregar steps que validen acceso a datos del backlog

3. **Fase 3: Verificaciones adicionales**
   - Verificar que los steps pueden leer stories de Neo4j
   - Verificar que los steps pueden crear tareas (si aplica)
   - Verificar que el contexto se rehidrata correctamente

4. **Fase 4: Limpieza opcional**
   - Agregar flag `PRESERVE_DATA` (similar a `02-create-test-data`)
   - Permitir limpiar datos después del test si se desea

## Comparación con Otros Tests E2E

### `02-create-test-data`
- ✅ Crea proyecto, épica, y stories
- ✅ Prepara datos para otros tests
- ❌ No ejecuta ceremonias

### `04-start-backlog-review-ceremony`
- ✅ Inicia ceremonia de backlog review
- ✅ Requiere datos previos (ejecuta `02-create-test-data` primero)
- ✅ Valida flujo completo de backlog review

### `09-ceremony-engine-real-side-effects` (actual)
- ✅ Valida efectos secundarios básicos
- ❌ No requiere datos previos
- ❌ No valida acceso a backlog

### `11-ceremony-engine-planning-integration` (propuesto)
- ✅ Requiere datos previos
- ✅ Valida acceso a backlog
- ✅ Valida flujos completos de planificación

## Conclusión

El test actual **NO contempla tareas en el backlog** y **NO puebla las bases de datos** con datos necesarios. Es un test básico que valida efectos secundarios mínimos.

Para hacer el test más útil y realista, recomendamos:

1. **Agregar preparación de datos** antes de ejecutar la ceremonia
2. **Usar una ceremonia más realista** que requiera datos del backlog
3. **Validar acceso a datos** durante la ejecución de la ceremonia

Esto haría el test más valioso para detectar problemas de integración y validar flujos completos de planificación.
