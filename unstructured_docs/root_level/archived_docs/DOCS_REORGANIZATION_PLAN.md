# 📚 Documentation Reorganization Plan

**Current State**: 104 .md files en raíz del proyecto (CAOS)  
**Target State**: Estructura organizada jerárquica y profesional

---

## 🎯 Objetivos

1. ✅ **Claridad**: Fácil encontrar documentación relevante
2. ✅ **Jerarquía**: Normative → Reference → Historical
3. ✅ **Mantenibilidad**: Fácil actualizar y deprecar
4. ✅ **Profesionalismo**: Igual que código (DDD, clean arch)

---

## 📁 Nueva Estructura Propuesta

```
swe-ai-fleet/
├── README.md                          ← Entry point (keep)
├── LICENSE                            ← Legal (keep)
├── CODE_OF_CONDUCT.md                ← Community (keep)
├── CONTRIBUTING.md                    ← Development (keep)
├── GOVERNANCE.md                      ← Project (keep)
│
├── docs/                              ← TODA la documentación
│   │
│   ├── 00-INDEX.md                    ← Master index (NEW)
│   │
│   ├── investors/                     ← DOCUMENTACIÓN PARA INVESTORS ⭐
│   │   ├── README.md                  ← Investment overview
│   │   ├── CONTEXT_PRECISION_TECHNOLOGY.md  ← Why we're disruptive
│   │   ├── INNOVATION_VISUALIZATION.md      ← Visual innovation
│   │   ├── EXECUTIVE_SUMMARY.md             ← Business case
│   │   └── BRANDING.md                      ← Brand identity
│   │
│   ├── normative/                     ← DOCUMENTOS NORMATIVOS ⭐
│   │   ├── README.md
│   │   ├── HEXAGONAL_ARCHITECTURE_PRINCIPLES.md
│   │   ├── TESTING_ARCHITECTURE.md
│   │   ├── API_GENERATION_RULES.md
│   │   └── DOCUMENTATION_STANDARDS.md
│   │
│   ├── architecture/                  ← Arquitectura técnica
│   │   ├── README.md
│   │   ├── MICROSERVICES_ARCHITECTURE.md
│   │   ├── COMPONENT_INTERACTIONS.md
│   │   ├── CORE_VS_MICROSERVICES.md
│   │   └── API_VERSIONING.md
│   │
│   ├── development/                   ← Guías de desarrollo
│   │   ├── README.md
│   │   ├── DEVELOPMENT_GUIDE.md
│   │   ├── TESTING_STRATEGY.md
│   │   ├── GIT_WORKFLOW.md
│   │   └── MICROSERVICES_BUILD_PATTERNS.md
│   │
│   ├── deployment/                    ← Deployment & Operations
│   │   ├── README.md
│   │   ├── INSTALLATION.md
│   │   ├── DEPLOYMENT_GUIDE.md
│   │   └── KUBERNETES_SETUP.md
│   │
│   ├── sessions/                      ← Session summaries
│   │   ├── 2025-10-21/
│   │   │   ├── SESSION_EPIC_COMPLETE.md
│   │   │   ├── SUCCESS_VLLM_AGENTS.md
│   │   │   └── TEST_RESULTS.md
│   │   ├── 2025-10-20/
│   │   │   └── HEXAGONAL_REFACTOR.md
│   │   └── archive/                   ← Older sessions
│   │
│   ├── investigations/                ← Bug reports & analysis
│   │   ├── BUG_ASYNCIO_RUN.md
│   │   ├── MOCK_AGENTS_ISSUE.md
│   │   ├── COUNCIL_PERSISTENCE.md
│   │   └── DELIBERATION_USECASES.md
│   │
│   ├── evidence/                      ← Production evidence
│   │   ├── VLLM_AGENTS_WORKING.md
│   │   ├── CLUSTER_EXECUTION.md
│   │   └── NEO4J_VALKEY_COMPLETE.md
│   │
│   ├── planning/                      ← Planning docs
│   │   ├── PR_STRATEGY.md
│   │   ├── ROADMAP.md
│   │   ├── ROADMAP_DETAILED.md
│   │   └── TODO_*.md files
│   │
│   └── reference/                     ← Reference docs (existing)
│       ├── FAQ.md
│       ├── SECURITY.md
│       └── ...
│
└── archived-docs/                     ← Deprecated/Old docs
    ├── README.md (explains why archived)
    ├── old-sessions/
    ├── old-test-reports/
    └── superseded/
```

---

## 🗂️ Categorización de Archivos Actuales

### 📌 KEEP IN ROOT (6)
```
README.md              ← Main entry point
LICENSE               ← Legal requirement
CODE_OF_CONDUCT.md    ← Community standards
CONTRIBUTING.md       ← How to contribute
GOVERNANCE.md         ← Project governance
SECURITY.md           ← Security policy
```

### ⭐ NORMATIVE (Move to docs/normative/)
```
HEXAGONAL_ARCHITECTURE_PRINCIPLES.md
TESTING_ARCHITECTURE.md
API_GENERATION_RULES.md
DOCUMENTATION_STANDARDS.md
```

### 🏗️ ARCHITECTURE (Move to docs/architecture/)
```
ARCHITECTURE_CORE_VS_MICROSERVICES.md
ARCHITECTURE_FLOW_ANALYSIS.md
API_VERSIONING_IMPLEMENTATION.md
AGENTS_VS_MODELS_ARCHITECTURE.md
MICROSERVICES_BUILD_PATTERNS.md (from docs/)
SIMPLIFIED_CONTAINER_ARCHITECTURE.md
```

### 📅 SESSIONS (Move to docs/sessions/2025-10-XX/)
```
SESSION_20251021_EPIC_COMPLETE.md                    → docs/sessions/2025-10-21/
SESSION_FINAL_20251021_COMPLETE_SUCCESS.md          → docs/sessions/2025-10-21/
SESSION_20251021_vLLM_AGENTS_COMPLETE.md            → docs/sessions/2025-10-21/
CLEAN_ARCHITECTURE_REFACTOR_20251020.md             → docs/sessions/2025-10-20/
SESSION_COMPLETE.md                                  → docs/sessions/archive/
SESSION_SUMMARY.md                                   → docs/sessions/archive/
SESSION_PERSISTENT_STREAMS.md                        → docs/sessions/archive/
SESSION_2025-10-16_COMPLETE.md (if exists)          → docs/sessions/2025-10-16/
```

### 🐛 INVESTIGATIONS (Move to docs/investigations/)
```
BUG_ASYNCIO_RUN_IN_VLLM_AGENT.md
MOCK_AGENTS_ISSUE.md
COUNCIL_PERSISTENCE_PROBLEM.md
DELIBERATION_USECASES_ANALYSIS.md
ORCHESTRATOR_HEXAGONAL_ANALYSIS.md
ARCHIVED_TESTS_INVESTIGATION.md
```

### ✅ EVIDENCE (Move to docs/evidence/)
```
SUCCESS_VLLM_AGENTS_WORKING_20251021.md
ALL_AGENTS_REAL_VLLM_EVIDENCE.md
CLUSTER_EXECUTION_EVIDENCE.md
NEO4J_VALKEY_COMPLETE_EVIDENCE.md
COMPLETE_SYSTEM_DEMONSTRATION.md
FULL_E2E_DEMONSTRATION_COMPLETE.md
DEPLOYMENT_COMPLETE.md
VERIFICATION_RESULTS.md
```

### 📋 PLANNING (Move to docs/planning/)
```
PR_STRATEGY.md
PARA_MAÑANA_20251021.md
ROADMAP.md
ROADMAP_DETAILED.md
TODO_VLLM_AGENT_REFACTOR.md
RAY_CONTAINERS_TODO.md
ORCHESTRATOR_MOCKAGENT_TODO.md
REFACTOR_DIRECTORY_STRUCTURE_PROPOSAL.md
REORGANIZATION_PLAN.md
```

### 🧪 TEST REPORTS (Move to docs/testing/reports/)
```
TEST_RESULTS_20251021.md
FINAL_TEST_REPORT.md
FINAL_TEST_SUMMARY.md
TEST_AUDIT.md
TEST_REORGANIZATION_SUMMARY.md
TESTS_SUMMARY.md
E2E_QUALITY_ANALYSIS.md
INTEGRATION_TESTS_AUDIT.md
UNIT_TESTS_TO_FIX.md
```

### 📦 SUMMARIES/COMPLETIONS (Move to docs/summaries/)
```
AGENT_TOOLS_COMPLETE.md
TOOLS_IMPLEMENTATION_SUMMARY.md
INTEGRATION_FINAL_SUMMARY.md
MONITORING_DASHBOARD_MVP.md
MONITORING_FRONTEND_SUMMARY.md
PERSISTENT_STREAMS_IMPLEMENTATION.md
```

### 🗑️ ARCHIVE (Move to archived-docs/)
```
COMMIT_MESSAGE_CONTEXT.txt
COMMIT_SUMMARY.md
COMMUNICATION_AUDIT.md
MONITORING_MOCK_DATA_*.md
E2E_REAL_AGENTS_PLAN.md (superseded by VERIFIED)
E2E_REAL_AGENTS_STATUS.md (superseded)
NO_STUBS_AUDIT.md
ORCHESTRATOR_E2E_RESULTS.md
ORCHESTRATOR_MOCKAGENT_TODO.md (obsolete)
PR_MESSAGE.md
PR_ORCHESTRATOR_E2E.md
PR_ORCHESTRATOR_MICROSERVICE.md
PR_RAY_VLLM_INTEGRATION.md
PR_TEST_ORGANIZATION.md
```

---

## 🎯 Execution Plan

### Phase 1: Create Structure (5 min)

```bash
# Create new directories
mkdir -p docs/normative
mkdir -p docs/sessions/{2025-10-21,2025-10-20,2025-10-16,2025-10-14,2025-10-11,archive}
mkdir -p docs/investigations
mkdir -p docs/evidence
mkdir -p docs/planning
mkdir -p docs/testing/reports
mkdir -p docs/summaries
mkdir -p archived-docs/{old-sessions,old-test-reports,superseded}
```

### Phase 2: Move Normative Docs (CRÍTICO - 2 min)

```bash
# These are the MOST important
mv HEXAGONAL_ARCHITECTURE_PRINCIPLES.md docs/normative/
mv TESTING_ARCHITECTURE.md docs/normative/
mv API_GENERATION_RULES.md docs/normative/
mv DOCUMENTATION_STANDARDS.md docs/normative/

# Create normative README
cat > docs/normative/README.md << 'EOF'
# Normative Documents

These documents are **NORMATIVE** and **MUST BE FOLLOWED**.

1. HEXAGONAL_ARCHITECTURE_PRINCIPLES.md - Code architecture
2. TESTING_ARCHITECTURE.md - Testing strategy
3. API_GENERATION_RULES.md - API development
4. DOCUMENTATION_STANDARDS.md - Documentation quality

**Status**: Binding for all development
EOF
```

### Phase 3: Move Sessions (5 min)

```bash
# Current session
mv SESSION_20251021_EPIC_COMPLETE.md docs/sessions/2025-10-21/
mv SESSION_FINAL_20251021_COMPLETE_SUCCESS.md docs/sessions/2025-10-21/
mv SESSION_20251021_vLLM_AGENTS_COMPLETE.md docs/sessions/2025-10-21/
mv SUCCESS_VLLM_AGENTS_WORKING_20251021.md docs/sessions/2025-10-21/
mv TEST_RESULTS_20251021.md docs/sessions/2025-10-21/
mv PARA_MAÑANA_20251021.md docs/sessions/2025-10-21/

# Previous sessions
mv CLEAN_ARCHITECTURE_REFACTOR_20251020.md docs/sessions/2025-10-20/
# ... (continue for other dates)
```

### Phase 4: Move Investigations (3 min)

```bash
mv BUG_ASYNCIO_RUN_IN_VLLM_AGENT.md docs/investigations/
mv MOCK_AGENTS_ISSUE.md docs/investigations/
mv COUNCIL_PERSISTENCE_PROBLEM.md docs/investigations/
mv DELIBERATION_USECASES_ANALYSIS.md docs/investigations/
mv ORCHESTRATOR_HEXAGONAL_ANALYSIS.md docs/investigations/
mv ARCHIVED_TESTS_INVESTIGATION.md docs/investigations/
```

### Phase 5: Move Evidence (3 min)

```bash
mv ALL_AGENTS_REAL_VLLM_EVIDENCE.md docs/evidence/
mv CLUSTER_EXECUTION_EVIDENCE.md docs/evidence/
mv NEO4J_VALKEY_COMPLETE_EVIDENCE.md docs/evidence/
mv COMPLETE_SYSTEM_DEMONSTRATION.md docs/evidence/
mv FULL_E2E_DEMONSTRATION_COMPLETE.md docs/evidence/
mv DEPLOYMENT_COMPLETE.md docs/evidence/
mv VERIFICATION_RESULTS.md docs/evidence/
```

### Phase 6: Move Planning (2 min)

```bash
mv PR_STRATEGY.md docs/planning/
mv TODO_*.md docs/planning/
mv *_TODO.md docs/planning/
mv REFACTOR_DIRECTORY_STRUCTURE_PROPOSAL.md docs/planning/
mv REORGANIZATION_PLAN.md docs/planning/
```

### Phase 7: Move Test Reports (3 min)

```bash
mv FINAL_TEST_*.md docs/testing/reports/
mv TEST_*.md docs/testing/reports/
mv INTEGRATION_TESTS_AUDIT.md docs/testing/reports/
mv E2E_QUALITY_ANALYSIS.md docs/testing/reports/
mv UNIT_TESTS_TO_FIX.md docs/testing/reports/
```

### Phase 8: Archive Obsolete (5 min)

```bash
mv COMMIT_*.md archived-docs/superseded/
mv PR_*.md archived-docs/superseded/
mv COMMUNICATION_AUDIT.md archived-docs/superseded/
mv MONITORING_MOCK_DATA_*.md archived-docs/superseded/
mv E2E_REAL_AGENTS_PLAN.md archived-docs/superseded/  # Superseded by VERIFIED
mv NO_STUBS_AUDIT.md archived-docs/superseded/
mv ORCHESTRATOR_E2E_RESULTS.md archived-docs/old-test-reports/
mv ORCHESTRATOR_MOCKAGENT_TODO.md archived-docs/superseded/
```

---

## 📋 Master Index (docs/00-INDEX.md)

```markdown
# 📚 SWE AI Fleet Documentation Index

**Single Source of Truth** para toda la documentación del proyecto.

---

## ⭐ START HERE

- [README](../README.md) - Project overview
- [Getting Started](getting-started/README.md) - Quick start guide
- [Installation](deployment/INSTALLATION.md) - Setup instructions

---

## 📖 NORMATIVE DOCUMENTS (MUST FOLLOW)

These documents are **binding** for all development:

1. [Hexagonal Architecture Principles](normative/HEXAGONAL_ARCHITECTURE_PRINCIPLES.md) ⭐
2. [Testing Architecture](normative/TESTING_ARCHITECTURE.md) ⭐
3. [API Generation Rules](normative/API_GENERATION_RULES.md)
4. [Documentation Standards](normative/DOCUMENTATION_STANDARDS.md)

**Status**: All code must comply with these principles.

---

## 🏗️ ARCHITECTURE

### System Design
- [Microservices Architecture](architecture/MICROSERVICES_ARCHITECTURE.md)
- [Component Interactions](architecture/COMPONENT_INTERACTIONS.md)
- [Core vs Microservices](architecture/CORE_VS_MICROSERVICES.md)

### Technical Details
- [API Versioning](architecture/API_VERSIONING.md)
- [Build Patterns](development/MICROSERVICES_BUILD_PATTERNS.md)
- [Infrastructure](infrastructure/)

---

## 🛠️ DEVELOPMENT

- [Development Guide](development/DEVELOPMENT_GUIDE.md)
- [Testing Strategy](development/TESTING_STRATEGY.md)
- [Git Workflow](development/GIT_WORKFLOW.md)
- [Contributing](../CONTRIBUTING.md)

---

## 🚀 DEPLOYMENT

- [Installation Guide](deployment/INSTALLATION.md)
- [Kubernetes Setup](infrastructure/kubernetes.md)
- [GPU Configuration](infrastructure/GPU_TIME_SLICING.md)

---

## 📊 SESSIONS & EVIDENCE

### Recent Sessions
- [2025-10-21: vLLM Agents + Observability](sessions/2025-10-21/)
- [2025-10-20: Hexagonal Refactor](sessions/2025-10-20/)
- [Older Sessions](sessions/archive/)

### Production Evidence
- [vLLM Agents Working](evidence/SUCCESS_VLLM_AGENTS.md)
- [Cluster Execution](evidence/CLUSTER_EXECUTION.md)
- [Complete System Demo](evidence/COMPLETE_SYSTEM.md)

---

## 🔍 INVESTIGATIONS & TROUBLESHOOTING

- [Bug Reports](investigations/)
- [Test Reports](testing/reports/)
- [Known Issues](investigations/)

---

## 📋 PLANNING

- [PR Strategy](planning/PR_STRATEGY.md)
- [Roadmap](planning/ROADMAP.md)
- [TODOs](planning/)

---

**Last Updated**: 21 October 2025  
**Maintained By**: Tirso (Lead Architect)
```

---

## 🚀 Implementation Script

```bash
#!/bin/bash
# scripts/reorganize-docs.sh

set -e

echo "📚 Reorganizing documentation..."

# Phase 1: Create structure
echo "Creating directories..."
mkdir -p docs/{normative,sessions/{2025-10-21,2025-10-20,2025-10-16,2025-10-14,2025-10-11,archive},investigations,evidence,planning,testing/reports,summaries}
mkdir -p archived-docs/{old-sessions,old-test-reports,superseded}

# Phase 2: Move Normative (CRITICAL)
echo "Moving normative docs..."
mv HEXAGONAL_ARCHITECTURE_PRINCIPLES.md docs/normative/ 2>/dev/null || true
mv TESTING_ARCHITECTURE.md docs/normative/ 2>/dev/null || true
mv API_GENERATION_RULES.md docs/normative/ 2>/dev/null || true
mv DOCUMENTATION_STANDARDS.md docs/normative/ 2>/dev/null || true

# Phase 3: Move Sessions
echo "Moving session docs..."
mv SESSION_20251021_*.md docs/sessions/2025-10-21/ 2>/dev/null || true
mv SUCCESS_VLLM_AGENTS_WORKING_20251021.md docs/sessions/2025-10-21/ 2>/dev/null || true
mv TEST_RESULTS_20251021.md docs/sessions/2025-10-21/ 2>/dev/null || true
mv PARA_MAÑANA_20251021.md docs/sessions/2025-10-21/ 2>/dev/null || true

mv CLEAN_ARCHITECTURE_REFACTOR_20251020.md docs/sessions/2025-10-20/ 2>/dev/null || true

mv DOCUMENTATION_AUDIT_2025-10-14.md docs/sessions/2025-10-14/ 2>/dev/null || true

mv SESSION_COMPLETE.md docs/sessions/archive/ 2>/dev/null || true
mv SESSION_SUMMARY.md docs/sessions/archive/ 2>/dev/null || true
mv SESSION_PERSISTENT_STREAMS.md docs/sessions/archive/ 2>/dev/null || true

# Phase 4: Move Investigations
echo "Moving investigation docs..."
mv BUG_ASYNCIO_RUN_IN_VLLM_AGENT.md docs/investigations/ 2>/dev/null || true
mv MOCK_AGENTS_ISSUE.md docs/investigations/ 2>/dev/null || true
mv COUNCIL_PERSISTENCE_PROBLEM.md docs/investigations/ 2>/dev/null || true
mv DELIBERATION_USECASES_ANALYSIS.md docs/investigations/ 2>/dev/null || true
mv ORCHESTRATOR_HEXAGONAL_ANALYSIS.md docs/investigations/ 2>/dev/null || true
mv ARCHIVED_TESTS_INVESTIGATION.md docs/investigations/ 2>/dev/null || true

# Phase 5: Move Evidence
echo "Moving evidence docs..."
mv ALL_AGENTS_REAL_VLLM_EVIDENCE.md docs/evidence/ 2>/dev/null || true
mv CLUSTER_EXECUTION_EVIDENCE.md docs/evidence/ 2>/dev/null || true
mv NEO4J_VALKEY_COMPLETE_EVIDENCE.md docs/evidence/ 2>/dev/null || true
mv COMPLETE_SYSTEM_DEMONSTRATION.md docs/evidence/ 2>/dev/null || true
mv FULL_E2E_DEMONSTRATION_COMPLETE.md docs/evidence/ 2>/dev/null || true
mv DEPLOYMENT_COMPLETE.md docs/evidence/ 2>/dev/null || true
mv VERIFICATION_RESULTS.md docs/evidence/ 2>/dev/null || true

# Phase 6: Move Planning
echo "Moving planning docs..."
mv PR_STRATEGY.md docs/planning/ 2>/dev/null || true
mv TODO_*.md docs/planning/ 2>/dev/null || true
mv *_TODO.md docs/planning/ 2>/dev/null || true
mv REFACTOR_DIRECTORY_STRUCTURE_PROPOSAL.md docs/planning/ 2>/dev/null || true
mv REORGANIZATION_PLAN.md docs/planning/ 2>/dev/null || true

# Phase 7: Move Test Reports
echo "Moving test reports..."
mv FINAL_TEST_*.md docs/testing/reports/ 2>/dev/null || true
mv TEST_*.md docs/testing/reports/ 2>/dev/null || true
mv INTEGRATION_TESTS_AUDIT.md docs/testing/reports/ 2>/dev/null || true
mv E2E_QUALITY_ANALYSIS.md docs/testing/reports/ 2>/dev/null || true
mv UNIT_TESTS_TO_FIX.md docs/testing/reports/ 2>/dev/null || true
mv E2E_TESTING_SESSION_SUMMARY.md docs/testing/reports/ 2>/dev/null || true

# Phase 8: Move Architecture
echo "Moving architecture docs..."
mv ARCHITECTURE_*.md docs/architecture/ 2>/dev/null || true
mv API_VERSIONING_IMPLEMENTATION.md docs/architecture/ 2>/dev/null || true
mv AGENTS_VS_MODELS_ARCHITECTURE.md docs/architecture/ 2>/dev/null || true
mv SIMPLIFIED_CONTAINER_ARCHITECTURE.md docs/architecture/ 2>/dev/null || true

# Phase 9: Move Summaries
echo "Moving summary docs..."
mv AGENT_TOOLS_COMPLETE.md docs/summaries/ 2>/dev/null || true
mv TOOLS_IMPLEMENTATION_SUMMARY.md docs/summaries/ 2>/dev/null || true
mv INTEGRATION_FINAL_SUMMARY.md docs/summaries/ 2>/dev/null || true
mv MONITORING_*.md docs/summaries/ 2>/dev/null || true
mv PERSISTENT_STREAMS_IMPLEMENTATION.md docs/summaries/ 2>/dev/null || true

# Phase 10: Archive Obsolete
echo "Archiving obsolete docs..."
mv COMMIT_*.md archived-docs/superseded/ 2>/dev/null || true
mv PR_*.md archived-docs/superseded/ 2>/dev/null || true
mv COMMUNICATION_AUDIT.md archived-docs/superseded/ 2>/dev/null || true
mv E2E_REAL_AGENTS_PLAN.md archived-docs/superseded/ 2>/dev/null || true
mv E2E_REAL_AGENTS_STATUS.md archived-docs/superseded/ 2>/dev/null || true
mv NO_STUBS_AUDIT.md archived-docs/superseded/ 2>/dev/null || true
mv ORCHESTRATOR_E2E_RESULTS.md archived-docs/old-test-reports/ 2>/dev/null || true

# Phase 11: Update References
echo "Updating references..."
# Update README.md to point to docs/00-INDEX.md
# Update all relative links in moved files

echo "✅ Documentation reorganized!"
echo "📊 Summary:"
find docs -type f -name "*.md" | wc -l
echo "   docs files organized"
find archived-docs -type f -name "*.md" | wc -l  
echo "   archived docs"
ls -1 *.md 2>/dev/null | wc -l
echo "   remaining in root (should be ~6)"
```

---

## 🎯 Benefits

### Before
```
swe-ai-fleet/
├── README.md
├── 104 .md files (CHAOS)
└── docs/
```

### After
```
swe-ai-fleet/
├── README.md                    ← Clear entry point
├── 5 community files            ← Standard OSS files
├── docs/
│   ├── 00-INDEX.md             ← Master navigation
│   ├── normative/              ← ⭐ Binding docs
│   ├── architecture/           ← Technical design
│   ├── development/            ← How-to guides
│   ├── sessions/               ← Historical record
│   ├── investigations/         ← Bug analysis
│   ├── evidence/               ← Proof of functionality
│   └── planning/               ← Roadmaps & TODOs
└── archived-docs/              ← Old/deprecated
```

**Clarity**: 100% improvement ✅

---

## 🎓 Principles Applied

### Documentation as Code
- Hierarchical structure (like clean arch layers)
- Single source of truth
- Clear ownership (normative vs reference)
- Version control (sessions by date)

### Domain-Driven Documentation
- Bounded contexts (normative, architecture, development)
- Ubiquitous language (consistent naming)
- Aggregates (index files for navigation)

### Clean Architecture for Docs
- Normative (domain rules)
- Reference (use cases)
- Historical (implementation evidence)
- Archived (deprecated)

---

## 🚀 Execution

```bash
# Create and run script
chmod +x scripts/reorganize-docs.sh
./scripts/reorganize-docs.sh

# Verify
tree docs -L 2
ls -1 *.md  # Should show only 6 files

# Commit
git add -A
git commit -m "docs: reorganize 104 .md files into hierarchical structure

Reorganization:
- 104 .md files in root → Organized hierarchy
- docs/normative/ - Binding architectural docs
- docs/sessions/ - Session summaries by date
- docs/investigations/ - Bug analysis
- docs/evidence/ - Production verification
- docs/planning/ - Roadmaps & TODOs
- archived-docs/ - Deprecated/obsolete

Benefits:
✅ Clarity (easy navigation)
✅ Hierarchy (normative → reference → historical)
✅ Maintainability (clear ownership)
✅ Professionalism (OSS standards)

Master Index: docs/00-INDEX.md"
```

---

## ✅ Verification Checklist

After reorganization:

- [ ] Root has only 6 .md files (README, LICENSE, CODE_OF_CONDUCT, CONTRIBUTING, GOVERNANCE, SECURITY)
- [ ] docs/normative/ has 4 files (Hexagonal, Testing, API, Documentation)
- [ ] docs/00-INDEX.md exists and has complete navigation
- [ ] All internal links updated (relative paths corrected)
- [ ] README.md points to docs/00-INDEX.md
- [ ] CI still passes (no broken paths)
- [ ] Git tracks all moves (git mv preserves history)

---

**Estimated Time**: 30 minutes  
**Impact**: 🟢 LOW (docs only, no code changes)  
**Risk**: 🟢 LOW (can revert easily)  
**Value**: 🔥 HIGH (professional appearance)

**Ready to execute?**

