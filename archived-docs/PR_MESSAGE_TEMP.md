# Fix CI Integration Tests and SonarQube Issues

## 🎯 Objetivo

Resolver problemas críticos que bloquean el CI:
1. Integration tests fallando en GitHub Actions (comando `docker compose` no detectado)
2. SonarQube Quality Gate fallando por warning de seguridad en `ui/po-react/Dockerfile`
3. Inconsistencia en nombres de archivos K8s

## 🔧 Cambios Realizados

### 1. Scripts de Integración - Soporte para `docker compose`

**Archivos modificados:**
- `tests/integration/services/context/run-integration.sh`
- `tests/integration/services/orchestrator/run-integration.sh`

**Cambio:**
```bash
# Antes: solo buscaba podman-compose y docker-compose (con guion)
if command -v podman-compose &> /dev/null; then
    COMPOSE_CMD="podman-compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "❌ Neither podman-compose nor docker-compose found"
    exit 1
fi

# Ahora: también detecta 'docker compose' (comando moderno sin guion)
if command -v podman-compose &> /dev/null; then
    COMPOSE_CMD="podman-compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo "❌ No compose tool found"
    exit 1
fi
```

**Por qué:** GitHub Actions usa Docker con el comando `docker compose` (sin guion), que es la versión moderna post-Docker Compose V2. Los runners de GitHub Actions tienen este comando disponible por defecto.

### 2. UI Dockerfile - Fix SonarQube Security Warning

**Archivos modificados:**
- `ui/po-react/Dockerfile`
- `ui/po-react/.dockerignore` (nuevo)

**Cambio en Dockerfile:**
```dockerfile
# ❌ Antes: COPY recursivo genérico (SonarQube warning)
COPY . .

# ✅ Ahora: COPY explícito solo de archivos necesarios
COPY index.html ./
COPY tsconfig*.json ./
COPY vite.config.ts ./
COPY tailwind.config.js ./
COPY postcss.config.js ./
COPY src/ ./src/
```

**Nuevo `.dockerignore`:**
Excluye archivos innecesarios del build context:
- `node_modules/` (se instala con npm ci)
- `.env*` (archivos de entorno sensibles)
- Archivos de IDE (`.vscode/`, `.idea/`)
- Documentación (`.md`, `README*`)
- Archivos de CI/CD
- Logs y temporales

**Verificación:**
```bash
$ podman build -t swe-fleet-ui:test ui/po-react/
✓ 30 modules transformed.
dist/index.html                   0.52 kB │ gzip:  0.35 kB
dist/assets/index-B4EjVe-j.css   12.51 kB │ gzip:  3.16 kB
dist/assets/index-AxMPb1BT.js   151.52 kB │ gzip: 48.38 kB
✓ built in 1.01s
Successfully tagged localhost/swe-fleet-ui:test
```

**Por qué:** SonarQube marcaba `COPY . .` como potencialmente inseguro porque podría copiar archivos sensibles (`.env`, secrets, etc.). El enfoque explícito es más seguro y es una best practice.

### 3. K8s Manifests - Consistencia en Nombres

**Cambio:**
```
deploy/k8s/orchestrator-service.yaml → deploy/k8s/11-orchestrator-service.yaml
```

**Documentación actualizada:**
- `services/orchestrator/README.md`
- `docs/microservices/ORCHESTRATOR_SERVICE.md`
- `docs/microservices/VLLM_AGENT_DEPLOYMENT.md`
- `docs/microservices/ORCHESTRATOR_INTERACTIONS.md`
- `docs/MICROSERVICES_BUILD_PATTERNS.md`

**Por qué:** Mantener consistencia con el patrón de numeración existente:
```
08-context-service.yaml
09-neo4j.yaml
10-valkey.yaml
11-orchestrator-service.yaml  ← ahora consistente
```

### 4. CI Workflow - Integration Tests en PRs (Temporal)

**Archivo modificado:**
- `.github/workflows/ci.yml`

**Cambio:**
```yaml
# Antes: solo en main
if: github.ref == 'refs/heads/main' && github.event_name == 'push'

# Ahora: también en PRs (temporal para validación)
if: github.event_name == 'pull_request' || (github.ref == 'refs/heads/main' && github.event_name == 'push')
```

**Por qué:** Permite validar que los integration tests funcionan correctamente en CI antes de hacer merge a main. Una vez confirmado que funciona, se puede revertir a solo ejecutar en main para ahorrar recursos de CI.

## 📊 Archivos Modificados

```
 .github/workflows/ci.yml                                   |  8 ++--
 deploy/k8s/{orchestrator-service.yaml => 11-orchestrator-service.yaml} |  0
 docs/MICROSERVICES_BUILD_PATTERNS.md                       |  2 +-
 docs/microservices/ORCHESTRATOR_INTERACTIONS.md            |  2 +-
 docs/microservices/ORCHESTRATOR_SERVICE.md                 |  4 +-
 docs/microservices/VLLM_AGENT_DEPLOYMENT.md                |  4 +-
 services/orchestrator/README.md                            |  2 +-
 tests/integration/services/context/run-integration.sh      |  6 ++-
 tests/integration/services/orchestrator/run-integration.sh |  6 ++-
 ui/po-react/.dockerignore                                  | 56 ++++++++++++++++++
 ui/po-react/Dockerfile                                     |  8 ++-
 11 files changed, 75 insertions(+), 20 deletions(-)
```

## ✅ Verificaciones Locales

- [x] **Linter:** `ruff check .` - Sin errores
- [x] **Docker Build:** `podman build ui/po-react/` - Exitoso
- [x] **Git:** Todos los cambios staged correctamente
- [x] **Documentación:** Referencias actualizadas consistentemente

## 🧪 Testing en CI

Este PR habilitará:
1. ✅ **Unit Tests** - Ya funcionando
2. ✅ **Integration Tests** - Ahora deberían ejecutarse correctamente con `docker compose`
3. ✅ **SonarQube** - No debería mostrar el warning de seguridad

## 🔄 Cambios Adicionales (Segundo Commit)

### Integration Tests Validados ✅
- **Integration tests pasaron correctamente en CI**
- Restaurada configuración original: solo ejecutar en `main` branch
- Ahorra recursos de CI ejecutando solo después de merge

### SonarQube Warning: http:// en URLs Internas
**Warning:**
```
"http://vllm-server-service:8000"
Make sure that using clear-text protocols is safe here.
```

**Solución - Documentación y Supresión:**
```yaml
- name: VLLM_URL
  # http:// is safe here: internal cluster communication only
  # Traffic never leaves the cluster network, TLS not required for pod-to-pod
  value: "http://vllm-server-service:8000"  # nosec - internal cluster communication
```

**Por qué es seguro:**
- `vllm-server-service` es DNS interno de Kubernetes (`.svc.cluster.local`)
- Comunicación pod-to-pod dentro del cluster
- Tráfico nunca sale de la red del cluster
- TLS/SSL no requerido para comunicación interna
- Añadida anotación `# nosec` para SonarQube

## 🔄 Próximos Pasos

1. ✅ ~~Validar que integration tests pasen en GitHub Actions~~ - **COMPLETADO**
2. Confirmar que SonarQube Quality Gate pasa con anotación `nosec`
3. ✅ ~~Revertir cambio temporal de integration tests en PRs~~ - **COMPLETADO**

## 📝 Notas

- **No breaking changes** - Solo fixes de CI/CD y mejoras de seguridad
- **Backward compatible** - Scripts siguen detectando `podman-compose` y `docker-compose`
- **Documentación completa** - Todas las referencias actualizadas

## 🔗 Issues Relacionados

- Resuelve: Integration tests fallando en CI (docker compose no detectado)
- Resuelve: SonarQube Quality Gate fallando (security warning en Dockerfile)
- Mejora: Consistencia en nombres de archivos K8s

