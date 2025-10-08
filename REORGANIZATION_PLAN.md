# Reorganization Plan - Infrastructure & Documentation

## 🎯 Objetivo

Preparar el repositorio para que sea fácilmente replicable por la comunidad open source:
- Eliminar archivos obsoletos y duplicados
- Organizar claramente YAMLs, scripts y documentación
- Punto de entrada claro para nuevos usuarios

---

## 📊 Análisis Actual

### ✅ Archivos ACTUALES (en producción)

**deploy/k8s-integration/**
- 00-namespace.yaml ✅
- 01-nats.yaml ✅
- 01-nats-ingress.yaml ✅  
- 02-services.yaml ✅
- 03-raycluster-agents.yaml ✅ (opcional, si quieres cluster separado)
- 04-ingress.yaml ❌ (no usado, reemplazado por 07-ui-ingress.yaml)
- 05-config.yaml ✅
- 06-registry.yaml ✅ (registry local)
- 07-ui-ingress.yaml ✅
- 08-ray-dashboard-ingress.yaml ✅ (nuevo)
- internal-services.yaml ✅
- internal-dns-config.yaml ❓ (verificar si duplica internal-services.yaml)

**scripts/** (actuales en uso)
- deploy-step-*.sh ✅ (1-7, despliegue paso a paso)
- deploy-all-steps.sh ✅
- verify-cluster-health.sh ✅
- deploy-local-registry.sh ✅
- push-to-local-registry.sh ✅
- create-registry-dns.sh ✅
- expose-ui.sh ✅
- expose-ray-dashboard.sh ✅

**config/**
- agile.fsm.yaml ✅
- rigor.yaml ✅
- prompt_scopes.yaml ✅

### ❌ Archivos OBSOLETOS (borrar o archivar)

**deploy/k8s/** (arquitectura antigua)
- deployment-demo-frontend.yaml ❌
- deployment-neo4j.yaml ❌
- deployment-redis.yaml ❌
- ingress-swe-fleet.yaml ❌
- namespace-swe.yaml ❌
- secret-neo4j-auth.yaml ❌
- secret-redis-auth.yaml ❌
- service-demo-frontend.yaml ❌
- service-neo4j.yaml ❌
- service-redis.yaml ❌

**deploy/k8s-new/** (borradores antiguos, duplicados de k8s-integration)
- TODO: Todos los archivos ❌

**deploy/helm/** (no usado actualmente)
- ❓ Mantener para futuros usuarios que prefieran Helm

**scripts/** (obsoletos)
- setup-ecr-madrid.sh ❌ (usamos registry local)
- update-manifests-for-ecr.sh ❌
- check_crio_nvidia_env.sh ❓ (¿útil para debug?)
- vllm_crio.sh ❓
- web_crio.sh ❓
- create-nats-dns.sh ❌ (duplicado, NATS usa internal DNS)
- setup-registry-dns.sh ❌ (duplicado de create-registry-dns.sh)

**docs/** (obsoletos o duplicados)
- CRIO_DIAGNOSTICS.md ❓ (útil para troubleshooting)
- CRIO_MANIFESTS_REVIEW.md ❌ (review específico, no doc general)
- DEPLOYMENT.md ❓ (verificar si duplica INSTALLATION.md)
- K8S_DEMO_RUNBOOK.md ❌ (demo antiguo)
- INGRESS_INSTALL.md ❌ (ya instalado, no necesario)
- INSTALL_CRIO.md ❓ (útil para setup inicial)
- INSTALL_K8S_CRIO_GPU.md ❓ (útil para setup inicial)
- DOCUMENTATION_SUMMARY.md ❌ (meta-doc, no necesario)

**Root-level docs** (duplicados)
- BUILD_SUMMARY.md ❌ (temporal)
- CLUSTER_INTEGRATION.md ❌ (temporal)
- CONTAINER_RUNTIMES.md ❓ (útil para entender CRI-O)
- CRIO_FIXES_SUMMARY.md ❌ (temporal)
- DEPLOY_NOW.md ❌ (temporal)
- DEPLOYMENT_WITH_LOCAL_IMAGES.md ❌ (temporal)
- DOCKER_DEPLOYMENT.md ❌ (no usamos Docker)
- MICROSERVICES_ARCHITECTURE.md ❓ (útil)
- PODMAN_CRIO_GUIDE.md ❓ (útil)
- PUSH_TO_REGISTRY.md ❌ (duplica scripts)
- QUICKSTART_MICROSERVICES.md ❓ (útil)
- REGISTRY_SETUP.md ❌ (duplica scripts)
- ROLLOUT_PLAN.md ❌ (temporal)
- TOOL_GATEWAY_IMPLEMENTATION.md ❌ (no implementado)

---

## 🔄 Plan de Reorganización

### 1. YAMLs de Kubernetes

```
deploy/
├── k8s/                          ← RENOMBRAR: k8s-production/
│   ├── 00-namespace.yaml
│   ├── 01-nats.yaml
│   ├── 02-nats-internal-dns.yaml ← FUSIONAR 01-nats-ingress + internal-services
│   ├── 03-configmaps.yaml        ← RENOMBRAR 05-config.yaml
│   ├── 04-services.yaml          ← RENOMBRAR 02-services.yaml
│   ├── 05-ui-ingress.yaml        ← RENOMBRAR 07-ui-ingress.yaml
│   ├── 06-ray-dashboard-ingress.yaml ← RENOMBRAR 08-ray-dashboard-ingress.yaml
│   ├── 07-registry.yaml          ← RENOMBRAR 06-registry.yaml
│   └── README.md                 ← NUEVO: Guía de despliegue
├── k8s-optional/                 ← NUEVO: Componentes opcionales
│   ├── raycluster-agents.yaml    ← MOVER 03-raycluster-agents.yaml
│   └── README.md
├── helm/                         ← MANTENER (para usuarios Helm)
│   └── (sin cambios)
└── examples/                     ← NUEVO: Ejemplos y arquitecturas antiguas
    └── old-architecture/         ← ARCHIVAR deploy/k8s/ aquí
```

### 2. Scripts

```
scripts/
├── infra/                        ← NUEVO: Scripts de infraestructura
│   ├── 00-verify-prerequisites.sh   ← NUEVO
│   ├── 01-deploy-namespace.sh       ← RENOMBRAR deploy-step-1-namespace.sh
│   ├── 02-deploy-nats.sh            ← RENOMBRAR deploy-step-2-nats.sh
│   ├── 03-deploy-config.sh          ← RENOMBRAR deploy-step-3-config.sh
│   ├── 04-deploy-services.sh        ← FUSIONAR steps 4-6 (planning, storycoach, workspace)
│   ├── 05-deploy-ui.sh              ← RENOMBRAR deploy-step-7-ui.sh
│   ├── 06-expose-ui.sh              ← MOVER expose-ui.sh
│   ├── 07-expose-ray-dashboard.sh   ← MOVER expose-ray-dashboard.sh
│   ├── deploy-all.sh                ← RENOMBRAR deploy-all-steps.sh
│   ├── verify-health.sh             ← RENOMBRAR verify-cluster-health.sh
│   └── README.md                    ← NUEVO: Guía de uso
├── registry/                     ← NUEVO: Scripts del registry
│   ├── deploy-local-registry.sh
│   ├── push-to-registry.sh
│   ├── create-registry-dns.sh
│   └── README.md
├── dev/                          ← Scripts de desarrollo
│   ├── dev.sh
│   ├── e2e.sh
│   └── redis_smoke.sh
└── diagnostics/                  ← Scripts de troubleshooting
    ├── check_crio_nvidia_env.sh
    └── k8s_calico_diag.sh
```

### 3. Documentación

```
docs/
├── getting-started/              ← NUEVO: Para nuevos usuarios
│   ├── README.md                 ← Punto de entrada principal
│   ├── prerequisites.md          ← Hardware, software requerido
│   ├── installation.md           ← Instalación paso a paso
│   └── quickstart.md             ← Deploy en 5 minutos
├── architecture/                 ← NUEVO: Diseño del sistema
│   ├── README.md
│   ├── microservices.md          ← MOVER/FUSIONAR MICROSERVICES_ARCHITECTURE + AGILE_TEAM
│   ├── api-specs.md              ← Explicar specs/
│   ├── fsm-workflow.md           ← Explicar FSM y rigor
│   └── context-management.md     ← MOVER CONTEXT_MANAGEMENT
├── infrastructure/               ← NUEVO: Setup de infra
│   ├── kubernetes.md             ← FUSIONAR K8S_* docs
│   ├── gpu-setup.md              ← GPU_TIME_SLICING + RAYCLUSTER_INTEGRATION
│   ├── ray-cluster.md            ← RAY_STANDALONE
│   ├── container-runtime.md      ← CONTAINER_RUNTIMES + PODMAN_CRIO_GUIDE
│   └── registry.md               ← Uso del registry local
├── development/                  ← NUEVO: Para contributors
│   ├── contributing.md           ← MOVER CONTRIBUTING
│   ├── development-guide.md      ← MOVER DEVELOPMENT_GUIDE
│   ├── git-workflow.md           ← MOVER GIT_WORKFLOW
│   └── testing.md                ← Cómo ejecutar tests
├── operations/                   ← NUEVO: Deployment y troubleshooting
│   ├── deployment.md             ← Guía de deployment completa
│   ├── monitoring.md             ← Ray dashboard, métricas
│   └── troubleshooting.md        ← FUSIONAR K8S_TROUBLESHOOTING + TROUBLESHOOTING_CRIO
├── reference/                    ← NUEVO: Referencia técnica
│   ├── glossary.md               ← MOVER GLOSSARY
│   ├── faq.md                    ← MOVER FAQ
│   ├── rfcs/                     ← MOVER RFCs aquí
│   └── adrs/                     ← MOVER ADRs aquí
├── vision/                       ← NUEVO: Visión del proyecto
│   ├── vision.md                 ← MOVER VISION
│   ├── roadmap.md                ← MOVER ROADMAP
│   ├── use-cases.md              ← MOVER USE_CASES
│   └── investors.md              ← MOVER INVESTORS
└── archive/                      ← NUEVO: Docs obsoletos
    └── (mover aquí docs antiguos)
```

### 4. Root Documentation

```
/
├── README.md                     ← ACTUALIZAR: Quick start + link a docs/
├── CONTRIBUTING.md               ← Link a docs/development/
├── CODE_OF_CONDUCT.md            ← MANTENER
├── LICENSE                       ← MANTENER
├── SECURITY.md                   ← MANTENER
├── GOVERNANCE.md                 ← MANTENER
├── .github/                      ← NUEVO: Templates de issues/PRs
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
└── (borrar resto de *.md del root)
```

---

## 📝 Nuevos Documentos a Crear

### docs/getting-started/README.md

```markdown
# Getting Started with SWE AI Fleet

Welcome! This guide will help you deploy SWE AI Fleet in your Kubernetes cluster.

## 🚀 Quick Start (5 minutes)

Prerequisites:
- Kubernetes cluster with GPU support
- kubectl configured
- 512GB RAM, 4x RTX 3090 (or similar)

Deploy:
\`\`\`bash
./scripts/infra/deploy-all.sh
\`\`\`

Access:
- UI: https://swe-fleet.yourdomain.com
- Ray Dashboard: https://ray.yourdomain.com

## 📚 Next Steps

- [Full Installation Guide](installation.md)
- [Architecture Overview](../architecture/README.md)
- [Troubleshooting](../operations/troubleshooting.md)
```

### scripts/infra/README.md

```markdown
# Infrastructure Scripts

Deploy SWE AI Fleet to Kubernetes step by step.

## Prerequisites

Run this first:
\`\`\`bash
./00-verify-prerequisites.sh
\`\`\`

## Deployment

### Option 1: All at Once (Recommended)

\`\`\`bash
./deploy-all.sh
\`\`\`

### Option 2: Step by Step

\`\`\`bash
./01-deploy-namespace.sh
./02-deploy-nats.sh
./03-deploy-config.sh
./04-deploy-services.sh
./05-deploy-ui.sh
./06-expose-ui.sh       # Optional: expose UI publicly
\`\`\`

## Verification

\`\`\`bash
./verify-health.sh
\`\`\`

## Rollback

\`\`\`bash
kubectl delete namespace swe-ai-fleet
\`\`\`
```

---

## ✅ Action Items

1. **Crear estructura nueva**
2. **Mover archivos a nuevas ubicaciones**
3. **Archivar obsoletos** en deploy/examples/old-architecture/ y docs/archive/
4. **Actualizar referencias** en archivos movidos
5. **Crear nuevos READMEs** como puntos de entrada
6. **Actualizar README.md principal**
7. **Commit con mensaje descriptivo**

---

## 🎯 Resultado Final

Un repositorio organizado donde:
- **Nuevos usuarios** encuentran `docs/getting-started/README.md` fácilmente
- **Scripts de infra** están en `scripts/infra/` con README claro
- **YAMLs de producción** están en `deploy/k8s/` numerados secuencialmente
- **Documentación** está categorizada (getting-started, architecture, infrastructure, development, operations)
- **No hay duplicados** ni archivos obsoletos confundiendo a la gente
