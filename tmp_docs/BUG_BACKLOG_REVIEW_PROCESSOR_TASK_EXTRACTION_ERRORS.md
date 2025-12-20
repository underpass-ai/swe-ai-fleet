# Bug Report: Errores en Task Extraction del Backlog Review Processor

**Fecha:** 2025-12-20
**Severidad:** Alta
**Estado:** ✅ SOLUCIÓN IDENTIFICADA
**Componente:** Backlog Review Processor - TaskExtractionResultConsumer
**Test E2E Relacionado:** `05-validate-deliberations-and-tasks`

**Solución Identificada:**
- Configurar `--reasoning-parser qwen3` en vLLM server (separar reasoning de content)
- Usar `response_format: json_schema` (strict) en requests (schema enforcement)
- Consumir solo `message.content` (JSON limpio, sin `<think>`)
- **NO desactivar thinking** (mantiene precisión)

---

## Resumen Ejecutivo

Durante la ejecución del test E2E `05-validate-deliberations-and-tasks`, se han identificado errores masivos en el procesamiento de resultados de extracción de tareas (Task Extraction) en el Backlog Review Processor. El consumer `TaskExtractionResultConsumer` está recibiendo eventos NATS con respuestas JSON inválidas o vacías, causando que todas las tareas extraídas fallen al procesarse.

**Fase del Diagrama que Falla:**
- **Paso 13** del diagrama `BACKLOG_REVIEW_FLOW_NO_STYLES.md`
- **Flujo:** `VLLM_TASK -.-> BRP` (NATS - VLLM response, TaskId, StoryID)
- **Componente:** `TaskExtractionResultConsumer` en Backlog Review Processor
- **Error:** Fallo al parsear JSON de la respuesta de vLLM

**Impacto:**
- ❌ Las tareas no se están creando en Planning Service
- ❌ El flujo de Backlog Review se detiene después de completar deliberaciones
- ❌ El test E2E falla en la Etapa 11 (Tasks Created in Planning)
- ❌ Los pasos 13.1 y 14 no se ejecutan (dependen del paso 13)

---

## Síntomas

### Comportamiento Esperado
1. ✅ Deliberaciones se completan correctamente (Etapa 5 del test)
2. ✅ Backlog Review Processor recibe eventos `planning.backlog_review.deliberations.complete`
3. ✅ Se dispara la extracción de tareas (Etapa 6)
4. ✅ Ray Executor ejecuta jobs de task extraction (Etapa 7-8)
5. ✅ vLLM genera respuestas con tareas estructuradas (Etapa 9)
6. ✅ Backlog Review Processor recibe eventos `agent.response.completed` con `task_type: "TASK_EXTRACTION"`
7. ✅ `TaskExtractionResultConsumer` parsea el JSON y crea tareas en Planning Service (Etapa 10-11)

### Comportamiento Actual
1. ✅ Deliberaciones se completan correctamente
2. ✅ Backlog Review Processor recibe eventos de deliberaciones completas
3. ✅ Se dispara la extracción de tareas
4. ✅ Ray Executor ejecuta jobs de task extraction
5. ✅ vLLM genera respuestas
6. ✅ Backlog Review Processor recibe eventos `agent.response.completed`
7. ❌ **`TaskExtractionResultConsumer` falla al parsear JSON: "Expecting value: line 1 column 1 (char 0)"**
8. ❌ Las tareas no se crean en Planning Service
9. ❌ El test E2E falla con timeout esperando tareas

---

## Errores Detectados

### Error Principal: Invalid JSON en Task Extraction Response

**Frecuencia:** Masiva (cientos de errores por segundo durante el procesamiento)

**Mensaje de Error:**
```
ERROR - Invalid JSON in task extraction response for ceremony-BRC-3bb7ea0c-b204-4fe6-affb-2de6f83204e3:story-s-11b74fc3-0c88-4350-b5fc-8a95b981c3be:task-extraction: Expecting value: line 1 column 1 (char 0)
```

**Ubicación:**
- **Componente:** `backlog_review_processor.infrastructure.consumers.task_extraction_result_consumer`
- **Método:** `_parse_tasks_json()`
- **Línea aproximada:** ~290

**Patrón del Error:**
- El error se repite múltiples veces para el mismo `task_id`
- Ocurre para todas las stories de la ceremonia
- El error indica que el JSON está vacío o no es válido

### Logs Relevantes

```
2025-12-20 11:28:06,397 - backlog_review_processor.infrastructure.consumers.task_extraction_result_consumer - ERROR - Invalid JSON in task extraction response for ceremony-BRC-3bb7ea0c-b204-4fe6-affb-2de6f83204e3:story-s-11b74fc3-0c88-4350-b5fc-8a95b981c3be:task-extraction: Expecting value: line 1 column 1 (char 0)
```

**Repetición:** El mismo error se repite decenas de veces en un segundo para el mismo task_id, sugiriendo:
- Reintentos automáticos del consumer
- Mensajes duplicados en NATS
- Problema de procesamiento que causa NAK y reprocesamiento

---

## Análisis Técnico

### Flujo de Task Extraction (Según Diagrama)

**Pasos del Diagrama que Funcionan:**
- ✅ **Paso 10:** `BRP → EXEC` (Trigger task creation) - Funciona correctamente
- ✅ **Paso 11:** `EXEC → RAYJOB_TASK` (Create Ray job) - Funciona correctamente
- ✅ **Paso 12:** `RAYJOB_TASK → VLLM_TASK` (Model invocation) - Funciona correctamente

**Paso del Diagrama que Falla:**
- ❌ **Paso 13:** `VLLM_TASK -.-> BRP` (NATS - VLLM response, TaskId, StoryID) - **FALLA AQUÍ**

**Pasos del Diagrama que No se Ejecutan (Dependen del Paso 13):**
- ❌ **Paso 13.1:** `BRP → CTX` (Save TASK response) - No se ejecuta
- ❌ **Paso 14:** `BRP → PL` (ALL TASK CREATED) - No se ejecuta

### Flujo Detallado de Task Extraction

```
1. DeliberationsCompleteConsumer recibe evento (Paso 9 completado)
   ↓
2. ExtractTasksFromDeliberationsUseCase se ejecuta
   ↓
3. [Paso 10] Se envía solicitud a Ray Executor para task extraction
   ↓
4. [Paso 11] Ray Executor crea job (RAYJOB_TASK)
   ↓
5. [Paso 12] Ray Job ejecuta en vLLM (VLLM_TASK)
   ↓
6. vLLM genera respuesta con tareas en formato JSON
   ↓
7. [Paso 13] Ray Worker publica evento NATS: agent.response.completed
   ↓
8. TaskExtractionResultConsumer recibe evento
   ↓
9. [ERROR EN PASO 13] _parse_tasks_json() falla al parsear JSON
   ↓
10. [Paso 13.1] NO SE EJECUTA - Save TASK response a Context Service
   ↓
11. [Paso 14] NO SE EJECUTA - Publicar ALL TASK CREATED a Planning Service
```

### Código Afectado

**Archivo:** `services/backlog_review_processor/infrastructure/consumers/task_extraction_result_consumer.py`

**Método `_parse_tasks_json()`:**
```python
def _parse_tasks_json(self, llm_response: str, task_id: str) -> list[dict[str, Any]] | None:
    """Parse tasks JSON from LLM response."""
    try:
        tasks_data = json.loads(llm_response)
        # ...
    except json.JSONDecodeError as e:
        logger.error(
            f"Invalid JSON in task extraction response for {task_id}: {e}"
        )
        return None
```

**Problema Identificado:**
- `llm_response` contiene tags `<think>` antes del JSON, causando que `json.loads()` falle
- El error "Expecting value: line 1 column 1 (char 0)" puede indicar string vacío O contenido que no empieza con `{` o `[`
- Los logs muestran que vLLM genera respuestas que empiezan con `<think>...</think>` seguido del JSON
- El método `_parse_tasks_json()` intenta parsear directamente sin limpiar los tags

### Método `_extract_llm_response()`:

```python
def _extract_llm_response(self, proposal_data: Any) -> str:
    """Extract LLM response string from proposal data."""
    if isinstance(proposal_data, dict):
        return proposal_data.get("content", str(proposal_data))
    elif isinstance(proposal_data, str):
        return proposal_data
    else:
        return str(proposal_data) if proposal_data else ""
```

**Problema Identificado:**
- El método extrae correctamente el `content` del `proposal`
- Pero el `content` incluye tags `<think>` antes del JSON
- No hay limpieza de tags antes de pasar a `_parse_tasks_json()`

### Método `_parse_tasks_json()`:

```python
def _parse_tasks_json(self, llm_response: str, task_id: str) -> list[dict[str, Any]] | None:
    """Parse JSON response and extract tasks array."""
    try:
        response_json = json.loads(llm_response)  # ❌ FALLA si llm_response tiene tags <think>
        tasks_data = response_json.get("tasks", [])
        return tasks_data
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in task extraction response for {task_id}: {e}")
        return None
```

**Problema Identificado:**
- Intenta parsear directamente `llm_response` como JSON
- No remueve tags `<think>` antes de parsear
- No busca el JSON dentro del contenido si está envuelto en markdown

---

## Investigación de Logs

### Logs del Backlog Review Processor

**Eventos Recibidos:**
```
2025-12-20 11:26:28,246 - INFO - 📥 Received task extraction result: ceremony-BRC-3bb7ea0c-b204-4fe6-affb-2de6f83204e3:story-s-bef41658-1dea-4802-9b63-11f401b1c8f2:task-extraction
```

**Errores Inmediatos:**
```
2025-12-20 11:26:28,246 - ERROR - Invalid JSON in task extraction response for ceremony-BRC-3bb7ea0c-b204-4fe6-affb-2de6f83204e3:story-s-bef41658-1dea-4802-9b63-11f401b1c8f2:task-extraction: Expecting value: line 1 column 1 (char 0)
```

**Observaciones:**
- El consumer SÍ está recibiendo los eventos NATS
- El problema ocurre inmediatamente después de recibir el evento
- El error se repite múltiples veces (posiblemente por NAK y reprocesamiento)

### Logs del Ray Executor

**Deliberaciones Completadas:**
```
2025-12-20 10:28:07,048 [INFO] ✅ Deliberation completed: deliberation-ceremony-BRC-3bb7ea0c-b204-4fe6-affb-2de6f83204e3:story-s-11b74fc3-0c88-4350-b5fc-8a95b981c3be:task-extraction-1766226441 (took 45.77s)
```

**Observaciones:**
- Ray Executor SÍ está completando las tareas de extracción
- Los jobs se ejecutan correctamente (~45 segundos)
- El problema está en la publicación del evento NATS o en su procesamiento

---

## Posibles Causas

### Causa 1: Respuesta de vLLM con Tags de Thinking (Más Probable) ⚠️

**Hipótesis:** vLLM está retornando respuestas que incluyen tags `<think>` antes del JSON, causando que el parseo falle.

**Evidencia:**
- Los logs de Ray Executor muestran respuestas que empiezan con `<think>`:
  ```
  💡 LLM RESPONSE - Agent: agent-task-extractor-001
  ================================================================================
  <think>
  Okay, let's start by analyzing all the agent deliberations...
  ```
- El error "Expecting value: line 1 column 1 (char 0)" sugiere que `llm_response` está vacío después de extraer de `proposal`
- vLLM está generando contenido, pero puede incluir markdown/thinking tags que no son JSON válido

**Flujo del Problema:**
1. vLLM genera respuesta con contenido (incluyendo tags `<think>`)
2. `VLLMResponse.from_vllm_api()` extrae `content` de `data["choices"][0]["message"]["content"]`
3. `VLLMResponse.to_dict()` retorna `{"content": self.content, ...}` donde `content` incluye tags `<think>`
4. `AgentResult.to_dict()` incluye `"proposal": {"content": "...", ...}` en el evento NATS
5. `TaskExtractionResultConsumer._extract_llm_response()` extrae `proposal_data.get("content", ...)`
6. `_parse_tasks_json()` intenta hacer `json.loads(llm_response)` donde `llm_response` contiene tags `<think>` antes del JSON
7. **FALLA:** JSON inválido porque empieza con `<think>` en lugar de `{` o `[`

**Verificación Necesaria:**
- Revisar logs completos de vLLM para ver el contenido completo de la respuesta
- Verificar si vLLM está retornando JSON puro o JSON envuelto en markdown/thinking tags
- Verificar si hay un paso de limpieza que debería remover los tags antes de parsear

### Causa 2: Mapeo Incorrecto de NATS Event

**Hipótesis:** El mapeo desde bytes NATS a `AgentResponse` no está extrayendo correctamente el campo `proposal`.

**Evidencia:**
- El consumer recibe el evento (log "Received task extraction result")
- Pero `llm_response` está vacío al intentar parsear

**Verificación Necesaria:**
- Revisar `AgentResponseMapper.from_nats_bytes()`
- Verificar estructura del evento NATS publicado por Ray Workers
- Comparar con el formato esperado en `TaskExtractionResultConsumer`

### Causa 3: Formato Incorrecto del Evento NATS

**Hipótesis:** Ray Workers están publicando eventos con estructura diferente a la esperada.

**Evidencia:**
- Ray Executor completa los jobs
- Pero el formato del evento puede no coincidir con lo esperado

**Verificación Necesaria:**
- Revisar código de `NATSResultPublisher` en Ray Workers
- Verificar formato del evento publicado para task extraction
- Comparar con formato esperado en el consumer

### Causa 4: Problema de Serialización/Deserialización

**Hipótesis:** Hay un problema al serializar/deserializar el JSON entre Ray Workers y Backlog Review Processor.

**Evidencia:**
- El evento llega al consumer
- Pero el contenido está corrupto o vacío

**Verificación Necesaria:**
- Revisar encoding/decoding de mensajes NATS
- Verificar si hay problemas de encoding (UTF-8, etc.)
- Revisar si el payload está siendo truncado

---

## Impacto en el Sistema

### Flujo de Backlog Review Bloqueado

**Fases del Diagrama:**
1. ✅ **Pasos 1-9 (Deliberation Execution):** Funcionan correctamente
2. ✅ **Paso 10 (Trigger task creation):** Funciona correctamente
3. ✅ **Paso 11 (Create Ray job):** Funciona correctamente
4. ✅ **Paso 12 (Model invocation):** Funciona correctamente
5. ❌ **Paso 13 (NATS - VLLM response):** **FALLA AQUÍ** - JSON inválido o vacío
6. ❌ **Paso 13.1 (Save TASK response):** No se ejecuta (depende del paso 13)
7. ❌ **Paso 14 (ALL TASK CREATED):** No se ejecuta (depende del paso 13.1)

**Consecuencias:**
- ❌ **Extracción de Tareas:** Falla completamente en el paso 13
- ❌ **Creación de Tareas:** No se crean tareas en Planning Service
- ❌ **Completitud del Flujo:** El flujo se detiene después de deliberaciones

### Test E2E

- **Etapa 5 (Deliberations Complete):** ✅ Pasa (con timeout, pero eventualmente completa)
- **Etapas 6-10:** ✅ Pasan (placeholders, no verifican realmente)
- **Etapa 11 (Tasks Created in Planning):** ❌ **FALLA** - Timeout esperando tareas que nunca se crean

---

## Soluciones Recomendadas (Estado del Arte)

### Información del Stack

**vLLM:**
- Versión: `docker.io/vllm/vllm-openai:latest` (última versión)
- Modelo: `Qwen/Qwen3-0.6B` (según ConfigMap) / `TinyLlama/TinyLlama-1.1B-Chat-v1.0` (según deployment)
- **Nota Crítica:** Qwen3 es un modelo reasoning que tiene thinking habilitado por defecto

**Configuración Actual del Servidor:**
- ❌ **NO tiene `--reasoning-parser` configurado** (reasoning contamina `content`)
- ❌ **NO usa structured outputs** en requests (no hay schema enforcement)
- ❌ **El consumer intenta parsear contenido que incluye reasoning tags**

**Problema Identificado:**
- Qwen3 genera tags `<think>` porque el thinking está habilitado y no hay reasoning parser
- vLLM no está aplicando schema enforcement (no se usa `response_format` ni `structured_outputs`)
- El consumer intenta parsear contenido que incluye reasoning tags → FALLA

---

### Solución 1: Structured Outputs / JSON Schema Enforcement (RECOMENDADA) ⭐

**Ventajas:**
- Elimina de raíz `<think>`, markdown y texto fuera de contrato
- El decoder queda constreñido al esquema
- No requiere limpieza/regex en el consumer
- Contrato versionable en un único sitio (schema)

**Implementación:**

1. **Definir JSON Schema estricto** para task extraction
2. **Usar `response_format` con `json_schema`** en el request a vLLM
3. **Validar con pydantic/jsonschema** antes de publicar a NATS
4. **Resultado:** El consumer recibe JSON estructurado, no necesita "rascar JSON" de texto

**Código de Ejemplo:**

Ver sección "Implementación Práctica" más abajo.

**Notas:**
- `response_format` y `structured_outputs` están documentados en vLLM OpenAI-compatible API
- En la práctica usarías uno según versión/stack
- Lo importante es schema enforcement

---

### Solución 2: Tool / Function Calling (Más Industrial)

**Ventajas:**
- El LLM no "responde JSON"; invoca una función con arguments parseables
- vLLM garantiza una llamada parseable usando structured outputs backend
- El payload consumible es `message.tool_calls[0].function.arguments` (JSON), no `message.content`
- Reduce muchísimo la necesidad de limpieza/regex
- El contrato vive en un único sitio (schema de tools), versionable

**Trade-off:**
- Algunos reasoning models pueden no soportar tool calling o lo soportan sólo en ciertos modos
- Verificar compatibilidad del modelo Qwen3 con tool calling

---

### Solución 3: Reasoning Outputs Separados (MANTENER PRECISIÓN) ⭐⭐

**⚠️ IMPORTANTE: NO desactivar thinking** - Reduce precisión en prompts complejos

**Problema Identificado:**
- Qwen3 tiene thinking habilitado por defecto (genera `<think>` tags)
- Desactivar thinking reduce precisión (el modelo pierde su scratchpad de razonamiento)
- Nemotron también genera reasoning traces que mejoran calidad

**Solución Correcta (Mantener Precisión + Parseabilidad):**

1. **Arrancar vLLM con reasoning parser** (server-side)
   - Para Qwen3: `--reasoning-parser qwen3`
   - Para Nemotron: `--reasoning-parser-plugin nano_v3_reasoning_parser.py --reasoning-parser nano_v3`

2. **Usar structured outputs** (request-side)
   - `response_format: {"type": "json_schema", ...}` (strict)
   - Esto fuerza JSON válido en `message.content`

3. **Consumir solo `message.content`** (JSON limpio)
   - El reasoning queda en `message.reasoning` (separado)
   - Opcionalmente persistir reasoning para auditoría/debug

**Resultado:**
- ✅ Thinking ON → Mejor precisión
- ✅ JSON limpio en `content` → Parseable sin hacks
- ✅ Reasoning separado → Disponible para observabilidad

**Configuración vLLM Server (Qwen3):**

```yaml
# deploy/k8s/30-microservices/vllm-server.yaml
containers:
- name: vllm
  image: docker.io/vllm/vllm-openai:latest
  args:
  - "--model"
  - "Qwen/Qwen3-0.6B"
  - "--reasoning-parser"
  - "qwen3"  # ⭐ Agregar reasoning parser
  env:
  - name: MODEL_NAME
    value: "Qwen/Qwen3-0.6B"
```

**Configuración vLLM Server (Nemotron - Futuro):**

```yaml
# Para Nemotron-3-Nano-30B-A3B
containers:
- name: vllm
  image: docker.io/vllm/vllm-openai:latest
  args:
  - "--model"
  - "nvidia/Nemotron-3-Nano-30B-A3B"
  - "--reasoning-parser-plugin"
  - "/path/to/nano_v3_reasoning_parser.py"
  - "--reasoning-parser"
  - "nano_v3"  # ⭐ Reasoning parser específico
```

**Código de Ejemplo (Request con Structured Outputs + Reasoning):**

```python
# En VLLMRequest o VLLMHTTPClient
request_payload = {
    "model": model,
    "messages": messages,
    "temperature": temperature,
    # ⭐ Structured outputs para JSON válido
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "task_extraction",
            "schema": task_schema,
            "strict": True,
        },
    },
    # ⚠️ NO desactivar thinking (reduce precisión)
    # El reasoning parser del servidor separará reasoning de content
}

# Procesar respuesta
response = await vllm_client.generate(request)
content = response.content  # JSON limpio (sin <think>)
reasoning = response.reasoning  # Reasoning separado (opcional)
```

**⚠️ Alternativa (NO RECOMENDADA - Reduce Precisión):**

```python
# Solo si realmente necesitas desactivar thinking (no recomendado)
request_payload = {
    "chat_template_kwargs": {
        "enable_thinking": False,  # ⚠️ Reduce precisión
    },
}
```

---

### Solución 4: Event-Driven Best Practices (DLQ + Idempotencia)

**Problema Actual:**
- Repetición "cientos por segundo" suena a NAK/redelivery loop
- Aunque se arregle el JSON, esto hay que blindarlo

**Recomendaciones:**
1. **Ack/Nak con backoff y max deliveries** (JetStream) → cuando exceda, a DLQ
2. **Idempotencia por task_id** en el consumer (si llega duplicado, ignore/ack)
3. **Publicar a NATS un evento canónico** (ya parseado/validado) desde el Ray Worker
4. **Dejar el BRP consumer como "thin consumer"** (no confiar en que siempre podrá parsear)

**Estructura de Evento Canónico:**

```python
{
    "task_id": "...",
    "story_id": "...",
    "ceremony_id": "...",
    "tasks": [...],          # typed, validated (no raw content)
    "raw_content": "...",    # opcional, truncado (solo para debugging)
    "model": "...",
    "trace_id": "...",
    "validated_at": "...",   # timestamp de validación
}
```

---

## Plan de Implementación Recomendado

### Fase 1: Solución Inmediata (Defensa Secundaria en Consumer)

1. **Agregar limpieza de tags `<think>` en `_parse_tasks_json()`**
   - Remover tags antes de parsear
   - Buscar JSON dentro del contenido
   - Extraer solo la parte JSON válida
   - Agregar logging detallado

2. **Agregar DLQ y max deliveries en JetStream**
   - Configurar max deliveries (ej: 3)
   - Configurar DLQ para poison messages
   - Agregar idempotencia por task_id

### Fase 2: Solución Robusta (Schema Enforcement + Reasoning Parser)

1. **Configurar Reasoning Parser en vLLM Server** ⭐
   - Agregar `--reasoning-parser qwen3` al deployment de vLLM
   - Esto separa reasoning de content automáticamente
   - Para Nemotron: usar `--reasoning-parser-plugin` + `--reasoning-parser nano_v3`

2. **Implementar structured outputs en `VLLMHTTPClient`**
   - Agregar método `build_task_extraction_request()` con JSON Schema
   - Usar `response_format` con `json_schema` y `strict: True`
   - **NO desactivar thinking** (mantener precisión)
   - Validar respuesta con pydantic/jsonschema antes de publicar

3. **Modificar `GenerateProposal` para task extraction**
   - Detectar si es task extraction (por task_id o metadata)
   - Usar structured outputs en lugar de text-only
   - Consumir solo `message.content` (JSON limpio)
   - Opcionalmente persistir `message.reasoning` para observabilidad
   - Validar respuesta antes de crear `AgentResult`

4. **Publicar evento canónico a NATS**
   - Estructura con `tasks` ya parseado/validado
   - No incluir `raw_content` o truncarlo
   - Agregar `validated_at` timestamp
   - Opcionalmente incluir `reasoning` separado (no en content)

### Fase 3: Optimización (Tool Calling si es compatible)

1. **Evaluar compatibilidad de Qwen3 con tool calling**
2. **Si es compatible, migrar a tool calling**
3. **Procesar `tool_calls[0].function.arguments` en lugar de `content`**

---

## Hallazgos de Investigación

### Logs de Ray Executor - Respuestas de vLLM

Los logs muestran que vLLM **SÍ está generando respuestas**, pero estas contienen tags de thinking:

```
💡 LLM RESPONSE - Agent: agent-task-extractor-001
================================================================================
<think>
Okay, let's start by analyzing all the agent deliberations...
```

**Observaciones:**
- ✅ vLLM está generando contenido (no está vacío)
- ⚠️ El contenido incluye tags `<think>` antes del JSON esperado
- ⚠️ El JSON real probablemente está después de los tags `<think>`
- ❌ El consumer está intentando parsear todo el contenido como JSON, incluyendo los tags
- ❌ No hay limpieza de tags antes de `json.loads()`

### Invocaciones a vLLM Server

**Componente:** `core/ray_jobs/infrastructure/adapters/vllm_http_client.py`

**Flujo de Invocación:**
```python
# 1. VLLMHTTPClient.generate() hace POST a vLLM
async with session.post(
    f"{self.vllm_url}/v1/chat/completions",
    json=request.to_dict(),
    timeout=aiohttp.ClientTimeout(total=self.timeout),
) as response:
    data = await response.json()

    # 2. VLLMResponse.from_vllm_api() extrae content
    content = data["choices"][0]["message"]["content"]

    # 3. Retorna VLLMResponse con content que incluye tags <think>
    return VLLMResponse(
        content=content.strip(),  # ⚠️ content puede incluir <think>...</think>
        ...
    )
```

**Endpoint vLLM:**
- URL: `{vllm_url}/v1/chat/completions` (OpenAI-compatible API)
- Método: POST
- Request: JSON con `model`, `messages`, `temperature`, etc.
- Response: JSON con `choices[0].message.content` que contiene la respuesta del LLM

**Problema:**
- vLLM está retornando contenido que incluye tags `<think>` antes del JSON
- El contenido no es JSON puro, sino texto que puede incluir markdown/thinking tags
- El consumer espera JSON puro en el campo `content`
- **El prompt especifica "Return ONLY valid JSON, no markdown, no explanations" pero vLLM no lo está siguiendo**

### Prompt de Task Extraction

**Ubicación:** `services/backlog_review_processor/application/usecases/extract_tasks_from_deliberations_usecase.py`

**Prompt Actual:**
```python
prompt = f"""You are a task extraction specialist. Analyze the following agent deliberations for a user story and extract concrete, actionable tasks.

Story ID: {story_id.value}

Agent Deliberations:
{chr(10).join(deliberations_text)}

Instructions:
1. Analyze all agent deliberations carefully
2. Extract concrete, actionable tasks that need to be completed
3. Each task should be specific, measurable, and have clear acceptance criteria
4. Tasks should be ordered logically (dependencies considered)
5. For each task, identify which agent deliberations contributed to it
6. Return a JSON array of tasks with the following structure:
   {{
     "tasks": [
       {{
         "title": "Task title",
         "description": "Detailed description",
         "estimated_hours": 8,
         "deliberation_indices": [0, 1, 2],
         "priority": 1
       }}
     ]
   }}

Return ONLY valid JSON, no markdown, no explanations.
"""
```

**Observaciones:**
- ✅ El prompt especifica claramente "Return ONLY valid JSON, no markdown, no explanations"
- ❌ vLLM está ignorando esta instrucción y retornando contenido con tags `<think>`
- ⚠️ El prompt puede necesitar ser más estricto o usar técnicas de "JSON mode" si vLLM lo soporta

### Flujo de Datos Identificado

```
1. vLLM HTTP API retorna:
   {
     "choices": [{
       "message": {
         "content": "<think>...</think>\n[{...JSON...}]"
       }
     }]
   }
   ↓
2. VLLMResponse.from_vllm_api() extrae:
   content = "<think>...</think>\n[{...JSON...}]"
   ↓
3. VLLMResponse.to_dict() retorna:
   {"content": "<think>...</think>\n[{...JSON...}]", ...}
   ↓
4. GenerateProposal.execute() retorna:
   {"content": "<think>...</think>\n[{...JSON...}]", ...}
   ↓
5. AgentResult.success_result() recibe:
   proposal = {"content": "<think>...</think>\n[{...JSON...}]", ...}
   ↓
6. AgentResult.to_dict() incluye:
   {"proposal": {"content": "<think>...</think>\n[{...JSON...}]", ...}, ...}
   ↓
7. NATSResultPublisher.publish_success() publica:
   {"proposal": {"content": "<think>...</think>\n[{...JSON...}]", ...}, ...}
   ↓
8. TaskExtractionResultConsumer._extract_llm_response() extrae:
   llm_response = "<think>...</think>\n[{...JSON...}]"
   ↓
9. _parse_tasks_json() intenta:
   json.loads("<think>...</think>\n[{...JSON...}]")
   ↓
10. ❌ FALLA: JSON inválido porque empieza con "<think>"
```

## Implementación Práctica

### Ejemplo: Structured Outputs para Task Extraction

**Archivo:** `core/ray_jobs/domain/vllm_request.py` (extender `VLLMRequest`)

```python
from typing import Any

def build_task_extraction_payload(
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.0,  # 0 para determinismo en JSON
) -> dict[str, Any]:
    """Build vLLM request with structured outputs for task extraction.

    Args:
        model: Model name
        messages: List of message dicts (role, content)
        temperature: Temperature (0 for deterministic JSON)

    Returns:
        Request payload with response_format and json_schema
    """
    task_schema = {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "minLength": 1},
                        "description": {"type": "string", "minLength": 1},
                        "estimated_hours": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 200,
                        },
                        "deliberation_indices": {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 0},
                        },
                        "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                    },
                    "required": ["title", "description", "estimated_hours", "priority"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["tasks"],
        "additionalProperties": False,
    }

    return {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "task_extraction",
                "schema": task_schema,
                "strict": True,  # Enforce strict schema compliance
            },
        },
        # Alternativa (según versión vLLM): usar structured_outputs
        # "structured_outputs": {"json": task_schema},
        # ⚠️ NO desactivar thinking aquí (reduce precisión)
        # El reasoning parser del servidor separará reasoning de content
        # Si el servidor tiene --reasoning-parser configurado, el reasoning
        # quedará en message.reasoning y content será JSON limpio
    }
```

**Uso en `VLLMHTTPClient.generate()`:**

```python
async def generate(self, request: VLLMRequest) -> VLLMResponse:
    """Generate text using vLLM HTTP API."""
    # Detectar si es task extraction (por metadata o task_id)
    is_task_extraction = self._is_task_extraction(request)

    if is_task_extraction:
        # Usar structured outputs
        payload = build_task_extraction_payload(
            model=self.model,
            messages=[msg.to_dict() for msg in request.messages],
            temperature=request.temperature,
        )
    else:
        # Usar request normal
        payload = request.to_dict()

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{self.vllm_url}/v1/chat/completions",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        ) as response:
            response.raise_for_status()
            data = await response.json()

            # Para structured outputs, el content ya es JSON válido
            message = data["choices"][0]["message"]
            content = message["content"]

            # Extraer reasoning si existe (separado por reasoning parser)
            reasoning = message.get("reasoning")  # Opcional, solo si servidor tiene parser

            # Validar que es JSON válido (opcional, pero recomendado)
            if is_task_extraction:
                try:
                    json.loads(content)  # Validar que es JSON
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from structured outputs: {e}")
                    raise RuntimeError(f"vLLM returned invalid JSON: {e}") from e

                # Log reasoning si existe (para observabilidad)
                if reasoning:
                    logger.debug(f"Reasoning trace available ({len(reasoning)} chars)")

            return VLLMResponse.from_vllm_api(
                api_data=data,
                agent_id=self.agent_id,
                role=self.role,
                model=self.model,
                temperature=request.temperature,
                reasoning=reasoning,  # Pasar reasoning separado
            )
```

---

## Próximos Pasos Inmediatos

1. **Implementar Solución 1 (Structured Outputs)** ⭐
   - [ ] Crear JSON Schema para task extraction
   - [ ] Modificar `VLLMHTTPClient.generate()` para aceptar `response_format`
   - [ ] Modificar `GenerateProposal.execute()` para usar structured outputs cuando sea task extraction
   - [ ] Validar respuesta con pydantic antes de publicar a NATS
   - [ ] Actualizar `TaskExtractionResultConsumer` para procesar JSON estructurado

2. **Configurar Reasoning Parser en vLLM Server** ⭐
   - [ ] Agregar `--reasoning-parser qwen3` al deployment de vLLM
   - [ ] Verificar que el reasoning se separa correctamente de content
   - [ ] Preparar configuración para Nemotron (cuando se migre)

3. **Actualizar VLLMResponse para soportar reasoning separado**
   - [ ] Agregar campo `reasoning` opcional a `VLLMResponse`
   - [ ] Extraer `message.reasoning` de la respuesta de vLLM
   - [ ] Persistir reasoning separado (opcional, para observabilidad)

3. **Agregar DLQ y Idempotencia**
   - [ ] Configurar max deliveries en JetStream consumer
   - [ ] Configurar DLQ para poison messages
   - [ ] Agregar idempotencia por task_id en consumer

4. **Agregar Logging Detallado**
   - [ ] Loggear request completo a vLLM (con response_format)
   - [ ] Loggear respuesta completa de vLLM
   - [ ] Loggear validación de schema
   - [ ] Loggear evento publicado a NATS

5. **Crear Tests**
   - [ ] Test unitario con structured outputs
   - [ ] Test de integración con vLLM mock
   - [ ] Test de consumer con JSON estructurado
   - [ ] Test de fallback si structured outputs falla

6. **Verificaciones Críticas**
   - [ ] Compatibilidad modelo: Verificar que Qwen3 soporta `response_format` con `json_schema`
   - [ ] Versión vLLM: Verificar si está en versión donde cambió `guided_json` → `structured_outputs`
   - [ ] Reasoning parser: Verificar que `--reasoning-parser qwen3` funciona correctamente
   - [ ] Cortes por stop: NO usar stop para cortar `<think>` (puede truncar JSON)
   - [ ] Tormenta de redeliveries: Implementar DLQ + idempotencia antes de deployar

---

## Configuración Específica del Servidor vLLM

### Configuración Actual (Problema)

**Archivo:** `deploy/k8s/30-microservices/vllm-server.yaml`

```yaml
containers:
- name: vllm
  image: docker.io/vllm/vllm-openai:latest
  env:
  - name: MODEL_NAME
    value: "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
  # ❌ NO tiene --reasoning-parser configurado
```

**Problema:** El servidor no tiene reasoning parser, por lo que el reasoning contamina `content`.

### Configuración Recomendada para Qwen3

```yaml
containers:
- name: vllm
  image: docker.io/vllm/vllm-openai:latest
  args:
  - "--model"
  - "Qwen/Qwen3-0.6B"
  - "--reasoning-parser"
  - "qwen3"  # ⭐ Separar reasoning de content
  env:
  - name: MODEL_NAME
    value: "Qwen/Qwen3-0.6B"
  # ... resto de configuración
```

**Resultado:**
- `message.content` → JSON limpio (sin `<think>`)
- `message.reasoning` → Reasoning separado (opcional, para observabilidad)

### Configuración para Nemotron-3-Nano (Futuro)

```yaml
containers:
- name: vllm
  image: docker.io/vllm/vllm-openai:latest
  args:
  - "--model"
  - "nvidia/Nemotron-3-Nano-30B-A3B"
  - "--reasoning-parser-plugin"
  - "/path/to/nano_v3_reasoning_parser.py"
  - "--reasoning-parser"
  - "nano_v3"  # ⭐ Reasoning parser específico de Nemotron
  env:
  - name: MODEL_NAME
    value: "nvidia/Nemotron-3-Nano-30B-A3B"
  # ... resto de configuración
```

**Notas:**
- Requiere `vllm>=0.12.0`
- Descargar `nano_v3_reasoning_parser.py` del modelcard de Hugging Face
- Montar el parser como volumen o incluirlo en la imagen

---

## Resumen Ejecutivo

### Problema Raíz
- Qwen3 genera reasoning tags `<think>` que contaminan `message.content`
- El consumer intenta parsear contenido con tags → FALLA
- **NO desactivar thinking** (reduce precisión)

### Solución Correcta (Mantener Precisión + Parseabilidad)

1. **Server-side:** Configurar `--reasoning-parser qwen3` en vLLM
   - Separa reasoning de content automáticamente
   - `message.content` queda limpio (JSON)
   - `message.reasoning` queda separado (opcional)

2. **Request-side:** Usar `response_format: json_schema` (strict)
   - Fuerza JSON válido en `message.content`
   - Schema enforcement garantiza contrato

3. **Consumer-side:** Consumir solo `message.content`
   - JSON ya validado y parseable
   - No requiere limpieza/regex

### Acciones Inmediatas

1. ⭐ **Agregar `--reasoning-parser qwen3` al deployment de vLLM**
2. ⭐ **Implementar structured outputs en `VLLMHTTPClient`**
3. ⭐ **Actualizar `VLLMResponse` para soportar reasoning separado**
4. ⭐ **Configurar DLQ + idempotencia en JetStream consumer**

### Beneficios

- ✅ **Mantiene precisión** (thinking ON)
- ✅ **Elimina fragilidad** (JSON estructurado)
- ✅ **Multi-modelo compatible** (Qwen3, Nemotron, etc.)
- ✅ **Fricción mínima** (cambiar modelo = cambiar config, no código)

---

## Referencias

- **Test E2E:** `e2e/tests/05-validate-deliberations-and-tasks/`
- **Consumer:** `services/backlog_review_processor/infrastructure/consumers/task_extraction_result_consumer.py`
- **Mapper:** `services/backlog_review_processor/infrastructure/mappers/agent_response_mapper.py`
- **Use Case:** `services/backlog_review_processor/application/usecases/extract_tasks_from_deliberations_usecase.py`
- **NATS Publisher:** `core/ray_jobs/infrastructure/adapters/nats_result_publisher.py`

---

**Autor:** AI Assistant (investigación basada en logs de producción)
**Fecha:** 2025-12-20
**Estado:** 🔍 INVESTIGANDO - Requiere más información de logs y código para determinar causa raíz
