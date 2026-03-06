# fleetctl vs planning-ui — Gap Analysis

**Date**: 2026-02-27
**Branch**: feat/fleetctl-fleet-proxy

## Legend

| Symbol | Meaning |
|--------|---------|
| OK | Fully implemented and working |
| PARTIAL | Exists but incomplete or limited |
| MISSING | Not implemented in fleetctl |
| N/A | Not applicable to CLI context |

---

## 1. Entity CRUD Operations

| Operation | planning-ui | fleetctl | Gap |
|-----------|------------|----------|-----|
| **Projects** | | | |
| List projects (with status filter) | OK | OK (client-side filter) | — |
| Create project | OK | OK | — |
| View project detail | OK | OK | — |
| Edit project | Not available | Not available | — |
| Delete project | Not available | Not available | — |
| **Epics** | | | |
| List epics (with status filter) | OK | OK (client-side filter) | — |
| Create epic | OK | OK | — |
| View epic detail | OK | OK | — |
| **Stories** | | | |
| List stories (with state filter) | OK | OK | — |
| Create story | OK | OK | — |
| View story detail | OK | OK | — |
| Transition story state | OK (full state machine UI) | OK | — |
| View DoR score | OK | OK | — |
| **Tasks** | | | |
| List tasks (with status filter) | OK | OK | — |
| Create task | PARTIAL (link only) | OK | fleetctl ahead |
| View task detail | OK (dedicated page) | PARTIAL (inline in story) | Minor |

---

## 2. Backlog Review Ceremony

| Operation | planning-ui | fleetctl | Gap |
|-----------|------------|----------|-----|
| List ceremonies (with status filter) | OK | OK (via Agent Conversations) | — |
| Create ceremony (select stories) | OK | OK | — |
| Start ceremony | OK | OK | — |
| View ceremony timeline (15 steps) | OK (visual timeline) | OK (ASCII timeline) | — |
| View review results per story | OK | OK (Agent Conversations) | — |
| Approve review plan (PO notes, concerns, priority) | OK | OK | — |
| Reject review plan (with reason) | OK | OK | — |
| Complete ceremony | OK | OK | — |
| Cancel ceremony | Not available | OK | fleetctl ahead |
| Live event updates during review | Not available | OK (WatchEvents) | fleetctl ahead |

---

## 3. Planning Ceremony

| Operation | planning-ui | fleetctl | Gap |
|-----------|------------|----------|-----|
| Start planning ceremony | OK (form with definition, story, steps) | OK | — |
| List planning instances | OK | OK | — |
| View planning instance detail | OK | OK | — |
| Select ceremony definition | OK (dropdown) | OK (text input) | — |

---

## 4. Task Derivation Ceremony

| Operation | planning-ui | fleetctl | Gap |
|-----------|------------|----------|-----|
| List task derivation ceremonies | STUB (501) | MISSING | Both incomplete |
| Create task derivation | STUB (501) | MISSING | Both incomplete |
| View task derivation detail | STUB (501) | MISSING | Both incomplete |

---

## 5. Graph / Context

| Operation | planning-ui | fleetctl | Gap |
|-----------|------------|----------|-----|
| View entity relationships (Neo4j) | OK (NodeContextViewer) | MISSING | **GAP** — no graph API in fleet-proxy |
| Traverse project->epic->story->task | OK (depth-based) | N/A (hierarchy nav covers this) | — |

---

## 6. Observability & Monitoring

| Operation | planning-ui | fleetctl | Gap |
|-----------|------------|----------|-----|
| Real-time event stream | Not available | OK (Communications Monitor) | fleetctl ahead |
| Category filtering (Domain/gRPC/Deliberation) | Not available | OK | fleetctl ahead |
| Payload search | Not available | OK | fleetctl ahead |
| Event detail with JSON payload | Not available | OK | fleetctl ahead |
| Agent deliberation viewer | Not available | OK (Agent Conversations) | fleetctl ahead |

---

## 7. Enrollment & Identity

| Operation | planning-ui | fleetctl | Gap |
|-----------|------------|----------|-----|
| Device enrollment (API key + CSR) | Not available | OK | fleetctl only |
| Certificate renewal | Not available | OK | — |

---

## 8. Decisions

| Operation | planning-ui | fleetctl | Gap |
|-----------|------------|----------|-----|
| Approve decision | Not available | OK | — |
| Reject decision | Not available | OK | — |

---

## Priority Action Items for fleetctl

### P0 — Core workflow gaps (DONE)

1. **Story state transitions** — DONE
   - `t` key in StoryDetail for state machine transitions
   - Shows valid transitions based on current state

2. **Planning ceremony start** — DONE
   - `p` key in EpicDetail opens ceremony form (definition, story, steps)
   - Calls `StartPlanningCeremony` gRPC

3. **Planning ceremony list + detail** — DONE
   - ViewCeremonies extended with `ListCeremonyInstances`, `GetCeremonyInstance`
   - Shows step statuses and outputs

### P1 — Complete existing stubs (DONE)

4. **Certificate renewal** — DONE
   - `r` key in Enrollment Done step triggers renewal flow
   - Generates new key pair + CSR, calls `Renew` gRPC

5. **Decision approval/rejection** — DONE
   - `ApproveDecision` and `RejectDecision` gRPC adapters wired
   - ViewDecisions fully functional

6. **Status filter for ListProjects/ListEpics** — DONE
   - `f` key cycles ALL/ACTIVE/ARCHIVED/DRAFT (client-side filter)
   - Applied to both Projects and ProjectDetail views

### P2 — Nice-to-have improvements (DONE)

7. **Backlog review timeline visualization** — DONE
   - ASCII timeline in BacklogReview dashboard showing ceremony phases
   - Per-story progress with status icons and timestamps

8. **DoR score display** — DONE (was already implemented)
   - Displayed in StoryDetail card and Stories list table column

9. **Task status transitions** — BLOCKED
   - Needs new fleet-proxy RPC — not available yet

### P3 — Future (not in planning-ui either)

10. **Graph context viewer**
    - Would need new fleet-proxy endpoint proxying to Context Service
    - Low priority since hierarchical nav covers main use case

11. **Task derivation ceremony**
    - Backend not implemented in planning service (501)
    - Blocked on backend work

---

## gRPC Method Implementation Status in fleetctl

| gRPC Method | FleetClient port | gRPC adapter | TUI wired | Status |
|-------------|-----------------|--------------|-----------|--------|
| Enroll | OK | OK | OK | DONE |
| Renew | OK | OK | OK | DONE |
| CreateProject | OK | OK | OK | DONE |
| CreateEpic | OK | OK | OK | DONE |
| CreateStory | OK | OK | OK | DONE |
| TransitionStory | OK | OK | OK | DONE |
| CreateTask | OK | OK | OK | DONE |
| StartPlanningCeremony | OK | OK | OK | DONE |
| StartBacklogReview | OK | OK | OK | DONE |
| CreateBacklogReview | OK | OK | OK | DONE |
| ApproveReviewPlan | OK | OK | OK | DONE |
| RejectReviewPlan | OK | OK | OK | DONE |
| CompleteBacklogReview | OK | OK | OK | DONE |
| CancelBacklogReview | OK | OK | OK | DONE |
| ApproveDecision | OK | OK | OK | DONE |
| RejectDecision | OK | OK | OK | DONE |
| ListProjects | OK | OK | OK | DONE |
| ListEpics | OK | OK | OK | DONE |
| ListStories | OK | OK | OK | DONE |
| ListTasks | OK | OK | OK | DONE |
| GetCeremonyInstance | OK | OK | OK | DONE |
| ListCeremonyInstances | OK | OK | OK | DONE |
| GetBacklogReview | OK | OK | OK | DONE |
| ListBacklogReviews | OK | OK | OK | DONE |
| WatchEvents | OK | OK | OK | DONE |

**Summary**: 24/24 RPCs fully wired. All gRPC adapters implemented and TUI-connected.

---

## Estimated Effort

| Item | Files to touch | Estimate |
|------|---------------|----------|
| Story transitions | grpc adapter + StoryDetail view | Small |
| Planning ceremony (start + list + detail) | grpc adapter + new view | Medium |
| Certificate renewal | grpc adapter + Enrollment view | Small |
| Decision approve/reject | grpc adapter + Decisions view | Small |
| Status filters (projects/epics) | Projects + ProjectDetail views | Trivial |
| DoR score display | StoryDetail + Stories views | Trivial |
| Backlog review timeline | BacklogReview view | Medium |
