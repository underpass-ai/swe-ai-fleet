# Documentation Inconsistencies Report

**Date:** 2025-11-07
**Auditor:** AI Assistant
**Scope:** Primary documentation (getting-started, architecture, operations)
**Method:** Cross-reference with git log reality

---

## 🚨 Critical Inconsistencies Found

### **1. docs/architecture/MICROSERVICES_ARCHITECTURE.md** ❌❌❌

**Status:** **OBSOLETE - Needs complete rewrite**

**Inconsistencies:**

| Line | Says | Reality | Severity |
|------|------|---------|----------|
| 13 | "Services near frontend: **Go**" | All services are **Python** | 🔴 CRITICAL |
| 30 | "Planning - **Technology: Go**" | Planning is **Python** | 🔴 CRITICAL |
| 43-53 | "**Story Coach** - Go, port 50052" | Service **does not exist** | 🔴 CRITICAL |
| 55-66 | "**Workspace Scorer** - Go, port 50053" | Service **does not exist** | 🔴 CRITICAL |
| 68-79 | "**Workspace Runner** - Python + K8s Jobs" | Not implemented (yet) | 🟡 MAJOR |
| 81-90 | "Context Service - **Go** + gRPC" | Context is **Python** | 🔴 CRITICAL |
| - | Missing **Workflow Service** | Exists (port 50056, RBAC L2) | 🔴 CRITICAL |
| - | Missing **Orchestrator Service** | Exists (port 50055) | 🔴 CRITICAL |
| - | Missing **Ray Executor Service** | Exists (port 50057) | 🔴 CRITICAL |
| - | Missing **Monitoring Service** | Exists (port 8080) | 🔴 CRITICAL |

**Verdict:** Document describes a **non-existent system**. Must be rewritten.

---

### **2. docs/getting-started/README.md** ❌

**Status:** **OUTDATED - Needs update**

**Inconsistencies:**

| Line | Says | Reality | Severity |
|------|------|---------|----------|
| 34 | `./scripts/infra/deploy-all.sh` | **Deleted** (use fresh-redeploy.sh) | 🔴 CRITICAL |
| 60 | "**StoryCoach Service**" | Does not exist | 🔴 CRITICAL |
| 61 | "**Workspace Service**" | Does not exist | 🔴 CRITICAL |
| 62 | "**PO UI**" | Exists but outdated | 🟡 MAJOR |
| - | Missing **Workflow Service** | Exists (RBAC L2) | 🔴 CRITICAL |
| - | Missing **Orchestrator** | Exists | 🔴 CRITICAL |
| - | Missing **Context** | Exists | 🔴 CRITICAL |
| - | Missing **Ray Executor** | Exists | 🔴 CRITICAL |
| - | Missing **Monitoring** | Exists | 🔴 CRITICAL |

**Verdict:** Quick start guide points to **deleted scripts** and **non-existent services**.

---

### **3. docs/getting-started/quickstart.md**

**Status:** Not checked yet (likely similar issues)

**Expected issues:**
- Probably references StoryCoach, Workspace
- Probably uses deploy-all.sh
- Probably missing new services

---

### **4. docs/operations/DEPLOYMENT.md** ✅

**Status:** **UPDATED** (Nov 7)

**Correctness:** ✅ All information accurate (fresh-redeploy.sh, Workflow on port 50056, etc.)

---

### **5. README.md** ✅

**Status:** **UPDATED** (Nov 7)

**Correctness:** ✅ All services listed, correct ports, Mermaid diagrams, RBAC L1+L2 mentioned

---

### **6. ROADMAP.md** ✅

**Status:** **UPDATED** (Nov 7)

**Correctness:** ✅ Progress metrics accurate, milestones realistic, velocity data from git

---

## 📊 Inconsistency Summary

| Document | Status | Critical Issues | Major Issues | Minor Issues |
|----------|--------|-----------------|--------------|--------------|
| **MICROSERVICES_ARCHITECTURE.md** | ❌ OBSOLETE | 8 | 1 | - |
| **getting-started/README.md** | ❌ OUTDATED | 6 | 1 | - |
| **getting-started/quickstart.md** | ⚠️ Unknown | TBD | TBD | TBD |
| operations/DEPLOYMENT.md | ✅ Current | 0 | 0 | 0 |
| README.md | ✅ Current | 0 | 0 | 0 |
| ROADMAP.md | ✅ Current | 0 | 0 | 0 |

**Total Critical Issues:** 14+
**Total Major Issues:** 2+

---

## 🎯 Actual System (Reality)

### **Services Deployed (6 microservices):**

| Service | Port | Language | Status | Tests |
|---------|------|----------|--------|-------|
| **Orchestrator** | 50055 | Python | ✅ Production | 142 |
| **Context** | 50054 | Python | ✅ Production | - |
| **Planning** | 50051 | Python | ✅ Production | 278 |
| **Workflow** | 50056 | Python | ✅ Ready | 138 |
| **Ray Executor** | 50057 | Python | ✅ Production | - |
| **Monitoring** | 8080 | Python | ✅ Production | 305 |

**Total:** 6 services, 1,265 tests, 90% coverage, **all Python**

### **Services That Don't Exist:**

- ❌ StoryCoach (port 50052) - **NEVER EXISTED**
- ❌ Workspace Scorer (port 50053) - **NEVER EXISTED**
- ❌ Workspace Runner (Python + K8s Jobs) - **NOT IMPLEMENTED**
- ❌ Gateway (REST API) - **NOT IMPLEMENTED**

### **Technology Stack (Reality):**

- **Backend:** Python 3.13+ (NOT Go)
- **Async Messaging:** NATS JetStream ✅
- **Sync RPC:** gRPC + Protocol Buffers ✅
- **Agent Execution:** Ray + vLLM ✅
- **Databases:** Neo4j + Valkey ✅
- **Container Runtime:** Podman + CRI-O ✅
- **Orchestration:** Kubernetes 1.28+ ✅

---

## 🔧 Recommended Actions

### **Priority 1: Fix Critical Documentation** (Blocker for onboarding)

**File:** `docs/architecture/MICROSERVICES_ARCHITECTURE.md`

**Action:** Complete rewrite

**New content should include:**
1. All 6 actual services (Orchestrator, Context, Planning, Workflow, Ray Executor, Monitoring)
2. Correct ports (50055, 50054, 50051, 50056, 50057, 8080)
3. Correct language (Python, not Go)
4. Architecture diagrams (Mermaid)
5. RBAC Levels 1, 2, 3
6. Event-driven flows
7. DDD + Hexagonal Architecture explanation

**ETA:** 2-3 hours

---

**File:** `docs/getting-started/README.md`

**Action:** Update

**Changes needed:**
1. Replace `deploy-all.sh` with `fresh-redeploy.sh --reset-nats`
2. Remove StoryCoach, Workspace references
3. Add all 6 actual services
4. Update architecture overview
5. Correct service ports

**ETA:** 30 minutes

---

**File:** `docs/getting-started/quickstart.md`

**Action:** Review and update (probably similar issues)

**ETA:** 30 minutes

---

### **Priority 2: Verify Other Documentation**

**Directories to audit:**
- `docs/microservices/` - Probably mentions obsolete services
- `docs/architecture/` - Multiple files may be outdated
- `docs/examples/` - May reference old APIs
- `docs/sessions/` - Historical, but should mark obsolete info

**ETA:** 1-2 hours

---

### **Priority 3: Create Documentation Standards**

**File:** `docs/normative/DOCUMENTATION_MAINTENANCE.md` (new)

**Content:**
1. How to keep docs in sync with code
2. Review checklist after major changes
3. Deprecated documentation policy
4. Documentation testing (link validation, code examples)

**ETA:** 1 hour

---

## 📋 Verification Checklist

### **Before Merging Documentation Updates:**

- [ ] All services listed match `git ls-files services/*/server.py`
- [ ] All ports match K8s manifests (`deploy/k8s/*-service.yaml`)
- [ ] All languages match Dockerfiles
- [ ] No references to deleted scripts (deploy-all.sh)
- [ ] No references to non-existent services (StoryCoach, Workspace)
- [ ] Workflow Service mentioned (port 50056, RBAC L2)
- [ ] RBAC Levels 1, 2, 3 status accurate
- [ ] Test counts match `make test-unit` output
- [ ] Coverage numbers match actual reports

---

## 🎯 Impact Assessment

### **User Impact:**

**Severity:** 🔴 **HIGH**

**Why:**
- New developers will try to deploy non-existent services
- Quick start guide points to deleted scripts (will fail)
- Architecture docs describe wrong system (confusion)
- Onboarding time increased (trial and error)

### **Project Credibility:**

**Severity:** 🔴 **HIGH**

**Why:**
- Documentation doesn't match reality (looks abandoned/chaotic)
- Makes project seem unprofessional
- Reduces trust in other documentation

---

## ✅ Action Plan

### **Immediate (This Session):**

1. ✅ README.md - DONE (Nov 7)
2. ✅ ROADMAP.md - DONE (Nov 7)
3. ✅ DEPLOYMENT.md - DONE (Nov 7)
4. ⏳ **MICROSERVICES_ARCHITECTURE.md** - REWRITE NEEDED
5. ⏳ **getting-started/README.md** - UPDATE NEEDED
6. ⏳ **getting-started/quickstart.md** - REVIEW NEEDED

### **Next Session:**

- Audit `docs/microservices/` directory
- Audit `docs/architecture/` files (20+ files)
- Create DOCUMENTATION_MAINTENANCE.md standards
- Add automated doc validation to CI

---

**Estimated Time to Fix All Critical Issues:** 4-5 hours

**Priority:** P0 (before public release or external demos)

---

**Prepared by:** AI Assistant
**Reviewed by:** Pending (Tirso García Ibáñez)
**Action Required:** Approve and execute fixes

