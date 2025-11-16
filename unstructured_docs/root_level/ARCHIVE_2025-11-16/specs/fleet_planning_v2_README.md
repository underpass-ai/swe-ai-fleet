# Planning Service API v2

**Version**: 2.0  
**Package**: `fleet.planning.v2`  
**Status**: Active  
**Replaces**: v1 (obsolete, removed)

---

## 🎯 Purpose

gRPC API for Planning Service - User Story Management with FSM and Decision Approval Workflow.

---

## 📋 Service Definition

```protobuf
service PlanningService {
  rpc CreateStory(CreateStoryRequest) returns (CreateStoryResponse);
  rpc ListStories(ListStoriesRequest) returns (ListStoriesResponse);
  rpc TransitionStory(TransitionStoryRequest) returns (TransitionStoryResponse);
  rpc ApproveDecision(ApproveDecisionRequest) returns (ApproveDecisionResponse);
  rpc RejectDecision(RejectDecisionRequest) returns (RejectDecisionResponse);
  rpc GetStory(GetStoryRequest) returns (Story);
}
```

---

## 🆕 Changes from v1

### Added
- ✅ `ApproveDecision` RPC - PO approval workflow
- ✅ `RejectDecision` RPC - PO rejection workflow (triggers re-deliberation)
- ✅ Extended `Story` message with `created_by`, `created_at`, `updated_at`
- ✅ `TransitionStory` RPC with explicit `target_state` parameter

### Modified
- ✅ `Transition` → `TransitionStory` (clearer naming)
- ✅ `TransitionRequest.event` → `TransitionRequest.target_state` (explicit FSM)
- ✅ Removed `GetPlan` RPC (responsibility of Context Service)

### Removed
- ❌ `GetPlan` RPC (moved to Context Service)
- ❌ `ac` (acceptance criteria) field (moved to brief or Context Service)
- ❌ `plan_json` (moved to Context Service)

---

## 🔌 Integration

### Implemented By
- **Planning Service** (Python) - `services/planning/`

### Consumed By
- **API Gateway** (to be implemented) - REST → gRPC translation
- **PO UI** (via API Gateway) - Decision approval workflow

---

## 📡 Event Flow

```
PO calls CreateStory
    ↓
Planning Service publishes: planning.story.created
    ↓
Context Service consumes: Creates Story node in graph

PO calls ApproveDecision
    ↓
Planning Service publishes: planning.decision.approved
    ↓
Orchestrator consumes: Triggers execution of approved proposal
```

---

**Planning API v2** - Active specification

