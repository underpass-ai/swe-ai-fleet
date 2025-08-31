# Tool Gateway Implementation Plan - M4 Milestone

## 🎯 Objetivo

Implementar la infraestructura para ejecutar herramientas de desarrollo de forma segura y trazable, transformando el sistema de "hablar y razonar" a "ejecutar, validar y aprender" de forma autónoma.

## 🏗️ Arquitectura del Tool Gateway

### Componentes Principales

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Agent LLM     │───▶│   Tool Gateway   │───▶│   Policy        │
│                 │    │   (FastAPI)      │    │   Engine        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Sandbox        │    │   Audit         │
                       │   Executor       │    │   Logger        │
                       └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Result         │    │   Redis         │
                       │   Processor      │    │   Streams       │
                       └──────────────────┘    └─────────────────┘
```

### Flujo de Datos

1. **Agent LLM** solicita ejecución de herramienta
2. **Tool Gateway** valida y autoriza la solicitud
3. **Policy Engine** verifica permisos y límites
4. **Sandbox Executor** ejecuta en contenedor aislado
5. **Audit Logger** registra cada operación
6. **Result Processor** procesa y formatea resultados
7. **Redis Streams** almacena para trazabilidad

## 🔧 Implementación Técnica

### 1. Tool Gateway (FastAPI)

#### Estructura del Proyecto

```
deploy/docker/tools/
├── docker-compose.tools.yml
├── Dockerfile
├── requirements.txt
└── src/
    └── swe_ai_fleet/
        └── tools/
            ├── __init__.py
            ├── gateway.py              # FastAPI app principal
            ├── policy_engine.py        # Motor de políticas
            ├── sandbox_executor.py     # Ejecutor sandbox
            ├── audit_logger.py         # Logger de auditoría
            └── result_processor.py     # Procesador de resultados
```

#### API Endpoints

```python
# POST /v1/tools/exec
{
    "role": "developer",
    "case_id": "case-123",
    "subtask_id": "DEV-123",
    "cmd": "pytest -q",
    "cwd": "/workspace/repo",
    "timeout_sec": 300,
    "env": {"PYTHONUNBUFFERED": "1"},
    "limits": {"cpu": 1.0, "mem_mb": 2048}
}

# Response
{
    "exec_id": "exec-7f1a",
    "exit_code": 0,
    "image": "python:3.11-bookworm",
    "stdout_tail": "...",
    "stderr_tail": "",
    "artifacts": [
        {"type": "junit_xml", "path": "/artifacts/junit.xml"}
    ],
    "logged_to": "swe:tools:exec:stream"
}
```

### 2. Policy Engine

#### Roles y Permisos

```python
ROLE_ALLOWLIST = {
    "developer": ("pytest", "python", "node", "npm", "go", "bash", "sh"),
    "qa":        ("pytest", "python", "k6", "newman", "bash", "sh"),
    "devops":    ("kubectl", "helm", "kubeval", "docker", "bash", "sh", "psql", "redis-cli"),
    "architect": ("python", "node", "eslint", "flake8", "trivy", "bash", "sh"),
    "data":      ("python", "pytest", "bash", "sh"),
}

# Límites por rol
ROLE_LIMITS = {
    "developer": {"cpu": 2.0, "mem_mb": 4096, "timeout_sec": 600},
    "devops":    {"cpu": 1.0, "mem_mb": 2048, "timeout_sec": 300},
    "qa":        {"cpu": 1.5, "mem_mb": 3072, "timeout_sec": 450},
    "architect": {"cpu": 1.0, "mem_mb": 2048, "timeout_sec": 300},
    "data":      {"cpu": 2.0, "mem_mb": 4096, "timeout_sec": 600},
}
```

#### Validaciones de Seguridad

- **Path validation**: Solo rutas dentro de `WORKSPACE_ROOT`
- **Command validation**: Solo comandos en allowlist del rol
- **Resource limits**: CPU, memoria y tiempo máximo
- **Environment filtering**: Bloqueo de variables sensibles

### 3. Sandbox Executor

#### Configuración Docker

```python
docker_cmd = [
    "docker", "run", "--rm",
    "--name", f"swe-exec-{exec_id}",
    "--network", "none",                    # Sin red
    "--cpus", str(req.limits.cpu),         # Límite CPU
    "--memory", f"{req.limits.mem_mb}m",   # Límite memoria
    "--pids-limit", "256",                 # Límite procesos
    "--read-only",                         # FS solo lectura
    "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,mode=1777,size=256m",
    "-v", f"{req.cwd}:/workspace",        # Montaje workspace
    "-w", "/workspace",                    # Directorio de trabajo
    image, "sh", "-lc", req.cmd           # Comando a ejecutar
]
```

#### Imágenes por Comando

```python
CMD_IMAGE_MAP = {
    "pytest": "python:3.11-bookworm",
    "python": "python:3.11-bookworm",
    "node":   "node:20-bookworm",
    "npm":    "node:20-bookworm",
    "go":     "golang:1.22-bookworm",
    "k6":     "grafana/k6:0.48.0",
    "newman": "postman/newman:6",
    "kubectl":"bitnami/kubectl:1.29",
    "helm":   "alpine/helm:3.15.3",
    "kubeval":"ghcr.io/instrumenta/kubeval:latest",
    "docker": "docker:25-cli",
    "psql":   "postgres:16-bookworm",
    "redis-cli":"redis:7-alpine",
    "eslint": "node:20-bookworm",
    "flake8": "python:3.11-bookworm",
    "trivy":  "aquasec/trivy:0.53.0",
    "bash":   "debian:12-slim",
    "sh":     "debian:12-slim",
}
```

### 4. Audit Logger

#### Estructura de Eventos

```python
# Redis Stream: swe:tools:exec:stream
fields = {
    "event": "tool_exec",
    "exec_id": exec_id,
    "role": req.role,
    "case_id": req.case_id,
    "subtask_id": req.subtask_id or "",
    "cmd": req.cmd,
    "image": image,
    "rc": str(rc),
    "stdout_tail": stdout,
    "stderr_tail": stderr,
    "ts": str(started),
    "duration_ms": str(duration),
    "artifacts_count": str(len(artifacts)),
}
```

#### Proyección a Neo4j

```cypher
// Crear nodo de ejecución
CREATE (e:ExecResult {
    exec_id: $exec_id,
    role: $role,
    case_id: $case_id,
    cmd: $cmd,
    exit_code: $rc,
    duration_ms: $duration,
    timestamp: $ts
})

// Conectar con caso de uso
MATCH (c:Case {case_id: $case_id})
CREATE (e)-[:EXECUTED_FOR]->(c)

// Conectar con subtarea si existe
MATCH (s:Subtask {subtask_id: $subtask_id})
CREATE (e)-[:EXECUTED_FOR]->(s)
```

### 5. Result Processor

#### Procesamiento de Artefactos

```python
def collect_artifacts(workspace_path: str) -> List[Artifact]:
    """Recolecta artefactos comunes del workspace"""
    artifacts = []
    
    # JUnit XML
    junit_path = os.path.join(workspace_path, "junit.xml")
    if os.path.isfile(junit_path):
        artifacts.append(Artifact(type="junit_xml", path=junit_path))
    
    # Coverage XML
    coverage_path = os.path.join(workspace_path, "coverage.xml")
    if os.path.isfile(coverage_path):
        artifacts.append(Artifact(type="coverage_xml", path=coverage_path))
    
    # Test results
    test_results_path = os.path.join(workspace_path, "test-results")
    if os.path.isdir(test_results_path):
        artifacts.append(Artifact(type="test_results", path=test_results_path))
    
    return artifacts
```

#### Análisis de Resultados

```python
def analyze_test_results(artifacts: List[Artifact]) -> TestAnalysis:
    """Analiza resultados de tests para feedback"""
    analysis = TestAnalysis()
    
    for artifact in artifacts:
        if artifact.type == "junit_xml":
            analysis.test_count = parse_junit_xml(artifact.path)
        elif artifact.type == "coverage_xml":
            analysis.coverage = parse_coverage_xml(artifact.path)
    
    return analysis
```

## 🚀 Implementation Plan

### Phase 1: Core Infrastructure (Week 1-2)

- [ ] **Basic Tool Gateway** with FastAPI
- [ ] **Policy Engine** with basic validations
- [ ] **Sandbox Executor** with Docker
- [ ] **Basic Audit Logger**

### Phase 2: Security & Isolation (Week 3)

- [ ] **Advanced sandboxing** with strict limits
- [ ] **Complete Policy Engine** with RBAC
- [ ] **Exhaustive security validations**
- [ ] **Security and penetration tests**

### Phase 3: Integration & Testing (Week 4)

- [ ] **Redis Streams integration**
- [ ] **Neo4j projection** for traceability
- [ ] **Complete e2e tests**
- [ ] **Documentation** and examples

### Phase 4: Production Ready (Week 5-6)

- [ ] **Monitoring** and metrics
- [ ] **Advanced structured logging**
- [ ] **Performance tuning** and optimizations
- [ ] **Kubernetes deployment**

## 🧪 Testing Strategy

### Unit Tests

```python
def test_policy_engine_role_validation():
    """Test that validates permissions by role"""
    policy = PolicyEngine()
    
    # Developer can execute pytest
    assert policy.can_execute("developer", "pytest", "/workspace/repo")
    
    # Developer CANNOT execute kubectl
    assert not policy.can_execute("developer", "kubectl", "/workspace/repo")

def test_sandbox_executor_isolation():
    """Test that validates sandbox isolation"""
    executor = SandboxExecutor()
    
    # Verify no network access
    result = executor.execute("ping 8.8.8.8", timeout=5)
    assert result.exit_code != 0
```

### Integration Tests

```python
def test_tool_gateway_e2e():
    """Complete test of tool flow"""
    # 1. Start infrastructure
    # 2. Execute valid command
    # 3. Verify result
    # 4. Verify audit
    # 5. Verify Neo4j projection
```

### Security Tests

```python
def test_path_traversal_prevention():
    """Test that prevents path traversal attacks"""
    # Try to access directories outside workspace
    # Verify it's blocked
```

## 🔒 Security Considerations

### Isolation

- **Ephemeral containers**: Each execution in new container
- **No privileges**: `--user` and `--read-only`
- **No network**: `--network none` by default
- **Strict limits**: CPU, memory, processes

### Input Validation

- **Path sanitization**: Prevent path traversal
- **Command validation**: Only allowed commands
- **Environment filtering**: Block sensitive variables
- **Resource limits**: Prevent DoS

### Audit

- **Complete log**: Each execution recorded
- **Traceability**: Connected with use cases
- **Alerts**: For suspicious behavior
- **Retention**: Log retention policy

## 📊 Metrics and Monitoring

### Key Metrics

- **Execution time** per tool
- **Success rate** per role and command
- **Resource usage** (CPU, memory)
- **Usage frequency** per tool

### Alerts

- **Consecutive failed executions**
- **Excessive resource usage**
- **Suspicious or unauthorized commands**
- **Sandboxing failures**

## 🚀 Deployment

### Docker Compose (Development)

```yaml
version: "3.9"
services:
  tool-gateway:
    build:
      context: ../..
      dockerfile: deploy/docker/tools/Dockerfile
    environment:
      - REDIS_URL=${REDIS_URL}
      - WORKSPACE_ROOT=${WORKSPACE_ROOT}
    ports:
      - "8088:8088"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
```

### Kubernetes (Producción)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tool-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tool-gateway
  template:
    spec:
      containers:
      - name: tool-gateway
        image: swe-ai-fleet/tool-gateway:latest
        ports:
        - containerPort: 8088
        securityContext:
          readOnlyRootFilesystem: true
          runAsNonRoot: true
```

## 🎯 Próximos Pasos

1. **Implementar Tool Gateway básico** con FastAPI
2. **Configurar Policy Engine** con roles y permisos
3. **Implementar Sandbox Executor** con Docker
4. **Integrar con sistema de auditoría** existente
5. **Tests exhaustivos** de seguridad y funcionalidad
6. **Deployment** en entorno de desarrollo

## 📚 Recursos y Referencias

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Docker Security**: https://docs.docker.com/engine/security/
- **Redis Streams**: https://redis.io/docs/data-types/streams/
- **Neo4j Cypher**: https://neo4j.com/docs/cypher-manual/current/