# Document Safe HTTP Usage in Configuration Files

## 🎯 Objetivo

Documentar y suprimir warnings de SonarQube sobre el uso de `http://` en archivos de configuración donde es completamente seguro (comunicación interna de red).

## 🔍 Contexto

SonarQube reporta warnings como:
```
"http://vllm-server-service:8000"
Make sure that using clear-text protocols is safe here.
```

Estos warnings son para URLs de **comunicación interna** que **NUNCA salen de la red del cluster/contenedor**.

## 🔧 Cambios Realizados

### 1. Helm Values (`deploy/helm/values.yaml`)

**Archivos documentados:**

```yaml
neo4j:
  boltUri: "bolt://neo4j.default.svc:7687"
  # http:// is safe: internal cluster DNS, traffic stays within cluster network
  httpUri: "http://neo4j.default.svc:7474"  # nosec - internal cluster communication

vllm:
  # http:// is safe: internal cluster DNS, traffic stays within cluster network
  endpoint: "http://vllm.default.svc:8000/v1"  # nosec - internal cluster communication
```

**Por qué es seguro:**
- `neo4j.default.svc` = DNS interno de Kubernetes (`.svc.cluster.local`)
- `vllm.default.svc` = DNS interno de Kubernetes
- Tráfico pod-to-pod dentro del cluster
- Red completamente aislada, nunca sale a internet
- TLS/SSL **NO necesario** para comunicación interna

### 2. Kong Configuration (`deploy/podman/kong/kong.yml`)

**Comentario añadido:**

```yaml
_format_version: "3.0"
_transform: true

# Kong API Gateway configuration for local Podman development
# All http:// URLs are internal to Podman network - safe for dev environment
services:
  - name: web-service
    url: http://swe-web:8080
  - name: vllm-service
    url: http://swe-vllm:8000
  # ... etc
```

**Por qué es seguro:**
- Configuración para **desarrollo local** solamente
- `swe-web`, `swe-vllm`, etc. son nombres DNS de la red Podman
- Red completamente local, no expuesta a internet
- Kong actúa como gateway interno

## 📊 URLs con http:// en el Proyecto

### ✅ Resueltos (Documentados con `# nosec`):
1. **K8s Manifests:**
   - `deploy/k8s/11-orchestrator-service.yaml` - vllm-server-service:8000 ✅
   
2. **Helm Charts:**
   - `deploy/helm/values.yaml` - neo4j httpUri ✅
   - `deploy/helm/values.yaml` - vllm endpoint ✅

3. **Local Dev:**
   - `deploy/podman/kong/kong.yml` - Todas las URLs ✅

### 🟢 No Requieren Cambios (Testing/Dev):
- `docker-compose.yml` - Healthchecks locales (no escaneado por SonarQube)
- `podman-compose.yml` - Healthchecks locales (no escaneado por SonarQube)
- `tests/integration/**/docker-compose*.yml` - Entornos de test (no escaneado)

### 🟢 No Requieren Cambios (Documentación):
- `specs/openapi.yaml` - Ejemplo de localhost endpoint (spec, no código)
- `specs/asyncapi.yaml` - Ejemplo de URI schema (spec, no código)

## 🔒 Principio de Seguridad

**Regla:** Solo usar `http://` para comunicación interna, nunca para tráfico expuesto a internet.

✅ **SEGURO - Comunicación Interna:**
```
http://service-name.namespace.svc.cluster.local:port  ← K8s
http://container-name:port                             ← Docker/Podman
http://localhost:port                                  ← Healthchecks
```

❌ **INSEGURO - Requiere HTTPS:**
```
http://api.example.com          ← Expuesto a internet
http://<PUBLIC_IP>              ← IP pública
```

## 🧪 Impacto

- **No breaking changes** - Solo comentarios y documentación
- **No cambios funcionales** - Las URLs siguen funcionando igual
- **SonarQube Quality Gate** - Debería pasar con anotaciones `# nosec`

## ✅ Verificaciones

- [x] Todas las URLs `http://` revisadas
- [x] URLs internas documentadas con `# nosec`
- [x] Comentarios explicativos añadidos
- [x] No hay URLs públicas con `http://`
- [x] Linter: Sin errores

## 📝 Relación con PR Anterior

Este PR complementa #67 (fix/ci-integration-tests-and-sonarqube) añadiendo documentación para todas las instancias de `http://` en archivos de configuración.

**PR #67 resolvió:**
- Scripts de integración con `docker compose`
- UI Dockerfile con COPY explícito
- Orchestrator K8s manifest con `# nosec`
- Consistencia en nombres de archivos K8s

**Este PR resuelve:**
- Helm values con URLs internas documentadas
- Kong config con comentario explicativo
- Documentación completa de todas las URLs `http://` en el proyecto

## 🔗 Issues Relacionados

- Resuelve: SonarQube warnings sobre `http://` en archivos de configuración
- Mejora: Documentación de seguridad en configuraciones internas

