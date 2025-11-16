# 📚 Documentation Reorganization Strategy — FINAL

**Date**: 2025-11-16  
**Status**: 🎯 READY FOR EXECUTION  
**Scope**: Move 12,000+ lines of documentation into organized structure

---

## 🎯 Objective

Transform documentation from **scattered across 50+ files** into:
1. **`unstructured_docs/`** - Archive of all existing `.md` files (grouped by source location)
2. **Core documentation** at project level (general + architecture)
3. **Microservices documentation** (each service has rich README.md)
4. **Core bounded contexts documentation**

---

## 📊 Current State Analysis

### Existing .md Files by Location

```
Root level (30+ files):
├── ARCHITECTURE_EVOLUTION.md
├── AUDIT_AGENTS_AND_TOOLS.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── INVESTMENT_THESIS_2025.md
├── KNOWLEDGE_GRAPH_ARCHITECTURE.md
├── MERMAID_*.md (3 files)
├── VALIDATION_TESTS_PLAN_2025.md
├── GENESIS_DEMO_GUIDE.md
└── ... (20+ more)

docs/ subdirectory (20+ files):
├── docs/README.md
├── docs/architecture/
├── docs/microservices/
├── docs/operations/
└── ... (various topics)

services/ subdirectory (10+ files):
├── services/planning/README.md
├── services/task-derivation/README.md
├── services/orchestrator/README.md
├── services/context/README.md
├── services/workflow/README.md
├── services/ray_executor/README.md
└── ... (subdirectories)

tests/ subdirectory (5+ files):
├── tests/e2e/README.md
├── tests/PERSISTENCE_TESTS_SUMMARY.md
└── ... (integration, unit)

deploy/ subdirectory (10+ files):
├── deploy/k8s/README.md
├── deploy/AUDIT_2025-11-08.md
└── ... (infrastructure docs)

scripts/ subdirectory (5+ files):
├── scripts/README.md
├── scripts/infra/README.md
└── ... (tooling docs)

jobs/ subdirectory (2+ files):
├── jobs/e2e-tests/README.md
└── ... (job definitions)
```

---

## 🗂️ New Target Structure

```
PROJECT_ROOT/
│
├── README.md (main entry point - KEEP AT ROOT)
├── ARCHITECTURE.md (unified architecture - NEW at root)
├── CONTRIBUTING.md (project contribution rules - KEEP)
├── ROADMAP.md (project vision - KEEP if exists)
│
├── unstructured_docs/
│   ├── README.md (navigation guide)
│   ├── root_level/ (30+ files from root)
│   │   ├── ARCHIVE_2025-11-16/
│   │   │   ├── AUDIT_AGENTS_AND_TOOLS.md
│   │   │   ├── ARCHITECTURE_EVOLUTION.md
│   │   │   ├── CODE_OF_CONDUCT.md
│   │   │   ├── INVESTMENT_THESIS_2025.md
│   │   │   ├── KNOWLEDGE_GRAPH_ARCHITECTURE.md
│   │   │   ├── MERMAID_STYLE_GUIDE.md
│   │   │   ├── MERMAID_AUDIT.md
│   │   │   ├── MERMAID_TRANSFORMATION_STRATEGY.md
│   │   │   ├── VALIDATION_TESTS_PLAN_2025.md
│   │   │   ├── GENESIS_DEMO_GUIDE.md
│   │   │   └── ... (20+ more)
│   │
│   ├── docs_subdirectory/
│   │   ├── DOCS_CONSOLIDATION_PLAN_2025-11-15.md
│   │   ├── DOCS_QUICK_DECISION_GUIDE.md
│   │   ├── DOCS_STATUS_DASHBOARD_2025-11-15.md
│   │   ├── DOCUMENTATION_STRATEGY_EXECUTIVE_SUMMARY_2025-11-15.md
│   │   ├── README_DOCS_ANALYSIS.md
│   │   └── ... (docs consolidation files)
│   │
│   ├── deployment_infrastructure/
│   │   ├── AUDIT_2025-11-08.md
│   │   ├── CLUSTER_RESTORATION_2025-11-08.md
│   │   ├── CONTEXT_DEPLOYMENT.md
│   │   └── ... (deployment docs)
│   │
│   ├── tests_quality/
│   │   ├── E2E_TESTS_FIX_SUMMARY.md
│   │   ├── E2E_TESTS_IMPLEMENTATION_REPORT.md
│   │   ├── E2E_TESTS_SUCCESS_REPORT.md
│   │   ├── PERSISTENCE_TESTS_SUMMARY.md
│   │   └── ... (testing docs)
│   │
│   ├── project_strategy/
│   │   ├── READY_TO_MERGE.md
│   │   ├── REFACTORED_E2E_TESTS_SUMMARY.md
│   │   ├── SESSION_COMPLETE_2025-11-09.md
│   │   └── ... (session/project docs)
│   │
│   └── core_bounded_contexts/
│       ├── HEXAGONAL_STRUCTURE.md
│       ├── CRITICAL_TASK_ORCHESTRATOR_CONTEXT_COUPLING.md
│       ├── RBAC_IMPLEMENTATION_SUMMARY.md
│       └── ... (core architecture docs)
│
├── docs/ (core documentation structure - KEEP + CLEAN)
│   ├── README.md (master index)
│   ├── ARCHITECTURE.md (or architecture/README.md)
│   ├── getting-started/
│   ├── reference/
│   ├── microservices/ → POINTS TO services/
│   ├── operations/
│   ├── infrastructure/
│   └── archived/
│
├── services/ (microservices - KEEP AS IS)
│   ├── planning/
│   │   ├── README.md (rich documentation)
│   │   └── ...
│   ├── task-derivation/
│   │   ├── README.md (rich documentation)
│   │   └── ...
│   ├── orchestrator/
│   │   ├── README.md (rich documentation)
│   │   └── ...
│   ├── context/
│   │   ├── README.md (rich documentation)
│   │   └── ...
│   ├── workflow/
│   │   ├── README.md (rich documentation)
│   │   └── ...
│   ├── ray_executor/
│   │   ├── README.md (rich documentation)
│   │   └── ...
│   └── ... (other services)
│
├── core/ (bounded contexts - DOCUMENT HERE)
│   ├── agents_and_tools/ → Document agents_and_tools ARCHITECTURE
│   │   ├── ARCHITECTURE.md (NEW)
│   │   └── README.md (maybe)
│   ├── orchestrator/ → Document orchestrator ARCHITECTURE
│   │   ├── ARCHITECTURE.md (NEW)
│   │   └── README.md (maybe)
│   ├── context/ → Document context ARCHITECTURE
│   │   ├── ARCHITECTURE.md (NEW)
│   │   └── README.md (maybe)
│   ├── workflow/ → Document workflow ARCHITECTURE
│   │   ├── ARCHITECTURE.md (NEW)
│   │   └── README.md (maybe)
│   └── ... (other core modules)
│
├── tests/ (testing structure - KEEP)
├── deploy/ (deployment - KEEP)
├── scripts/ (tooling - KEEP)
└── jobs/ (job definitions - KEEP)
```

---

## 🔄 Execution Plan (7 Steps)

### Step 1: Create Archive Directory Structure
```bash
mkdir -p unstructured_docs/{root_level,docs_subdirectory,deployment_infrastructure,tests_quality,project_strategy,core_bounded_contexts}
```

### Step 2: Move Root-Level .md Files
```bash
# All .md files in PROJECT_ROOT → unstructured_docs/root_level/
# Except: README.md, CONTRIBUTING.md, ROADMAP.md (keep at root)
```

### Step 3: Categorize Moved Files
```bash
# Group into ARCHIVE_2025-11-16/ subdirectory
# Organize by topic (architecture, investment, mermaid, docs-meta, tests, sessions)
```

### Step 4: Create Navigation Guide
```bash
# New: unstructured_docs/README.md
# Explains: Why these files are archived, how to find specific topics
```

### Step 5: Clean docs/ Subdirectory
```bash
# Move old docs consolidation files to unstructured_docs/docs_subdirectory/
# Keep: docs/README.md, docs/architecture/, docs/microservices/, etc.
```

### Step 6: Document Bounded Contexts
```bash
# For each core/{MODULE}:
#   Create ARCHITECTURE.md documenting that bounded context
#   Example: core/agents_and_tools/ARCHITECTURE.md
```

### Step 7: Create Root-Level Unified Documentation
```bash
# New: ARCHITECTURE.md (at project root)
# Purpose: High-level system architecture (not implementation detail)
# References: Bounded contexts + microservices + data flow
```

---

## 📋 Files to Keep at Root

✅ **KEEP THESE** (core to project):
- `README.md` (main entry point)
- `CONTRIBUTING.md` (contribution guidelines)
- `ROADMAP.md` (if it exists - project vision)
- `.cursorrules` (development rules)

---

## 📋 Files to Move to unstructured_docs/

All other `.md` files at root → unstructured_docs/ (organized by category)

---

## 🎯 What Gets Documented Where

### Level 1: Project Root (ARCHITECTURE.md)
- System overview
- How microservices interact
- Core data flows
- High-level principles

### Level 2: Microservices (services/{SERVICE}/README.md)
- Already well-documented ✅
- Keep as is
- Link from docs/microservices/README.md

### Level 3: Core Bounded Contexts (core/{MODULE}/ARCHITECTURE.md)
- Domain model for that context
- Ports defined
- Use cases
- Internal structure
- Example: core/agents_and_tools/ARCHITECTURE.md

### Level 4: Unstructured Archive (unstructured_docs/)
- All old consolidation files
- All session/progress files
- All analysis/audit files
- Preserved for reference, not primary documentation

---

## 🔧 Implementation Notes

### Git Strategy
```bash
# 1. Create unstructured_docs/ directory structure
# 2. Use git mv (preserves history) to move files
# 3. Create one commit per category
# 4. Clean summary commit at end
```

### What NOT to Delete
- Any `.md` file is MOVED (not deleted)
- Full git history preserved
- Can be retrieved: `git log --diff-filter=R -- unstructured_docs/`

### Validation
- `find . -name "*.md" -type f | wc -l` (should stay same)
- `git log --oneline` (shows move history)
- All files accessible via git

---

## 📊 Expected Results

### Before
```
191 markdown files scattered across 50+ locations
Multiple levels of redundancy
Unclear which doc is "canonical"
Navigation time: 10-15 minutes
```

### After
```
✅ 30+ active documentation files (root + docs/ + services/)
✅ 50+ archived files (unstructured_docs/ - preserved for reference)
✅ Clear hierarchy (project → architecture → microservices → core)
✅ Single sources of truth per topic
✅ Navigation time: 30 seconds
✅ Full git history preserved
```

---

## 🎯 Success Criteria

- [ ] All `.md` files accounted for (moved or kept)
- [ ] `unstructured_docs/` has clear structure
- [ ] Root level has only essential files
- [ ] Each bounded context has `ARCHITECTURE.md`
- [ ] Project root has unified `ARCHITECTURE.md`
- [ ] Git history preserved (git log shows moves)
- [ ] No files deleted (only moved)
- [ ] All links still work (test with `git log --all --source`)

---

**Status**: Ready for execution  
**Effort**: ~2-3 hours  
**Risk**: LOW (git-based moves, fully reversible)  
**Next Step**: Approval to execute


