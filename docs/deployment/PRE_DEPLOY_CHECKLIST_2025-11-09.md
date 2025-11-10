# PRE-DEPLOY CHECKLIST - Project Hierarchy
**Date**: 2025-11-09
**Branch**: `feature/project-entity-mandatory-hierarchy`
**Target**: K8s Cluster (swe-ai-fleet namespace)

---

## 🎯 DEPLOYMENT READINESS ANALYSIS

### ✅ WHAT WE HAVE (Already Implemented)

| Component | Status | Details |
|-----------|--------|---------|
| **Domain Entities** | ✅ DONE | Project, Epic, Story, Task with mandatory hierarchy |
| **Domain Events** | ✅ DONE | ProjectCreated, EpicCreated, TaskCreated, StoryCreated |
| **gRPC API** | ✅ DONE | planning.proto v2 with 9 new RPCs |
| **gRPC Handlers** | ✅ DONE | All 9 handlers implemented in server.py |
| **Use Cases** | ✅ DONE | CreateProject, CreateEpic, CreateTask |
| **Event Publishers** | ✅ DONE | NATS publishing in all use cases |
| **Unit Tests** | ✅ DONE | 1,289 tests passing, 50.75% coverage |
| **Neo4j Constraints** | ✅ DONE (file) | cypher file exists, NOT applied yet |
| **Documentation** | ✅ DONE | NEXT_STEPS, EVENT_AUDIT, refactor proposal |

---

## ❌ WHAT'S MISSING (Blocking Deploy)

### 🔴 CRITICAL - Must Fix Before Deploy

#### 1. Event Consumers (Context Service) - **HIGHEST PRIORITY**
**Status**: ❌ NOT IMPLEMENTED
**Effort**: 4-6 hours
**Blocking**: Context Service won't react to hierarchy events

**Events Without Consumers** (from EVENT_AUDIT_2025-11-09.md):
```
planning.project.created   ❌ No consumer (Context Service needs to create Project node)
planning.epic.created      ❌ No consumer (Context Service needs to create Epic node)
planning.task.created      ❌ No consumer (Context Service needs to create Task node)
planning.story.created     ❌ No consumer (Context Service needs to create Story node)
```

**Files to Create**:
```
services/context/consumers/planning_consumer.py (UPDATE)
├── Add: _project_sub subscription
├── Add: _epic_sub subscription
├── Add: _task_sub subscription
├── Add: _story_sub subscription (if not exists)
└── Add: polling methods for each event
```

**Implementation Pattern**:
```python
# In planning_consumer.py start() method:
self._project_sub = await self.js.pull_subscribe(
    subject="planning.project.created",
    durable="context-planning-project-created",
    stream="PLANNING_EVENTS",
)

# Add polling task
async def _poll_project_created(self):
    while True:
        messages = await self._project_sub.fetch(batch=10, timeout=1.0)
        for msg in messages:
            payload = json.loads(msg.data.decode())
            # Create Project node in Neo4j
            await self.graph.save_project(
                project_id=payload["project_id"],
                name=payload["name"],
                # ...
            )
            await msg.ack()
```

**Dependencies**:
- ✅ `GraphCommandPort.save_project()` - Already implemented
- ✅ `GraphCommandPort.save_epic()` - Already implemented
- ✅ Domain mappers - Already exist
- ❌ Consumer polling loops - NOT implemented

---

#### 2. Neo4j Constraints Application - **HIGH PRIORITY**
**Status**: ❌ NOT APPLIED (file exists but not executed in cluster)
**Effort**: 30 minutes
**Blocking**: Orphan nodes can be created without parents

**File**: `core/context/infrastructure/neo4j_constraints.cypher`
```cypher
// Constraint: Tasks MUST have a parent Story
CREATE CONSTRAINT task_must_have_story IF NOT EXISTS
FOR (t:Task)
REQUIRE (t)-[:BELONGS_TO]->(:Story);

// Constraint: Stories MUST have a parent Epic
CREATE CONSTRAINT story_must_have_epic IF NOT EXISTS
FOR (s:Story)
REQUIRE (s)-[:BELONGS_TO]->(:Epic);

// Constraint: Epics MUST have a parent Project
CREATE CONSTRAINT epic_must_have_project IF NOT EXISTS
FOR (e:Epic)
REQUIRE (e)-[:BELONGS_TO]->(:Project);
```

**How to Apply**:
```bash
# Option 1: Via kubectl exec
kubectl exec -it -n swe-ai-fleet neo4j-0 -- cypher-shell \
  -u neo4j -p $NEO4J_PASSWORD \
  -f /path/to/neo4j_constraints.cypher

# Option 2: Via K8s Job
kubectl apply -f deploy/k8s/99-jobs/neo4j-apply-constraints.yaml
```

**Action**: Create K8s Job manifest to apply constraints during deploy.

---

#### 3. Container Images Rebuild - **HIGH PRIORITY**
**Status**: ❌ OUTDATED (current images don't have new code)
**Effort**: 1 hour (build + push)
**Blocking**: K8s cluster running old code without hierarchy support

**Services to Rebuild**:

##### Planning Service
```bash
# Current: registry.underpassai.com/swe-fleet/planning:v0.1.0
# New:     registry.underpassai.com/swe-fleet/planning:v0.2.0-hierarchy

cd services/planning
podman build -t registry.underpassai.com/swe-fleet/planning:v0.2.0-hierarchy .
podman push registry.underpassai.com/swe-fleet/planning:v0.2.0-hierarchy
```

**What's included in new image**:
- ✅ 9 new gRPC handlers (Project/Epic/Task)
- ✅ CreateProject/CreateEpic/CreateTask use cases
- ✅ Event publishers for hierarchy events
- ✅ Updated CreateStory with epic_id validation
- ✅ Protobuf stubs regenerated (planning_pb2.py)

##### Context Service
```bash
# Current: registry.underpassai.com/swe-fleet/context:v0.1.0
# New:     registry.underpassai.com/swe-fleet/context:v0.2.0-hierarchy

cd services/context
podman build -t registry.underpassai.com/swe-fleet/context:v0.2.0-hierarchy .
podman push registry.underpassai.com/swe-fleet/context:v0.2.0-hierarchy
```

**What's included in new image**:
- ✅ Updated domain entities (Project, Epic, Story with hierarchy)
- ✅ Neo4j adapters for Project/Epic
- ❌ Event consumers for hierarchy events (MUST IMPLEMENT FIRST)

---

#### 4. K8s Manifests Update - **MEDIUM PRIORITY**
**Status**: ❌ OUTDATED (manifests reference v0.1.0)
**Effort**: 15 minutes
**Blocking**: kubectl apply will deploy old images

**Files to Update**:

##### `deploy/k8s/30-microservices/planning.yaml`
```yaml
# Line 54: Update image tag
- image: registry.underpassai.com/swe-fleet/planning:v0.2.0-hierarchy
  # Was: registry.underpassai.com/swe-fleet/planning:v0.1.0
```

##### `deploy/k8s/30-microservices/context.yaml`
```yaml
# Update image tag
- image: registry.underpassai.com/swe-fleet/context:v0.2.0-hierarchy
```

**Note**: Can also use `:latest` tag during development, but `:v0.2.0-hierarchy` is better for traceability.

---

### 🟡 RECOMMENDED - Should Fix For Production

#### 5. NATS Stream Configuration Verification
**Status**: ⚠️ NEEDS VERIFICATION
**Effort**: 30 minutes
**Issue**: New events need to be routed correctly

**Verify Stream Subjects**:
```bash
kubectl exec -it -n swe-ai-fleet nats-0 -- nats stream info PLANNING_EVENTS

# Expected subjects:
# - planning.story.transitioned
# - planning.plan.approved
# - planning.project.created   (NEW)
# - planning.epic.created      (NEW)
# - planning.task.created      (NEW)
# - planning.story.created     (NEW)
```

**If missing, update stream**:
```bash
kubectl exec -it -n swe-ai-fleet nats-0 -- nats stream add PLANNING_EVENTS \
  --subjects="planning.>" \
  --retention=work \
  --storage=file \
  --replicas=1
```

---

#### 6. Frontend (PO-UI) Update
**Status**: ⚠️ BREAKING CHANGE
**Effort**: 2-3 hours
**Issue**: CreateStory now requires epic_id

**Current PO-UI Behavior**:
```typescript
// ui/po-react/src/components/CreateStoryForm.tsx (hypothetical)
const createStory = async (data) => {
  await planningClient.CreateStory({
    title: data.title,
    brief: data.brief,
    created_by: user.id,
    // ❌ Missing: epic_id (NOW REQUIRED)
  });
};
```

**Required Changes**:
```typescript
const createStory = async (data) => {
  await planningClient.CreateStory({
    epic_id: data.epic_id,  // ✅ NOW MANDATORY
    title: data.title,
    brief: data.brief,
    created_by: user.id,
  });
};

// Add Epic selector to UI:
<EpicSelector
  projectId={selectedProject}
  onSelect={(epicId) => setEpicId(epicId)}
/>
```

**Workaround for Deploy**:
- Create a "DEFAULT" Epic manually in Neo4j
- Hardcode `epic_id: "EPIC-DEFAULT-001"` in UI temporarily
- Log warning: "Using default epic, please implement epic selector"

---

### 🟢 OPTIONAL - Nice to Have

#### 7. Integration Tests
**Status**: ⚠️ NOT IMPLEMENTED
**Effort**: 3-4 hours
**Value**: Verify hierarchy enforcement end-to-end

**Test Scenarios**:
```python
# tests/integration/test_hierarchy_enforcement.py

async def test_cannot_create_story_without_epic():
    # Attempt to create story with non-existent epic_id
    # Should raise: ValueError("Parent epic EPIC-XYZ not found")

async def test_cannot_create_epic_without_project():
    # Attempt to create epic with non-existent project_id
    # Should raise: ValueError("Parent project PROJ-XYZ not found")

async def test_full_hierarchy_creation():
    # 1. Create Project
    # 2. Create Epic under Project
    # 3. Create Story under Epic
    # 4. Create Task under Story
    # 5. Verify all nodes linked in Neo4j
```

#### 8. Monitoring & Observability
**Status**: ⚠️ NEEDS UPDATE
**Effort**: 1-2 hours

**Add Metrics**:
```python
# services/planning/server.py
hierarchy_creation_counter = Counter(
    'planning_hierarchy_creations_total',
    'Number of hierarchy entities created',
    ['entity_type']  # project, epic, story, task
)

hierarchy_validation_failures = Counter(
    'planning_hierarchy_validation_failures_total',
    'Failed parent validations',
    ['entity_type', 'error_type']
)
```

**Add Logs**:
```python
logger.info(
    "Hierarchy entity created",
    extra={
        "entity_type": "epic",
        "entity_id": epic_id,
        "parent_id": project_id,
        "trace_id": request_id,
    }
)
```

---

## 📋 DEPLOYMENT SEQUENCE (Recommended Order)

### Step 1: Implement Event Consumers (4-6 hours) 🔴
```bash
# 1. Create/update consumers in Context Service
vim services/context/consumers/planning_consumer.py

# 2. Add unit tests
vim services/context/tests/unit/consumers/test_planning_consumer.py

# 3. Verify tests pass
cd services/context && make test-unit
```

### Step 2: Create Neo4j Constraints Job (30 min) 🔴
```bash
# 1. Create K8s Job manifest
vim deploy/k8s/99-jobs/apply-neo4j-constraints.yaml

# 2. Job will apply constraints on cluster
kubectl apply -f deploy/k8s/99-jobs/apply-neo4j-constraints.yaml
```

### Step 3: Rebuild & Push Images (1 hour) 🔴
```bash
# 1. Planning Service
cd services/planning
podman build -t registry.underpassai.com/swe-fleet/planning:v0.2.0-hierarchy .
podman push registry.underpassai.com/swe-fleet/planning:v0.2.0-hierarchy

# 2. Context Service (after consumers implemented)
cd services/context
podman build -t registry.underpassai.com/swe-fleet/context:v0.2.0-hierarchy .
podman push registry.underpassai.com/swe-fleet/context:v0.2.0-hierarchy
```

### Step 4: Update K8s Manifests (15 min) 🔴
```bash
# Update image tags
vim deploy/k8s/30-microservices/planning.yaml
vim deploy/k8s/30-microservices/context.yaml

# Commit changes
git add deploy/k8s/30-microservices/*.yaml
git commit -m "chore(k8s): update image tags to v0.2.0-hierarchy"
```

### Step 5: Deploy to Cluster (10 min) 🟡
```bash
# Apply updated manifests
kubectl apply -f deploy/k8s/30-microservices/planning.yaml
kubectl apply -f deploy/k8s/30-microservices/context.yaml

# Wait for rollout
kubectl rollout status deployment/planning -n swe-ai-fleet
kubectl rollout status deployment/context -n swe-ai-fleet

# Verify pods running
kubectl get pods -n swe-ai-fleet -l app=planning
kubectl get pods -n swe-ai-fleet -l app=context
```

### Step 6: Verify Deployment (10 min) 🟡
```bash
# 1. Check logs
kubectl logs -n swe-ai-fleet -l app=planning --tail=50
kubectl logs -n swe-ai-fleet -l app=context --tail=50

# 2. Test gRPC endpoints
grpcurl -plaintext internal-planning.swe-ai-fleet:50054 list

# 3. Create test Project
grpcurl -plaintext -d '{"name":"Test Project"}' \
  internal-planning.swe-ai-fleet:50054 \
  planning.PlanningService/CreateProject

# 4. Verify event consumed
kubectl logs -n swe-ai-fleet -l app=context | grep "project.created"
```

### Step 7: Update Frontend (2-3 hours) 🟢
```bash
# Implement Epic selector in PO-UI
# Update CreateStory form to include epic_id
# Rebuild and redeploy UI
```

---

## ⏱️ TIME ESTIMATES

| Phase | Effort | Priority |
|-------|--------|----------|
| **Event Consumers** | 4-6 hours | 🔴 CRITICAL |
| **Neo4j Constraints** | 30 min | 🔴 CRITICAL |
| **Image Rebuild** | 1 hour | 🔴 CRITICAL |
| **Manifests Update** | 15 min | 🔴 CRITICAL |
| **Deploy & Verify** | 20 min | 🟡 RECOMMENDED |
| **Frontend Update** | 2-3 hours | 🟢 OPTIONAL |
| **Integration Tests** | 3-4 hours | 🟢 OPTIONAL |
| **Monitoring** | 1-2 hours | 🟢 OPTIONAL |

**MINIMUM VIABLE DEPLOY**: 6-8 hours (Critical items only)
**PRODUCTION READY**: 12-16 hours (Critical + Recommended)
**COMPLETE**: 18-24 hours (All items)

---

## 🚦 DEPLOYMENT DECISION MATRIX

### Can We Deploy NOW?
**NO** ❌

**Reason**: Event consumers NOT implemented. Context Service won't react to hierarchy events, creating inconsistency between Planning Service (gRPC writes) and Context Service (graph reads).

### What's the MINIMUM to deploy?
1. ✅ Implement 4 event consumers in Context Service (4-6 hours)
2. ✅ Apply Neo4j constraints (30 min)
3. ✅ Rebuild images (1 hour)
4. ✅ Update manifests (15 min)
5. ✅ Deploy and verify (20 min)

**Total**: ~7 hours for minimum viable deploy

### What happens if we deploy WITHOUT consumers?
❌ **Data Inconsistency**:
- Planning Service creates Projects/Epics via gRPC ✅
- Events published to NATS ✅
- Context Service does NOT create Neo4j nodes ❌
- Queries fail: "Project PROJ-123 not found" ❌
- Orphan relationships: Story → Epic (Epic doesn't exist in graph) ❌

### Recommendation:
**DO NOT DEPLOY** until event consumers are implemented. This is a **HARD BLOCKER**.

---

## 📝 CHECKLIST SUMMARY

**Before Deploy**:
- [ ] Implement 4 event consumers (Context Service)
- [ ] Unit test consumers (90% coverage)
- [ ] Create Neo4j constraints K8s Job
- [ ] Rebuild Planning Service image
- [ ] Rebuild Context Service image
- [ ] Push images to registry
- [ ] Update K8s manifests with new image tags
- [ ] Verify NATS stream configuration
- [ ] Apply Neo4j constraints Job
- [ ] Deploy Planning Service
- [ ] Deploy Context Service
- [ ] Verify logs (no errors)
- [ ] Test CreateProject via grpcurl
- [ ] Verify event consumed (check Context logs)
- [ ] Verify Neo4j node created (cypher-shell query)

**After Deploy**:
- [ ] Update PO-UI with epic_id selector
- [ ] Add integration tests
- [ ] Add monitoring metrics
- [ ] Update user documentation

---

**Status**: 🔴 NOT READY FOR DEPLOY (Consumers blocking)
**ETA to Deploy**: 7 hours (minimum) | 16 hours (recommended)
**Next Action**: Implement event consumers in Context Service


