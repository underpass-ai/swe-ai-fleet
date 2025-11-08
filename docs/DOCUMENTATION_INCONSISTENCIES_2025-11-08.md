# Documentation Inconsistencies - 2025-11-08

**Date**: 2025-11-08  
**Context**: Post deploy/ reorganization and cluster restoration  
**Status**: 🔴 **CRÍTICAS** - Requieren actualización urgente  

---

## Executive Summary

**Inconsistencias encontradas**: 7 tipos, ~100+ referencias incorrectas

**Impacto**:
- 🔴 Usuarios seguirán paths incorrectos → comandos fallan
- 🔴 Docs mencionan servicios obsoletos (StoryCoach, Workspace)
- 🔴 Registry namespace mixto causa confusión
- 🟡 Referencias a CRI-O standalone (archivado)

**Acción requerida**: Actualizar ~20 documentos

---

## 🔴 INCONSISTENCIA #1: Paths Legacy de deploy/k8s/ (CRÍTICO)

### Problema

**49 referencias** a paths con numeración legacy en **17 archivos**:

```
❌ deploy/k8s/08-context-service.yaml
❌ deploy/k8s/11-orchestrator-service.yaml
❌ deploy/k8s/12-planning-service.yaml
❌ deploy/k8s/14-ray-executor.yaml
etc.
```

**Nuevos paths correctos**:

```
✅ deploy/k8s/30-microservices/context.yaml
✅ deploy/k8s/30-microservices/orchestrator.yaml
✅ deploy/k8s/30-microservices/planning.yaml
✅ deploy/k8s/30-microservices/ray-executor.yaml
```

### Archivos Afectados (Top 10)

| Archivo | Referencias | Prioridad |
|---------|-------------|-----------|
| `architecture/decisions/2025-11-06/RBAC_L2_FINAL_STATUS.md` | 10 | 🔴 ALTA |
| `sessions/2025-10-21/SESSION_PERSISTENT_STREAMS.md` | 6 | 🟡 MEDIA |
| `monitoring/OBSERVABILITY_SETUP.md` | 6 | 🟡 MEDIA |
| `examples/PLANNING_WITH_TOOLS.md` | 5 | 🟡 MEDIA |
| `summaries/RAY_JOBS_STATUS.md` | 3 | 🟡 BAJA |
| `getting-started/README.md` | 2 | 🔴 ALTA |
| `infrastructure/RAYCLUSTER_INTEGRATION.md` | 2 | 🟡 MEDIA |

### Fix Recomendado

```bash
# Buscar y reemplazar en docs/
find docs/ -name "*.md" -type f -exec sed -i \
  's|deploy/k8s/08-context-service.yaml|deploy/k8s/30-microservices/context.yaml|g' {} \;

find docs/ -name "*.md" -type f -exec sed -i \
  's|deploy/k8s/11-orchestrator-service.yaml|deploy/k8s/30-microservices/orchestrator.yaml|g' {} \;

# (Y así para todos los servicios)
```

---

## 🔴 INCONSISTENCIA #2: Puerto de Planning (CRÍTICO)

### Problema

**6 referencias** a Planning en puerto **50053** (incorrecto):

```
❌ planning:50053
❌ internal-planning:50053
❌ port 50053 (en contexto de planning)
```

**Puerto correcto**: **50054** (corregido en ConfigMaps y YAMLs el 2025-11-08)

### Fix Requerido

```bash
# Reemplazar referencias a Planning puerto 50053 → 50054
grep -r "planning.*50053\|50053.*planning" docs/ --include="*.md" -l | \
  xargs sed -i 's/:50053/:50054/g' (solo en contexto de planning)
```

**Manualmente verificar**: No confundir con otros servicios en 50053

---

## 🟡 INCONSISTENCIA #3: CRI-O Standalone Referencias (MEDIO)

### Problema

**Referencias a CRI-O standalone** en **7 archivos** (fuera de archived/):

| Archivo | Referencias | Obsoleto? |
|---------|-------------|-----------|
| `GOLDEN_PATH.md` | 9 | ⚠️ PARCIAL (secciones específicas) |
| `infrastructure/INSTALL_CRIO.md` | 8 | ⚠️ PARCIAL (instalación CRI-O válida) |
| `infrastructure/CONTAINER_RUNTIMES.md` | 2 | ⚠️ PARCIAL |
| `infrastructure/PODMAN_CRIO_GUIDE.md` | 1 | ⚠️ PARCIAL |
| `operations/TROUBLESHOOTING_CRIO.md` | 1 | ⚠️ ÚTIL (troubleshooting de CRI-O como runtime) |
| `reference/rfcs/RFC-0004-worker-setup.md` | 2 | ✅ HISTÓRICO (mantener) |
| `INDEX.md` | 1 | ⚠️ ACTUALIZAR índice |

### Acción Recomendada

**NO archivar estos docs completos**, sino:

1. **GOLDEN_PATH.md**: Añadir deprecation notice en secciones CRI-O standalone
2. **INSTALL_CRIO.md**: OK - instalación de CRI-O como runtime K8s es válida
3. **CONTAINER_RUNTIMES.md**: Añadir nota "standalone deprecated, K8s current"
4. **PODMAN_CRIO_GUIDE.md**: Añadir deprecation notice
5. **TROUBLESHOOTING_CRIO.md**: OK - troubleshooting de runtime es válido
6. **INDEX.md**: Actualizar con nueva estructura

---

## 🔴 INCONSISTENCIA #4: Registry Namespace Mixto (CRÍTICO)

### Problema

**65 referencias** a registry namespace (inconsistente):

```
registry.underpassai.com/swe-fleet:       56 referencias
registry.underpassai.com/swe-ai-fleet:     9 referencias
```

**Ratio**: 56:9 (mayoría usa `swe-fleet`)

### Archivos Afectados (Muestra)

- `architecture/WORKFLOW_ORCHESTRATION_SERVICE_DESIGN.md`
- `testing/E2E_JOBS_K8S_GUIDE.md`
- `sessions/2025-10-21/...` (múltiples)
- `evidence/...` (múltiples)
- `microservices/VLLM_AGENT_DEPLOYMENT.md`

### Decisión Arquitectónica Requerida

**Opción A (RECOMENDADA)**: Unificar a `swe-ai-fleet`
- ✅ Align con namespace K8s (`swe-ai-fleet`)
- ✅ Scripts ya usan `swe-ai-fleet`
- ❌ Requiere actualizar 56 referencias

**Opción B**: Unificar a `swe-fleet`
- ✅ Mayoría ya usa este nombre
- ❌ Desalineado con namespace K8s
- ❌ Requiere actualizar scripts

**Recomendación**: **Opción A** + crear ADR-001-registry-namespace.md

### Fix Recomendado

```bash
# Buscar y reemplazar globalmente
find docs/ -name "*.md" -type f -exec sed -i \
  's|registry.underpassai.com/swe-fleet/|registry.underpassai.com/swe-ai-fleet/|g' {} \;

# También actualizar YAMLs en deploy/k8s/
find deploy/k8s -name "*.yaml" -type f -exec sed -i \
  's|registry.underpassai.com/swe-fleet/|registry.underpassai.com/swe-ai-fleet/|g' {} \;
```

---

## 🟡 INCONSISTENCIA #5: Scripts Obsoletos (MEDIO)

### Problema

Referencias a scripts que ya no existen o fueron renombrados:

| Script Mencionado | Estado | Archivo Correcto |
|-------------------|--------|------------------|
| `deploy-all.sh` | ❌ NO EXISTE | `fresh-redeploy.sh` |
| `rebuild-and-deploy.sh` | ❌ NO EXISTE | `fresh-redeploy.sh` |

### Archivos Afectados

- `audits/current/DOCUMENTATION_INCONSISTENCIES_2025-11-07.md`
- `operations/DEPLOYMENT.md`
- `sessions/2025-10-21/TEST_RESULTS_20251021.md`
- `TESTING_ARCHITECTURE.md`

### Fix Recomendado

```bash
find docs/ -name "*.md" -type f -exec sed -i \
  's|deploy-all.sh|fresh-redeploy.sh|g' {} \;

find docs/ -name "*.md" -type f -exec sed -i \
  's|rebuild-and-deploy|fresh-redeploy|g' {} \;
```

---

## 🟡 INCONSISTENCIA #6: Servicios Obsoletos Mencionados (MEDIO)

### Problema

**24 referencias** a servicios que NO están en producción actualmente:

```
❌ StoryCoach (mencionado en docs, NO desplegado)
❌ Workspace (mencionado en docs, NO desplegado)
```

**Servicios en Producción** (verificado con `kubectl get pods`):
```
✅ orchestrator
✅ context
✅ planning
✅ workflow
✅ ray-executor
✅ monitoring-dashboard
✅ vllm-server
```

### Archivos con Referencias

Múltiples archivos en:
- `docs/architecture/`
- `docs/sessions/`
- `docs/summaries/`

### Acción Requerida

**Investigar**:
1. ¿StoryCoach y Workspace están deprecated?
2. ¿O están en `04-services.yaml` (que eliminamos)?
3. ¿Necesitan volver a desplegarse?

**Si están deprecated**:
- Añadir deprecation notice en docs que los mencionen
- Crear SERVICES_DEPRECATED.md con status

**Si están vigentes pero no desplegados**:
- Desplegar usando nueva estructura
- O explicar por qué no están desplegados

---

## 🟡 INCONSISTENCIA #7: Referencias a Helm/Kustomize (BAJO)

### Problema

**1 referencia** a Helm/Kustomize en `infrastructure/INSTALL_K8S_CRIO_GPU.md`

**Context**: Helm y Kustomize fueron archivados (no se usan)

### Fix Recomendado

Añadir nota en INSTALL_K8S_CRIO_GPU.md:

```markdown
> **Note**: This guide mentions Helm charts. Those have been archived.
> Current deployment uses direct kubectl apply.
> See: deploy/k8s/README.md
```

---

## 📋 PLAN DE CORRECCIÓN

### Fase 1: Fixes Críticos (P0) - 1 hora

1. **Actualizar paths de deploy/k8s/** en docs top-level:
   - `getting-started/README.md` ✅
   - `getting-started/quickstart.md` ✅
   - `operations/DEPLOYMENT.md` ✅

2. **Corregir puerto de Planning** (50053→50054):
   - Buscar y reemplazar cuidadosamente

3. **Añadir deprecation notice** en docs CRI-O:
   - GOLDEN_PATH.md
   - CONTAINER_RUNTIMES.md
   - PODMAN_CRIO_GUIDE.md

### Fase 2: Unificación Registry (P1) - 1-2 horas

4. **Decidir namespace**: `swe-ai-fleet` (recomendado)

5. **Crear ADR**: `docs/architecture/decisions/ADR-001-registry-namespace.md`

6. **Buscar y reemplazar** globalmente:
   - 56 referencias en docs/
   - 13 imágenes en deploy/k8s/

### Fase 3: Limpieza General (P2) - 2-3 horas

7. **Investigar StoryCoach/Workspace** status

8. **Actualizar scripts references**:
   - deploy-all.sh → fresh-redeploy.sh

9. **Session docs** (2025-10-21): Añadir "Historical" notice

### Fase 4: Índices y Navigation (P3) - 1 hora

10. **Actualizar INDEX.md** con nueva estructura

11. **Crear deploy/k8s/INDEX.md** visual (tree structure)

12. **Actualizar README.md** principal con nueva estructura

---

## 🎯 PRIORIZACIÓN

### CRÍTICO (Hacer HOY)

| Issue | Archivos | Impacto | Esfuerzo |
|-------|----------|---------|----------|
| #1: Deploy paths | 17 docs | 🔴 Alto | 30 min |
| #2: Planning puerto | 6 refs | 🔴 Alto | 15 min |
| #4: Registry namespace | 65 refs | 🔴 Alto | 1h |

**Total P0**: ~2 horas

### ALTO (Esta Semana)

| Issue | Archivos | Impacto | Esfuerzo |
|-------|----------|---------|----------|
| #3: CRI-O standalone | 7 docs | 🟡 Medio | 30 min |
| #5: Scripts obsoletos | 4 docs | 🟡 Medio | 15 min |
| #7: Helm/Kustomize | 1 doc | 🟡 Bajo | 5 min |

**Total P1**: ~1 hora

### MEDIO (Próxima Semana)

| Issue | Archivos | Impacto | Esfuerzo |
|-------|----------|---------|----------|
| #6: StoryCoach/Workspace | 24 refs | 🟡 Medio | 1h (investigar) |

---

## 🔧 SCRIPT DE CORRECCIÓN AUTOMÁTICA

```bash
#!/bin/bash
# Fix documentation inconsistencies

set -e

echo "🔧 Corrigiendo inconsistencias en documentación..."

# 1. Fix deploy paths (crítico)
echo "1️⃣  Actualizando paths de deploy/k8s/..."

find docs/ -name "*.md" -type f ! -path "*/archived/*" -exec sed -i \
  -e 's|deploy/k8s/08-context-service.yaml|deploy/k8s/30-microservices/context.yaml|g' \
  -e 's|deploy/k8s/11-orchestrator-service.yaml|deploy/k8s/30-microservices/orchestrator.yaml|g' \
  -e 's|deploy/k8s/12-planning-service.yaml|deploy/k8s/30-microservices/planning.yaml|g' \
  -e 's|deploy/k8s/14-ray-executor.yaml|deploy/k8s/30-microservices/ray-executor.yaml|g' \
  -e 's|deploy/k8s/15-workflow-service.yaml|deploy/k8s/30-microservices/workflow.yaml|g' \
  -e 's|deploy/k8s/13-monitoring-dashboard.yaml|deploy/k8s/40-monitoring/monitoring-dashboard.yaml|g' \
  -e 's|deploy/k8s/15-nats-streams-init.yaml|deploy/k8s/20-streams/nats-streams-init.yaml|g' \
  {} \;

# 2. Fix Planning port (crítico)
echo "2️⃣  Corrigiendo puerto de Planning..."

# Cuidado: solo reemplazar en contexto de Planning
grep -rl "planning.*50053\|50053.*planning" docs/ --include="*.md" | \
  xargs sed -i 's/planning:50053/planning:50054/gi'

# 3. Fix obsolete script names
echo "3️⃣  Actualizando nombres de scripts..."

find docs/ -name "*.md" -type f ! -path "*/archived/*" -exec sed -i \
  -e 's|deploy-all\.sh|fresh-redeploy.sh|g' \
  -e 's|rebuild-and-deploy|fresh-redeploy|g' \
  {} \;

# 4. Registry namespace (requiere decisión - comentado)
# echo "4️⃣  Unificando registry namespace a swe-ai-fleet..."
# find docs/ -name "*.md" -type f -exec sed -i \
#   's|registry.underpassai.com/swe-fleet/|registry.underpassai.com/swe-ai-fleet/|g' {} \;

echo ""
echo "✅ Correcciones automáticas completadas"
echo "⚠️  Registry namespace NO corregido (requiere decisión ADR)"
```

---

## ⚠️ CASOS ESPECIALES

### Session Docs (2025-10-21)

**Issue**: Referencias a paths legacy son **históricamente correctas**

**Solución**: Añadir header note:

```markdown
> **Historical Note**: This session doc references old deploy/ structure.
> For current structure, see: deploy/k8s/README.md
> Date: 2025-10-21 (before reorganization)
```

**Archivos**:
- `docs/sessions/2025-10-21/*.md` (8 archivos)

### RFC Documents

**Issue**: RFCs son **inmutables** (decisiones históricas)

**Solución**: NO modificar, añadir "Historical" badge en título

```markdown
# RFC-0004: Worker Setup [HISTORICAL]

> Written: 2025-XX-XX
> Status: Superseded by Kubernetes approach
> See: docs/infrastructure/INSTALL_K8S_CRIO_GPU.md
```

---

## 📊 IMPACTO POR TIPO DE DOC

| Tipo de Doc | Inconsistencias | Acción |
|-------------|-----------------|--------|
| **Getting Started** | Alta (paths legacy) | 🔴 FIX inmediato |
| **Architecture** | Media (registry namespace) | 🟡 FIX después de ADR |
| **Operations** | Alta (paths, scripts) | 🔴 FIX inmediato |
| **Sessions** | Baja (históricas) | ⚠️ Header note |
| **RFC/Decisions** | Ninguna (inmutables) | ✅ Mantener como históricos |
| **Infrastructure** | Media (CRI-O standalone) | 🟡 Deprecation notices |

---

## ✅ DOCS QUE ESTÁN CORRECTOS

**No necesitan cambios**:
- `TESTING_ARCHITECTURE.md` ✅
- `GIT_WORKFLOW.md` ✅
- `GOLDEN_PATH.md` ✅ (excepto secciones CRI-O)
- `architecture/AGENTS_AND_TOOLS_*.md` ✅ (series completa)
- `architecture/RBAC_*.md` ✅ (series completa)

---

## 🎯 RECOMENDACIÓN FINAL

### Acción Inmediata (Hoy)

1. **Ejecutar script de corrección automática** (arriba)
   - Duración: 5 minutos
   - Impacto: Corrige ~50 referencias

2. **Añadir deprecation notices** manualmente
   - GOLDEN_PATH.md (secciones CRI-O)
   - CONTAINER_RUNTIMES.md
   - PODMAN_CRIO_GUIDE.md

3. **Añadir "Historical" notes** en session docs
   - `docs/sessions/2025-10-21/*.md`

### Esta Semana

4. **Crear ADR-001-registry-namespace.md**
5. **Unificar registry namespace** (después de ADR)
6. **Investigar StoryCoach/Workspace** status

### Próxima Semana

7. **Actualizar INDEX.md**
8. **Crear guía de migración** para developers

---

## 📈 MÉTRICAS DE CALIDAD POST-FIX

### Objetivo

| Métrica | Actual | Target | Gap |
|---------|--------|--------|-----|
| Docs actualizados (< 1 mes) | 40% | 80% | 40% |
| Referencias correctas | 60% | 95% | 35% |
| Deprecation notices | 0% | 100% | 100% |
| Registry namespace único | 15% (9/65) | 100% | 85% |

### Después de Fixes

| Métrica | Esperado |
|---------|----------|
| Docs actualizados | 75% |
| Referencias correctas | 90% |
| Deprecation notices | 100% |
| Registry namespace único | 100% (después de ADR) |

---

## 💡 RECOMENDACIONES A LARGO PLAZO

### 1. Docs Review Policy

```markdown
Every PR that changes infra/deploy must:
- [ ] Update affected docs
- [ ] Check for broken links
- [ ] Verify code examples work
```

### 2. Automated Link Checking

```bash
# CI check for broken internal references
find docs/ -name "*.md" -exec \
  grep -o 'deploy/k8s/[^ ]*\.yaml' {} \; | \
  while read ref; do
    [ -f "$ref" ] || echo "BROKEN: $ref"
  done
```

### 3. Deprecation Policy

```markdown
When deprecating a feature/path:
1. Add deprecation notice with date
2. Provide migration path
3. Keep for 3 months minimum
4. Then move to archived/
```

### 4. Version Docs by Release

```
docs/
├── v1.0/  (stable)
├── v2.0/  (stable)
├── latest/  (symlink to current)
└── archived/
```

---

**Autor**: AI Assistant  
**Fecha**: 2025-11-08  
**Siguiente**: Ejecutar fixes automáticos + ADR registry namespace  

