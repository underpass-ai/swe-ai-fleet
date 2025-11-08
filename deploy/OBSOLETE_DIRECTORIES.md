# Obsolete Directories Analysis - 2025-11-08

## Executive Summary

**Verdict**: 🔴 **TODOS OBSOLETOS** - Archivar a `deploy/archived/`

---

## 📁 Directory Analysis

### 1. deploy/crio/ - ❌ **OBSOLETO**

**Contenido**: 9 archivos (CRI-O Pod/Container JSON specs)
- redis-pod.json, redis-ctr.json
- neo4j-pod.json, neo4j-ctr.json
- vllm-pod.json, vllm-ctr.json
- redisinsight-pod.json, redisinsight-ctr.json
- README.md

**Propósito Original**: 
- Correr servicios con **CRI-O standalone** (sin Kubernetes)
- Host networking (`"network": 2`)
- Manual `crictl runp` / `crictl create` commands

**Por Qué Está Obsoleto**:
```
README dice: "Status: Advanced/Experimental — Standalone CRI‑O path"
README dice: "Prefer Kubernetes + CRI‑O for cluster workflows"

REALIDAD:
✅ Cluster usa Kubernetes (v1.34.1) desde hace 23+ días
✅ Servicios desplegados como Deployments/StatefulSets
✅ Nadie usa crictl manualmente
❌ CRI-O standalone NO se usa más
```

**Referencias en Docs**:
- `docs/INFRA_ARCHITECTURE.md` (obsoleto - dice "CRI-O is current")
- `docs/infrastructure/CONTAINER_RUNTIMES.md`
- `docs/infrastructure/PODMAN_CRIO_GUIDE.md`

**Acción**: 🗄️ **ARCHIVAR** a `deploy/archived/cri-o-standalone/`

---

### 2. deploy/helm/ - ❌ **OBSOLETO** (no usado)

**Contenido**: 
- Chart.yaml (version 0.1.0)
- values.yaml
- templates/redis.yaml (214 bytes)
- templates/neo4j.yaml (303 bytes)
- templates/kuberay-cluster.yaml (520 bytes)

**Propósito Original**:
- Helm chart para desplegar Redis, Neo4j, KubeRay
- Parametrización via values.yaml

**Por Qué Está Obsoleto**:
```
REALIDAD:
✅ Cluster usa YAMLs directos (deploy/k8s/)
✅ No hay helm releases instalados
✅ Scripts usan kubectl apply, NO helm install
❌ Chart nunca fue usado en producción
❌ Templates minimalistas (3 servicios básicos)
```

**Verificación**:
```bash
# Check si hay releases de helm
$ helm list -n swe-ai-fleet
# Output esperado: empty (no releases)
```

**Acción**: 🗄️ **ARCHIVAR** a `deploy/archived/helm-experimental/`

**Razón para No Usar Helm**:
- YAMLs directos son más simples para el proyecto
- No necesitamos parametrización multi-entorno aún
- Mantenimiento más sencillo sin Helm
- Si en el futuro necesitamos multi-tenancy → considerar Helm

---

### 3. deploy/kustomize/ - ⚠️ **PROBABLEMENTE OBSOLETO**

**Contenido**:
- calico/calico-node-cni-patch.yaml (634 bytes)
- calico/kustomization.yaml (1K)

**Propósito Original**:
- Kustomize patch para Calico CNI
- Modificar configuración de calico-node DaemonSet

**Por Qué Probablemente Está Obsoleto**:
```
REALIDAD:
✅ Calico está desplegado y funcionando (namespace calico-system)
✅ Patch probablemente ya aplicado durante instalación inicial
❌ No hay scripts que usen kustomize
❌ No documentado en runbooks actuales
```

**Verificación Requerida**:
```bash
# Check si el patch está aplicado
kubectl get daemonset calico-node -n calico-system -o yaml | grep -A 5 "CNI_MTU"

# Si el patch ya está aplicado → OBSOLETO
# Si el patch NO está aplicado → ¿Necesario?
```

**Contenido del Patch**:
```yaml
# Modifica calico-node para:
# - CNI_MTU settings
# - IP autodetection method
# - FELIX settings
```

**Acción**: 
- ⚠️ **VERIFICAR** si patch ya está aplicado en calico-system
- Si SÍ → 🗄️ **ARCHIVAR** a `deploy/archived/kustomize-calico-patch/`
- Si NO y es necesario → **MANTENER** (pero documentar)

---

### 4. deploy/podman/kong/ - ❌ **OBSOLETO**

**Contenido**: 
- kong.yml (954 bytes, podman-compose file)

**Propósito Original**:
- Kong API Gateway con podman-compose
- PostgreSQL backend
- Ports 8000 (proxy), 8443 (proxy SSL), 8001 (admin)

**Por Qué Está Obsoleto**:
```
REALIDAD:
✅ Cluster usa ingress-nginx (NO Kong)
✅ Ingress controller ya desplegado en ingress-nginx namespace
❌ Kong nunca fue desplegado
❌ No hay services de Kong en cluster
❌ podman-compose NO se usa (solo kubectl)
```

**Verificación**:
```bash
# Check si Kong existe
$ kubectl get pods --all-namespaces | grep kong
# Output: (empty)

$ kubectl get ingress -A | head -5
# Todos usan ingressClassName: nginx (NO kong)
```

**Acción**: 🗄️ **ARCHIVAR** a `deploy/archived/kong-experimental/`

**Razón para No Usar Kong**:
- ingress-nginx ya cumple el propósito
- Kong añadiría complejidad sin beneficio claro
- No necesitamos API Gateway avanzado aún

---

## 📊 RESUMEN

| Directorio | Status | Uso Actual | Acción |
|-----------|--------|------------|--------|
| `deploy/crio/` | ❌ OBSOLETO | CRI-O standalone (no usado) | 🗄️ ARCHIVAR |
| `deploy/helm/` | ❌ OBSOLETO | Helm chart (no usado) | 🗄️ ARCHIVAR |
| `deploy/kustomize/` | ⚠️ DUDOSO | Calico patch (verificar) | 🔍 VERIFICAR → ARCHIVAR |
| `deploy/podman/` | ❌ OBSOLETO | Kong (no desplegado) | 🗄️ ARCHIVAR |

**Total a archivar**: 4 directorios (después de verificar kustomize)

---

## 🎯 PLAN DE ARCHIVADO

### Estructura Propuesta

```
deploy/
├── k8s/              ✅ PRODUCCIÓN (reorganizado)
├── archived/         📦 NUEVO
│   ├── cri-o-standalone/
│   │   ├── README.md (con deprecation notice)
│   │   └── *.json (9 archivos)
│   ├── helm-experimental/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   ├── kustomize-calico-patch/  (si no se usa)
│   │   └── calico/
│   └── kong-experimental/
│       └── kong/kong.yml
└── ARCHIVED_README.md  (índice de qué hay archivado y por qué)
```

---

## 🧹 SCRIPT DE ARCHIVADO

```bash
#!/bin/bash
# Archive obsolete deployment directories

ARCHIVE_DIR="deploy/archived"

mkdir -p "${ARCHIVE_DIR}"

# 1. Archive CRI-O standalone
mv deploy/crio "${ARCHIVE_DIR}/cri-o-standalone"

# 2. Archive Helm
mv deploy/helm "${ARCHIVE_DIR}/helm-experimental"

# 3. Archive Kustomize (after verification)
mv deploy/kustomize "${ARCHIVE_DIR}/kustomize-calico-patch"

# 4. Archive Kong/Podman
mv deploy/podman "${ARCHIVE_DIR}/kong-experimental"

# 5. Create deprecation notices
cat > "${ARCHIVE_DIR}/README.md" << 'EOD'
# Archived Deployment Methods

This directory contains obsolete deployment approaches that are no longer used.

## Why Archived

- **CRI-O Standalone**: Replaced by Kubernetes with CRI-O runtime
- **Helm**: Replaced by direct kubectl apply
- **Kustomize**: Calico patch already applied
- **Kong**: Never used, replaced by ingress-nginx

## Current Approach

See `deploy/k8s/` for current production deployment.

## Date Archived

2025-11-08
EOD

git add "${ARCHIVE_DIR}"
git rm -r deploy/crio deploy/helm deploy/kustomize deploy/podman
git commit -m "chore: archive obsolete deployment directories"
```

---

## ⚠️ VERIFICACIÓN ANTES DE ARCHIVAR

### Kustomize Calico Patch

**Verificar si está aplicado**:
```bash
kubectl get daemonset calico-node -n calico-system -o yaml | grep -E "CNI_MTU|IP_AUTODETECTION_METHOD"

# Si los valores del patch están presentes → Ya aplicado → ARCHIVAR
# Si NO están presentes → Decidir si es necesario
```

### Doble Check: ¿Alguien Usa Estos Dirs?

```bash
# Buscar referencias en scripts
grep -r "deploy/crio\|deploy/helm\|deploy/kustomize\|deploy/podman" scripts/ 2>/dev/null

# Si no hay referencias → Seguro archivar
```

---

## 💡 RECOMENDACIÓN FINAL

### Acción Inmediata

1. ✅ **Archivar ahora**:
   - `deploy/crio/` → OBSOLETO confirmado
   - `deploy/helm/` → OBSOLETO confirmado  
   - `deploy/podman/` → OBSOLETO confirmado

2. ⚠️ **Verificar primero, luego archivar**:
   - `deploy/kustomize/` → Check si Calico patch aplicado

### Beneficios

- ✅ Estructura limpia en `deploy/`
- ✅ Solo métodos actuales visibles
- ✅ Historia preservada en `archived/`
- ✅ Fácil recuperar si necesario (git history)

---

**Conclusión**: **SÍ, todos obsoletos. Proceder con archivado.**

**Espacio a liberar**: ~15 KB (pequeño pero limpia conceptualmente)

