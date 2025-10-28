# Candidatos para Extraer a YAML/JSON

## 1. ✅ Role Prompts (ALTA PRIORIDAD)
**Ubicación:** `core/agents_and_tools/agents/application/usecases/generate_plan_usecase.py:75-81`

```python
role_prompts = {
    "DEV": "You are an expert software developer focused on writing clean, maintainable code.",
    "QA": "You are an expert QA engineer focused on testing and quality validation.",
    "ARCHITECT": "You are a senior software architect focused on design and analysis.",
    "DEVOPS": "You are a DevOps engineer focused on deployment and infrastructure.",
    "DATA": "You are a data engineer focused on databases and data pipelines.",
}
```

**Problema:**
- Hardcodeado en código
- Ya existe `core/agents_and_tools/resources/profiles/` con YAML para cada rol
- Estos prompts podrían estar en cada profile YAML

**Solución:** Mover a `resources/profiles/*.yaml`

---

## 2. ✅ System Prompts para Plan Generation (ALTA PRIORIDAD)
**Ubicación:** `core/agents_and_tools/agents/application/usecases/generate_plan_usecase.py:83-104`

```python
system_prompt = role_prompts.get(role, f"You are an expert {role} engineer.")
system_prompt += "\n\n"
tools_json = json.dumps(available_tools.capabilities, indent=2)
system_prompt += f"You have access to the following tools:\n{tools_json}\n\n"
system_prompt += f"Mode: {available_tools.mode}\n\n"
system_prompt += "Generate a step-by-step execution plan in JSON format."

user_prompt = f"""Task: {task}

Context:
{context}

Generate an execution plan as a JSON object with this structure:
{{
  "reasoning": "Why this approach...",
  "steps": [
    {{"tool": "files", "operation": "read_file", "params": {{"path": "src/file.py"}}}},
    ...
  ]
}}

Use ONLY the available tools listed above. Be specific with file paths based on the context.
"""
```

**Problema:**
- Template de prompt hardcodeado
- Formato JSON hardcodeado
- Difícil de modificar sin tocar código

**Solución:** Mover a `resources/prompts/plan_generation.yaml`

---

## 3. ✅ System Prompts para Next Action (ReAct)
**Ubicación:** `core/agents_and_tools/agents/application/usecases/generate_next_action_usecase.py:69-104`

```python
system_prompt = f"""You are an autonomous agent using ReAct (Reasoning + Acting) pattern.

Available tools:
{json.dumps(available_tools.capabilities, indent=2)}

Decide the next action based on task and previous observations.
Respond in JSON format:
{{
  "done": false,
  "reasoning": "Why this action...",
  "step": {{"tool": "files", "operation": "read_file", "params": {{"path": "..."}}}}
}}

Or if task is complete:
{{
  "done": true,
  "reasoning": "Task complete because..."
}}
"""

user_prompt = f"""Task: {task}

Context: {context}

Observation History:
[history formatted here]

What should I do next?
"""
```

**Problema:**
- Template ReAct hardcodeado
- Formato JSON hardcodeado
- Difícil de experimentar con diferentes estrategias

**Solución:** Mover a `resources/prompts/next_action_react.yaml`

---

## 4. ✅ JSON Parsing Logic (ALTA PRIORIDAD)
**Ubicación:** `core/agents_and_tools/agents/application/usecases/generate_plan_usecase.py:114-122`

```python
# Try to extract JSON if wrapped in markdown
if JSON_CODE_BLOCK_START in response:
    json_start = response.find(JSON_CODE_BLOCK_START) + JSON_MARKDOWN_DELIMITER_LEN
    json_end = response.find(JSON_CODE_BLOCK_END, json_start)
    response = response[json_start:json_end].strip()
elif "```" in response:
    json_start = response.find("```") + 3
    json_end = response.find("```", json_start)
    response = response[json_start:json_end].strip()
```

**Problema:**
- Lógica de parsing hardcodeada en use case
- Misma lógica duplicada en `generate_next_action_usecase.py`
- No reutilizable
- Dificulta testing

**Solución:**
- Crear un `ResponseParser` en la capa de infraestructura
- O mover a un utility/mapper reutilizable
- Permitir configuración de delimitadores via YAML

---

## 5. ⚠️ Constantes de Configuración (MEDIA PRIORIDAD)
**Ubicación:** Varios archivos en `core/agents_and_tools/tools/`

### file_tool.py
```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
```

### http_tool.py
```python
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
DEFAULT_TIMEOUT = 30  # seconds
```

### db_tool.py
```python
MAX_RESULT_SIZE = 1000  # Maximum rows to return
DEFAULT_TIMEOUT = 30  # seconds
```

### test_tool.py
```python
DEFAULT_TIMEOUT = 600  # 10 minutes
```

**Problema:**
- Configuración hardcodeada
- No puede variar entre entornos (dev/prod)
- No puede configurarse por cliente

**Solución:** Mover a `resources/config/tools_config.yaml` o variables de entorno

---

## 6. ⚠️ TESTS_PATH (BAJA PRIORIDAD)
**Ubicación:** `core/agents_and_tools/agents/vllm_agent.py`

```python
TESTS_PATH = "tests"
```

**Solución:** Ya está en variables, podría ser configuración del profile.

---

## Recomendaciones

### Prioridad ALTA:
1. Mover role prompts a profiles existentes
2. Crear `resources/prompts/` con templates YAML
3. Refactor use cases para cargar desde YAML
4. Extraer lógica de JSON parsing a servicio reutilizable

### Prioridad MEDIA:
5. Mover constantes de tools a config YAML o env vars

### Prioridad BAJA:
6. TESTS_PATH ya está bien como está

---

## Estructura Propuesta

```
core/agents_and_tools/resources/
├── profiles/
│   ├── developer.yaml
│   │   ├── role_prompt: "You are an expert software developer..."
│   │   ├── capabilities: [...]
│   │   └── ...
│   └── ...
├── prompts/
│   ├── plan_generation.yaml
│   │   ├── system_template: "..."
│   │   ├── user_template: "..."
│   │   └── json_schema: {...}
│   ├── next_action_react.yaml
│   │   ├── system_template: "..."
│   │   └── json_schema: {...}
│   └── ...
└── config/
    ├── tools_config.yaml
    │   ├── file_tool:
    │   │   max_size: 10485760
    │   ├── http_tool:
    │   │   max_request_size: 10485760
    │   │   default_timeout: 30
    │   └── ...
    └── ...
```

