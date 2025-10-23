# SWE AI Fleet - Agent Tools

Comprehensive toolset for AI agents to perform software engineering tasks within isolated workspace containers.

## 🎯 Overview

This module provides a secure, auditable toolkit for AI agents to interact with:
- **Git** - Version control operations
- **Files** - Read, write, search, edit code
- **Tests** - Execute test suites (pytest, go test, npm, cargo)
- **Docker** - Build and run containers
- **HTTP** - Call REST APIs
- **Databases** - Query PostgreSQL, Redis, Neo4j
- **Audit** - Complete operation traceability

## 🔒 Security Features

All tools implement:
- ✅ **Workspace isolation** - Operations restricted to workspace directory
- ✅ **Input validation** - Prevent path traversal, command injection
- ✅ **Timeout protection** - Automatic termination of long-running operations
- ✅ **Resource limits** - Memory and CPU constraints
- ✅ **Audit trail** - Every operation logged (file + Redis + Neo4j)
- ✅ **No credential logging** - Passwords and tokens redacted
- ✅ **Error handling** - Graceful failure without leaking info

## 📦 Tools Reference

### 1. Git Tool (`git_tool.py`)

Operations: `clone`, `status`, `add`, `commit`, `push`, `pull`, `checkout`, `branch`, `diff`, `log`

```python
from swe_ai_fleet.tools import GitTool

git = GitTool("/workspace")

# Clone repository
result = git.clone("https://github.com/user/repo.git", branch="main", depth=1)

# Make changes
git.add(["src/main.py"])
git.commit("feat: add new feature", author="Agent <agent@example.com>")

# Push changes
git.push("origin", "main")

# Check status
status = git.status(short=True)
print(status.stdout)
```

### 2. File Tool (`file_tool.py`)

Operations: `read`, `write`, `append`, `search`, `list`, `edit`, `delete`, `mkdir`, `info`, `diff`

```python
from swe_ai_fleet.tools import FileTool

files = FileTool("/workspace")

# Read file
result = files.read_file("src/main.py")
print(result.content)

# Write file
files.write_file("src/utils.py", "def helper(): pass")

# Search in files
results = files.search_in_files("def main", extensions=[".py"])
print(results.content)

# Edit file (search & replace)
files.edit_file("src/main.py", search="old_name", replace="new_name")

# List files
listing = files.list_files("src/", recursive=True, pattern="*.py")

# Diff files
diff = files.diff_files("src/main.py")  # Git diff
# or
diff = files.diff_files("file1.py", "file2.py")  # Compare two files
```

### 3. Test Tool (`test_tool.py`)

Frameworks: `pytest`, `go`, `npm`, `cargo`, `make`

```python
from swe_ai_fleet.tools import TestTool

tests = TestTool("/workspace")

# Run pytest
result = tests.pytest(
    markers="not e2e and not integration",
    verbose=True,
    coverage=True,
    junit_xml="/workspace/test-reports/junit.xml"
)

# Run Go tests
result = tests.go_test(
    package="./pkg/...",
    coverage=True,
    race=True
)

# Run npm tests
result = tests.npm_test(script="test:unit")

# Run cargo tests
result = tests.cargo_test(package="mylib")
```

### 4. Docker Tool (`docker_tool.py`)

Operations: `build`, `run`, `exec`, `ps`, `logs`, `stop`, `rm`

```python
from swe_ai_fleet.tools import DockerTool

docker = DockerTool("/workspace")  # Auto-detects podman or docker

# Build image
result = docker.build(
    context_path=".",
    tag="myapp:latest",
    no_cache=False
)

# Run container
result = docker.run(
    image="python:3.13",
    command=["python", "-c", "print('hello')"],
    env={"ENV_VAR": "value"},
    volumes={"/tmp/data": "/data"},
    rm=True
)

# Execute in running container
result = docker.exec("container-name", ["ls", "-la"])

# Get logs
result = docker.logs("container-name", tail=100)
```

### 5. HTTP Tool (`http_tool.py`)

Methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`

```python
from swe_ai_fleet.tools import HttpTool

http = HttpTool(allow_localhost=True)  # For testing

# GET request
result = http.get("https://api.example.com/users")
print(result.status_code, result.body)

# POST request with JSON
result = http.post(
    "https://api.example.com/users",
    json_data={"name": "John", "email": "john@example.com"},
    headers={"Authorization": "Bearer token123"}
)

# PUT request
result = http.put(
    "https://api.example.com/users/123",
    json_data={"name": "John Updated"}
)
```

### 6. Database Tool (`db_tool.py`)

Databases: PostgreSQL, Redis, Neo4j

```python
from swe_ai_fleet.tools import DatabaseTool

db = DatabaseTool()

# PostgreSQL query
result = db.postgresql_query(
    "postgresql://user:pass@localhost:5432/mydb",
    "SELECT * FROM users WHERE id = %s",
    params=(123,)
)
print(result.data)

# Redis command
result = db.redis_command(
    "redis://localhost:6379/0",
    ["GET", "mykey"]
)
print(result.data)

# Neo4j Cypher query
result = db.neo4j_query(
    "bolt://localhost:7687",
    "neo4j",
    "password",
    "MATCH (n:User) RETURN n LIMIT 10"
)
print(result.data)
```

### 7. Validators (`validators.py`)

Security validation functions:

```python
from swe_ai_fleet.tools import (
    validate_path,
    validate_url,
    validate_git_url,
    validate_command_args,
    validate_env_vars,
    validate_container_image,
    sanitize_log_output
)

# Validate path is within workspace
validate_path("src/main.py", "/workspace")  # OK
validate_path("../../etc/passwd", "/workspace")  # Raises ValueError

# Validate URL
validate_url("https://api.example.com")  # OK
validate_url("file:///etc/passwd")  # Raises ValueError

# Validate Git URL
validate_git_url("https://github.com/user/repo.git")  # OK
validate_git_url("file:///tmp/repo")  # Raises ValueError

# Validate command args (prevent injection)
validate_command_args(["ls", "-la"])  # OK
validate_command_args(["ls", "; rm -rf /"])  # Raises ValueError
```

### 8. Audit System (`audit.py`)

Complete operation traceability:

```python
from swe_ai_fleet.tools import configure_audit_logger, get_audit_logger

# Configure at startup
logger = configure_audit_logger(
    log_file="/workspace/.task/audit.log",
    redis_client=redis_client,  # Optional
    neo4j_driver=neo4j_driver   # Optional
)

# Tools automatically log operations
git = GitTool("/workspace", audit_callback=logger.log)
git.commit("feat: new feature")  # Automatically audited

# Or manually log
from swe_ai_fleet.tools import audit_tool_operation

audit_tool_operation({
    "tool": "custom",
    "operation": "analyze",
    "params": {"file": "main.py"},
    "success": True,
    "metadata": {"lines": 100}
})

# Query audit logs
logger.query_logs(tool="git", success=True, limit=50)
```

## 🏗️ Architecture

### Tool Execution Flow

```
Agent → Tool Call → Validators → Tool Execution → Audit → Result
                      ↓              ↓               ↓
                    Security      Workspace      Redis/Neo4j
                    Checks        Container      Event Store
```

### Integration with Runner

```python
# tools/runner/runner_tool.py uses these tools internally

from swe_ai_fleet.tools import (
    GitTool, FileTool, TestTool, 
    configure_audit_logger
)

# In workspace container:
workspace_path = "/workspace"
audit_logger = configure_audit_logger(
    log_file=f"{workspace_path}/.task/audit.log"
)

# Tools available to agent
git = GitTool(workspace_path, audit_callback=audit_logger.log)
files = FileTool(workspace_path, audit_callback=audit_logger.log)
tests = TestTool(workspace_path, audit_callback=audit_logger.log)
```

## 📋 Usage Patterns

### Pattern 1: Code Review & Fix

```python
# 1. Clone repo
git.clone("https://github.com/user/repo.git", branch="fix/bug-123")

# 2. Read file
code = files.read_file("src/module.py")

# 3. Search for pattern
issues = files.search_in_files("TODO|FIXME", path="src/")

# 4. Edit file
files.edit_file("src/module.py", 
    search="old_implementation",
    replace="new_implementation"
)

# 5. Run tests
test_result = tests.pytest(markers="not e2e", coverage=True)

# 6. Commit if tests pass
if test_result.success:
    git.add("all")
    git.commit("fix: resolve issue #123")
    git.push("origin", "fix/bug-123")
```

### Pattern 2: API Integration Test

```python
# 1. Start service in container
docker.run(
    image="myapp:latest",
    ports={"8080": "8080"},
    detach=True,
    name="test-service"
)

# 2. Wait for readiness
import time
time.sleep(5)

# 3. Test API
result = http.get("http://localhost:8080/health")
assert result.status_code == 200

# 4. Run integration tests
test_result = tests.pytest(markers="integration")

# 5. Cleanup
docker.stop("test-service")
docker.rm("test-service")
```

### Pattern 3: Database Migration

```python
# 1. Read migration file
migration = files.read_file("migrations/001_create_users.sql")

# 2. Execute migration
result = db.postgresql_query(
    "postgresql://user:pass@localhost:5432/mydb",
    migration.content
)

# 3. Verify
verify = db.postgresql_query(
    "postgresql://user:pass@localhost:5432/mydb",
    "SELECT count(*) FROM users"
)

# 4. Log results
files.write_file(
    "migration-results.txt",
    f"Migration completed: {result.rows_affected} rows affected"
)
```

## 🧪 Testing

Run unit tests for tools:

```bash
# Test all tools
pytest tests/unit/tools/ -v

# Test specific tool
pytest tests/unit/tools/test_git_tool.py -v

# With coverage
pytest tests/unit/tools/ --cov=swe_ai_fleet.tools
```

## 📚 Dependencies

**Required** (always installed):
- `pathlib` (stdlib)
- `subprocess` (stdlib)

**Optional** (install as needed):
```bash
# HTTP client
pip install requests

# PostgreSQL
pip install psycopg2-binary

# Redis
pip install redis

# Neo4j
pip install neo4j
```

Or install all at once:
```bash
pip install -e ".[tools]"  # When added to pyproject.toml
```

## 🔧 Configuration

### Environment Variables

Tools respect standard environment variables:

```bash
# Git
export GIT_AUTHOR_NAME="Agent Name"
export GIT_AUTHOR_EMAIL="agent@example.com"
export GIT_COMMITTER_NAME="Agent Name"
export GIT_COMMITTER_EMAIL="agent@example.com"

# PostgreSQL
export PGUSER=postgres
export PGPASSWORD=secret

# Redis
export REDIS_URL=redis://localhost:6379/0

# Neo4j
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password
```

### Workspace Structure

```
/workspace/
  /.git/              ← Git repository
  /.task/             ← Task metadata
    /audit.log        ← Audit trail (NDJSON)
    /task-spec.json   ← Task specification
  /src/               ← Source code
  /tests/             ← Tests
  /coverage/          ← Coverage reports
  /test-reports/      ← Test artifacts
```

## 🚀 Integration with Runner

These tools are designed to work within the Runner's workspace container:

1. **Runner creates workspace** - Isolated directory per task
2. **Tools execute operations** - Within workspace boundaries
3. **Audit trail collected** - All operations logged
4. **Results published** - Via NATS to orchestrator

See `tools/runner/README.md` for Runner integration details.

## 🎯 Roadmap

### ✅ Completed (v0.1.0)
- [x] Git operations (9 commands)
- [x] File operations (10 commands)
- [x] Test execution (5 frameworks)
- [x] Docker operations (7 commands)
- [x] HTTP client (6 methods)
- [x] Database clients (3 databases)
- [x] Security validators (8 functions)
- [x] Audit system (file + Redis + Neo4j)

### 🚧 Next (v0.2.0)
- [ ] Tool Gateway (FastAPI) for unified API
- [ ] Policy Engine (RBAC) for fine-grained access
- [ ] Advanced sandboxing (seccomp, AppArmor)
- [ ] Tool chaining and workflows
- [ ] Metrics and monitoring
- [ ] Tool usage analytics

### 🔮 Future (v1.0.0)
- [ ] Code analysis tools (AST, complexity)
- [ ] Lint tools (ruff, golangci-lint)
- [ ] Build tools (make, npm build)
- [ ] Deploy tools (kubectl apply, helm install)
- [ ] AI-specific tools (embedding, vector search)

## 📖 Related Documentation

- [Runner System](runner/README.md)
- [Agent Architecture](../../docs/architecture/DELIBERATE_ORCHESTRATE_DESIGN.md)
- [Security Policy](../../SECURITY.md)
- [API Specifications](../../specs/)

## 🤝 Contributing

When adding new tools:

1. Follow the existing pattern:
   - Create `XyzTool` class
   - Implement `XyzResult` dataclass
   - Add `execute_xyz_operation()` convenience function
   - Include audit callback support

2. Add security checks:
   - Input validation in `validators.py`
   - Workspace isolation
   - Timeout protection
   - Audit logging

3. Write tests:
   - Unit tests in `tests/unit/tools/`
   - Integration tests if needed

4. Update exports:
   - Add to `__init__.py`
   - Update this README

## 📄 License

Apache License 2.0 - See [LICENSE](../../LICENSE)

