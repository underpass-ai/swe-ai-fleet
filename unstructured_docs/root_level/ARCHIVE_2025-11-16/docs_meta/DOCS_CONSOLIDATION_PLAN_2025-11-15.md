# 📋 DOCUMENTATION CONSOLIDATION PLAN
**Date**: 2025-11-15  
**Scope**: Analyze, Clean, and Simplify docs/ (191 files → ~50 core files)  
**Effort**: ~4-6 hours refactoring  

---

## 🎯 EXECUTIVE SUMMARY

### Current State
- **191 markdown files** across 2.7MB
- **Massive redundancy**: Same content in 3-4 places
- **38 subdirectories**: Overly complex structure
- **Path inconsistencies**: 49+ references to legacy deploy/ paths
- **Orphan/obsolete files**: ~40 files no longer relevant

### Target State
- **~50 core documentation files** (organized, non-redundant)
- **Clear structure**: 5 top-level categories
- **Single source of truth**: Each topic documented once
- **Rich microservices docs**: All 6 services have complete README.md
- **Simple navigation**: One root `docs/README.md` as entry point

### Value Delivered
✅ Faster onboarding (clear path → Getting Started)  
✅ Reduced maintenance burden (less duplication)  
✅ Better consistency (single specs, single patterns)  
✅ Production-ready documentation  

---

## 📊 DETAILED ANALYSIS

### Current Structure Breakdown

```
docs/                           (2.7MB, 191 files, 38 dirs)
├── Root level files           (21 files - HIGHLY REDUNDANT)
├── architecture/              (45 files - Mixed analysis + decisions)
├── infrastructure/            (6 files - Overlaps with deploy/)
├── operations/                (3 files - Should be root-level)
├── sessions/                  (29 files - Historical, archive-worthy)
├── audits/                    (9 files - Some obsolete, 2025-11-09 latest)
├── CRITICAL/                  (2 files - HTMX with IMPLEMENTATION_STATUS)
├── microservices/             (3 files - INCOMPLETE, should be services/{SERVICE}/README.md)
├── examples/                  (2 files - Minimal content)
├── getting-started/           (3 files - Outdated, should consolidate)
├── evidence/                  (7 files - Post-milestone proof, archive-worthy)
├── investigations/            (4 files - Deep dives, archive-worthy)
├── investors/                 (5 files - Business-focused, separate concern)
├── normative/                 (2 files - Legal/compliance, minimal)
├── monitoring/                (1 file)
├── progress/                  (1 file)
├── refactoring/               (2 files)
├── reference/                 (8 files - Mixed reference material)
├── specs/                     (3 files - Should point to services/*/specs/)
├── summaries/                 (14 files - Historical summaries, archive-worthy)
└── context_demo/              (CSVs, JSONs - Keep as-is)
```

### Redundancy Matrix (Content appears 2-4 times)

| Topic | Locations | Status |
|-------|-----------|--------|
| **Microservices Architecture** | `architecture/MICROSERVICES_ARCHITECTURE.md` + `services/{service}/README.md` + `microservices/*.md` | 🔴 SPLIT |
| **Getting Started** | `docs/getting-started/quickstart.md` + `README.md` + `GOLDEN_PATH.md` + `DEVELOPMENT_GUIDE.md` | 🔴 4 PLACES |
| **Deployment** | `operations/DEPLOYMENT.md` + `GOLDEN_PATH.md` + `deploy/README.md` + several playbooks | 🔴 SCATTERED |
| **RBAC** | `architecture/RBAC_*.md` (3 files) + `architecture/decisions/2025-11-06/` (8 files) + summaries | 🟡 VERY VERBOSE |
| **Context Management** | `architecture/CONTEXT_MANAGEMENT.md` + `architecture/CONTEXT_REHYDRATION_FLOW.md` + examples | 🟡 SCATTERED |
| **Testing** | `TESTING_STRATEGY.md` (740 lines) + `TESTING_ARCHITECTURE.md` (1191 lines) | 🟡 OVERLAPPING |
| **Troubleshooting** | `K8S_TROUBLESHOOTING.md` + `CRIO_DIAGNOSTICS.md` + scattered in services/ | 🔴 FRAGMENTED |

---

## 🗑️ PHASE 1: IDENTIFY FILES FOR DELETION

### Category A: DEFINITELY DELETE (35 files)

#### Sessions & Historical Records (29 files)
```
docs/sessions/*.md                    → Move to docs/archived/sessions/
docs/progress/*.md                    → Consolidate into NEXT_STEPS
```
**Reasoning**: Historical artifacts, not current ops. Reference via git log.

#### Obsolete Audits (4 files)
```
docs/audits/current/*.md              → Keep ONLY latest (2025-11-09 versions)
docs/audits/CLUSTER_STATE_2025-10-30.md → Expired (30 days old)
```
**Reasoning**: Superseded by latest IMPLEMENTATION_STATUS.md

#### Duplicate Session Summaries (2 files)
```
docs/DOCUMENTATION_INCONSISTENCIES_2025-11-08.md  → Consolidated in cleanup plan
docs/RBAC_*.md (all 3)                           → Keep ONLY architectural decision
```

### Category B: CONSOLIDATE INTO PARENT (25 files)

#### Getting Started Consolidation
```
docs/getting-started/*.md             → Merge into docs/README.md (Quick Start section)
docs/GOLDEN_PATH.md                   → Merge into Quick Start
docs/DEVELOPMENT_GUIDE.md             → Create services/DEV_GUIDE.md
```

#### Infrastructure Docs
```
docs/infrastructure/*.md              → Keep only RAYCLUSTER_INTEGRATION.md + GPU_TIME_SLICING.md
docs/INSTALL_*.md                     → Move to docs/infrastructure/installation/
```

#### Specs
```
docs/specs/*.md                       → Point to services/*/specs/ instead
```

### Category C: ARCHIVE (20 files)
```
docs/evidence/*                       → Move to docs/archived/evidence/ (proof of milestones)
docs/investigations/*                 → Move to docs/archived/investigations/ (deep dives)
docs/investors/*                      → Move to docs/archived/investors/ (business context)
docs/summaries/*                      → Move to docs/archived/summaries/ (historical)
```

**Total deletions from root**: ~35 files  
**Total moves to archived/**: ~20 files  
**Net reduction**: 55 files → 5 core files at root

---

## 📁 PHASE 2: NEW STRUCTURE

### Target Organization

```
docs/
├── README.md                          (70 lines - MASTER INDEX)
├── VISION.md                          (unchanged - core thesis)
├── getting-started/
│   ├── README.md                      (100 lines - quick start entry)
│   ├── prerequisites.md               (unchanged)
│   └── installation.md                (merged from INSTALL_*.md)
├── architecture/
│   ├── README.md                      (150 lines - architecture overview)
│   ├── hexagonal-architecture.md      (FROM .cursorrules)
│   ├── ddd-principles.md              (domain-driven design reference)
│   ├── microservices-design.md        (from MICROSERVICES_ARCHITECTURE.md)
│   ├── event-driven-design.md         (async patterns)
│   ├── data-model.md                  (entity/VO reference)
│   └── decisions/
│       ├── README.md                  (Index of ADRs)
│       └── 2025-11-09-hierarchy.md    (Keep ONLY latest epoch)
├── microservices/
│   ├── README.md                      (80 lines - registry of all 6 services)
│   ├── planning/                      → REMOVE (points to services/planning/README.md)
│   ├── orchestrator/                  → REMOVE (points to services/orchestrator/README.md)
│   └── ...
├── operations/
│   ├── README.md                      (100 lines - ops overview)
│   ├── deployment.md                  (unified deployment guide)
│   ├── troubleshooting.md             (unified K8S + CRI-O)
│   ├── k8s-diagnostics.md             (from K8S_TROUBLESHOOTING.md)
│   └── maintenance.md                 (SLA, scaling, upgrades)
├── reference/
│   ├── README.md                      (50 lines - reference index)
│   ├── glossary.md                    (unchanged)
│   ├── api-versioning.md              (from API_VERSIONING_STRATEGY.md)
│   ├── security.md                    (from SECURITY_PRIVACY.md)
│   ├── testing.md                     (merged TESTING_STRATEGY + TESTING_ARCHITECTURE)
│   └── faq.md                         (unchanged)
├── infrastructure/
│   ├── README.md                      (GPU, Ray, CRI-O overview)
│   ├── container-runtimes.md          (CRI-O + Podman)
│   ├── gpu-setup.md                   (from GPU_TIME_SLICING.md)
│   └── ray-cluster.md                 (from RAYCLUSTER_INTEGRATION.md)
└── archived/                          (NEW FOLDER)
    ├── README.md                      (50 lines - what went here and why)
    ├── sessions/                      (29 session files)
    ├── audits/                        (old audit files, pre-2025-11-09)
    ├── evidence/                      (milestone proofs)
    ├── investigations/                (deep dives)
    ├── investors/                     (business materials)
    └── summaries/                     (historical summaries)
```

**New Total**: ~50 core files + ~80 archived = 130 files (down from 191)

---

## 💎 PHASE 3: ENRICH MICROSERVICES DOCUMENTATION

Each service **already has** a rich README.md with:
- ✅ Executive Summary
- ✅ Hexagonal Architecture (Layers, Directory Structure)
- ✅ Domain Model (Value Objects, Entities)
- ✅ Ports & Adapters
- ✅ Use Cases & Workflows
- ✅ Data Persistence
- ✅ API Reference (gRPC + AsyncAPI)
- ✅ Integration Points
- ✅ Testing & Coverage
- ✅ Getting Started
- ✅ Monitoring & Observability
- ✅ Troubleshooting
- ✅ Compliance Checklist

### Add to Each Service README

**NEW SECTIONS** (append to existing READMEs):

#### 1. **AsyncAPI Event Specification**
```markdown
## Event Specifications

### Published Events
| Event | Channel | Payload | Consumers |
| ----- | ------- | ------- | --------- |
| `planning.story.transitioned` | `agile.events` | {story_id, transition, project_id} | workflow, ... |

### Subscribed Events
| Event | Channel | Purpose | Handler |
| ----- | ------- | ------- | ------- |
| `agent.work.completed` | `agent.responses` | Get task result | ProcessResultUseCase |
```

#### 2. **gRPC Service Specification**
```markdown
## gRPC API Reference

### Services & Methods
```proto
service PlanningService {
  rpc CreateProject(...) returns (...);
  rpc GetPlan(...) returns (...);
  ...
}
```

#### 3. **Error Codes & Recovery**
```markdown
## Error Handling & Recovery

| Error | Code | Recovery | Retry |
| ----- | ---- | -------- | ----- |
| Context unavailable | 503 | Wait + exponential backoff | Yes (3x) |
| Neo4j timeout | 504 | Circuit breaker open | No (manual) |
```

#### 4. **Performance Characteristics**
```markdown
## Performance & Scaling

| Operation | Latency | Throughput | Limits |
| --------- | ------- | ---------- | ------ |
| GetPlan | 50ms | 1000 req/s | ~10K plans |
| CreateTask | 150ms | 100 req/s | Async dequeue |
```

#### 5. **SLA & Monitoring**
```markdown
## SLA & Monitoring

- **Availability**: 99.5% (target)
- **P99 Latency**: <500ms for gRPC
- **Key Metrics**: Message lag, event processing time, error rate
- **Alerting**: Pagerduty on SLA breach
```

#### 6. **Complete Troubleshooting**
Expand existing "Troubleshooting" section:
```markdown
### Common Issues

#### Issue: "Context not found" errors
**Symptom**: Task execution fails with ServiceUnavailable  
**Root Cause**: Context consumer lag >5min  
**Fix**: Restart context-service consumers, check NATS connectivity  
**Prevention**: Monitor context.lag metric

#### Issue: Task derivation timeout
**Symptom**: Ray job hangs for 30s+  
**Root Cause**: vLLM model load, GPU contention  
**Fix**: `kubectl rollout restart -n ray deployment/ray-head`  
**Prevention**: Pre-load models, monitor GPU time-slicing fairness
```

---

## 🚀 PHASE 4: CREATE ROOT DOCUMENTATION INDEX

### New `docs/README.md` (70 lines, single entry point)

```markdown
# SWE AI Fleet - Documentation

Welcome! Start here to navigate our comprehensive documentation.

## 🚀 Quick Start
- **New to the project?** → [Getting Started](./getting-started/)
- **Want to deploy?** → [Deployment Guide](./operations/deployment.md)
- **Need to debug?** → [Troubleshooting](./operations/troubleshooting.md)

## 📚 Documentation Structure

### Architecture & Design
- [Hexagonal Architecture & DDD](./architecture/hexagonal-architecture.md)
- [Microservices Design](./architecture/microservices-design.md)
- [Event-Driven Patterns](./architecture/event-driven-design.md)
- [Data Model & Value Objects](./architecture/data-model.md)
- [Architectural Decisions](./architecture/decisions/)

### Microservices (Full Specs)
| Service | Doc | Type | Status |
| ------- | --- | ---- | ------ |
| **Planning** | [README.md](../services/planning/README.md) | Core | ✅ Complete |
| **Task Derivation** | [README.md](../services/task-derivation/README.md) | Core | ✅ Complete |
| **Orchestrator** | [README.md](../services/orchestrator/README.md) | Core | ✅ Complete |
| **Context** | [README.md](../services/context/README.md) | Core | ✅ Complete |
| **Workflow** | [README.md](../services/workflow/README.md) | Core | ✅ Complete |
| **Ray Executor** | [README.md](../services/ray_executor/README.md) | Core | ✅ Complete |

### Infrastructure & Operations
- [Infrastructure Setup](./infrastructure/) - GPU, Ray, CRI-O
- [Deployment & Operations](./operations/deployment.md)
- [Troubleshooting & Maintenance](./operations/troubleshooting.md)
- [Monitoring & Observability](./operations/maintenance.md)

### Reference & Compliance
- [API Versioning Strategy](./reference/api-versioning.md)
- [Security & Privacy](./reference/security.md)
- [Testing Strategy](./reference/testing.md)
- [Glossary](./reference/glossary.md)

### Historical Archive
- [Sessions & Progress](./archived/) - Historical work, audits, investigations
- [Project Vision](./VISION.md) - Original thesis & goals

## 📖 How to Use This Documentation

1. **First time?** Read [Getting Started](./getting-started/)
2. **Deploying?** Follow [Deployment Guide](./operations/deployment.md)
3. **Developing a service?** Check [specific service README](../services/)
4. **Debugging?** Search [Troubleshooting](./operations/troubleshooting.md)
5. **Understanding design?** Read [Architecture](./architecture/)

---

**Last Updated**: 2025-11-15
```

---

## 🔧 PHASE 5: EXECUTION PLAN (WITH GIT COMMITS)

### Step 1: Archive Old Content (Commit 1)
```bash
git mv docs/sessions docs/archived/sessions
git mv docs/audits docs/archived/audits  
git mv docs/evidence docs/archived/evidence
git mv docs/investigations docs/archived/investigations
git mv docs/investors docs/archived/investors
git mv docs/summaries docs/archived/summaries

git commit -m "docs: archive historical sessions, audits, evidence

Reorganize documentation:
- Move 29 session files → archived/sessions/
- Move 4 old audit files → archived/audits/
- Move 7 evidence files → archived/evidence/
- Move 4 investigation files → archived/investigations/
- Move 5 investor files → archived/investors/
- Move 14 summary files → archived/summaries/

Total: 63 files moved to archived/
Rationale: Keep git history but remove from main docs workflow
Impact: Cleaner docs/ structure, faster navigation"
```

### Step 2: Delete Root-Level Redundancy (Commit 2)
```bash
# Delete files that are now consolidated/superseded
rm docs/RBAC_COMPLETE_JOURNEY.md
rm docs/RBAC_MERGE_READY.md
rm docs/RBAC_READY_FOR_MERGE_AND_DEPLOY.md
rm docs/DOCUMENTATION_INCONSISTENCIES_2025-11-08.md
rm docs/SESSION_SUMMARY_2025-11-09.md
rm docs/NEXT_STEPS_2025-11-09.md
rm -rf docs/getting-started/  # Will merge into ops/

git commit -m "docs: remove consolidated/superseded root-level files

Delete 9 files that were consolidated:
- RBAC_*.md (3) → Decision in architecture/decisions/
- SESSION_SUMMARY, NEXT_STEPS → Archived to git log
- DOCUMENTATION_INCONSISTENCIES → Addressed in cleanup
- getting-started/ → Merging into README.md

Impact: Reduced from 21 to 12 root files"
```

### Step 3: Consolidate Getting Started (Commit 3)
```bash
# Merge getting-started content into root
cat docs/getting-started/README.md docs/GOLDEN_PATH.md >> docs/README_TMP.md
# (manual editing and formatting)
mv docs/README_TMP.md docs/README.md

rm docs/GOLDEN_PATH.md
rm -rf docs/getting-started

mkdir -p docs/getting-started
# Create new getting-started/README.md and prerequisites.md

git commit -m "docs: consolidate getting-started into README + unified guide

Changes:
- Merge GOLDEN_PATH.md + getting-started/ → docs/README.md
- Create unified docs/getting-started/README.md (100 lines, quick entry)
- Keep prerequisites.md in getting-started/
- Remove duplicative installation docs

Result: Single entry point, clear progression
Getting Started path: docs/README.md → getting-started/ → specific guides"
```

### Step 4: Reorganize Architecture (Commit 4)
```bash
# Move decision files and consolidate
mkdir -p docs/architecture/decisions/archive
mv docs/architecture/decisions/2025-11-06 docs/architecture/decisions/archive/
mv docs/architecture/decisions/2025-11-07 docs/architecture/decisions/archive/
# Keep only latest (2025-11-08+)

# Create new high-level arch docs
# - hexagonal-architecture.md (from .cursorrules)
# - ddd-principles.md
# - event-driven-design.md

git commit -m "docs: reorganize architecture directory

Changes:
- Archive old decisions (2025-11-06/07) → decisions/archive/
- Keep latest decision epoch (2025-11-08+)
- Add new high-level architecture guides:
  - hexagonal-architecture.md (DDD + Ports/Adapters)
  - ddd-principles.md (Value Objects, Entities, Events)
  - event-driven-design.md (NATS patterns, async flows)
- Create architecture/README.md as entry point (150 lines)

Result: Clearer architecture learning path"
```

### Step 5: Consolidate Operations (Commit 5)
```bash
# Merge scattered troubleshooting
cat docs/K8S_TROUBLESHOOTING.md docs/CRIO_DIAGNOSTICS.md >> docs/operations/troubleshooting.md
# (manual dedup and formatting)

rm docs/K8S_TROUBLESHOOTING.md docs/CRIO_DIAGNOSTICS.md
rm docs/CRIO_MANIFESTS_REVIEW.md

git commit -m "docs: consolidate operations & troubleshooting

Changes:
- Merge K8S_TROUBLESHOOTING + CRIO_DIAGNOSTICS → operations/troubleshooting.md
- Create unified operations/README.md (100 lines)
- Move DEPLOYMENT.md to operations/ (if not already)
- Create operations/maintenance.md (SLA, scaling, upgrades)

Result: Single troubleshooting source, clear ops workflow
Operations path: operations/README.md → [deployment|troubleshooting|maintenance]"
```

### Step 6: Final Cleanup & Index (Commit 6)
```bash
# Create new docs/README.md as master index
# Create docs/archived/README.md (50 lines explaining what's archived)
# Update docs/architecture/README.md
# Update docs/operations/README.md
# Update docs/reference/README.md
# Update docs/infrastructure/README.md

git commit -m "docs: create unified index and clean structure

Final Structure:
  docs/README.md ...................... Master index (70 lines)
  docs/{architecture,operations,reference,infrastructure}/ ........ Category hubs
  docs/archived/ ........................ Historical materials
  services/{service}/README.md ........ Rich microservice docs (6 files)

Key Improvements:
✅ Single entry point (docs/README.md)
✅ Clear category navigation
✅ All microservices have complete 600+ line READMEs
✅ No redundancy (each topic once)
✅ Historical content preserved but archived
✅ All links internally consistent

File Count: 191 → ~130 files (32% reduction)
Navigation Time: 10min → 30sec (typical user)

See also: DOCS_CONSOLIDATION_PLAN_2025-11-15.md for detailed analysis"
```

---

## 📊 EXECUTION CHECKLIST

### Pre-Cleanup
- [ ] Review all 191 files for hidden dependencies
- [ ] Update internal links in root README.md files
- [ ] Verify services/ paths are correct (no broken symlinks)
- [ ] Export git history for important doc evolution

### Cleanup Execution
- [ ] Execute commits 1-6 above (in order)
- [ ] Validate all internal `[links](paths)` still work
- [ ] Check that no markdown references deleted files
- [ ] Verify archived/ has README explaining structure
- [ ] Test navigation flow: README → categories → specific docs

### Post-Cleanup
- [ ] Update GitHub Pages config (if using)
- [ ] Test search indexing (if using Algolia/similar)
- [ ] Create PR with comprehensive change log
- [ ] Measure: (current) 191 files → (target) ~130 files
- [ ] Team review + approval

---

## 🎁 MICROSERVICES DOCUMENTATION ENHANCEMENT

### Add to Each Service README (Append Sections)

#### For all 6 services:

```markdown
## Event Specifications (AsyncAPI)

### Published Events
- Event name, channel, payload schema, consumers

### Subscribed Events
- Event name, channel, purpose, error handling

## gRPC API Details
- Service methods with proto signatures
- Request/response examples
- Timeout & retry policy

## Error Handling & Recovery
- Error codes, root causes, fixes, prevention

## Performance Characteristics
- Latency, throughput, resource usage
- Scaling limits, bottlenecks

## Monitoring & Alerting
- Key metrics, dashboards, SLA targets
- Alert thresholds

## Complete Troubleshooting
- Common issues, symptoms, fixes, prevention
- Debug commands, log patterns
```

**Example**: See `services/planning/README.md` lines 650-750 for template.

---

## 📈 SUCCESS METRICS

| Metric | Current | Target | Check |
| ------ | ------- | ------ | ----- |
| Root-level files | 21 | 8 | `ls docs/*.md \| wc -l` |
| Total files | 191 | ~130 | `find docs -name "*.md" \| wc -l` |
| Disk usage | 2.7MB | ~2.0MB | `du -sh docs/` |
| Redundant topics | 7 types | 0 | Code review |
| Broken links | Unknown | 0 | `linkchecker docs/` |
| Service README quality | 600-850 lines | All ✅ | Manual audit |

---

## ⏱️ ESTIMATED EFFORT

| Phase | Tasks | Effort | Owner |
| ----- | ----- | ------ | ----- |
| 1. Analysis | Identify deletions, consolidations | 1h | AI |
| 2. Archive & Delete | Git moves, rm commands | 30min | AI |
| 3. Consolidate | Merge files, update links | 2h | AI |
| 4. Create Index | Write README, category hubs | 1h | AI |
| 5. Enrich Microservices | Add event/error/perf sections | 2h | AI |
| 6. Validation | Link checks, team review | 1h | Team |
| **Total** | | **~7.5h** | |

---

## 🔗 REFERENCES

- Current state: `docs/` (191 files, 2.7MB)
- Analysis: `docs/DOCUMENTATION_INCONSISTENCIES_2025-11-08.md`
- Microservices: `services/{planning,task-derivation,orchestrator,context,workflow,ray_executor}/README.md`
- Cursor rules: `.cursorrules` (HEXAGONAL_ARCHITECTURE_PRINCIPLES.md section)

---

**Next Action**: Approval to execute Phase 1 (Archive & Delete)


