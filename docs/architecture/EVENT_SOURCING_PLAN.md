# Event Sourcing Implementation Plan

## 📋 Overview

This document outlines the plan to implement **Event Sourcing** in the SWE AI Fleet system, transforming the Context Service from a stateless notification system to an event-driven architecture with full auditability and state reconstruction capabilities.

## 🎯 Current State (v0.2.3)

### Architecture
- **Pattern**: Request/Response + Ephemeral Events
- **State Storage**: Neo4j (graph) + Valkey (cache)
- **NATS Consumers**: Ephemeral (no durability)
- **Message Loss**: Acceptable during pod restarts
- **Audit Trail**: Limited (only current state in DB)

### Implementation Details
```python
# Current: Ephemeral consumers with queue groups
await js.subscribe(
    "context.update.request",
    queue="context-workers",  # Load balancing only
)
```

**Why Ephemeral?**
- State of truth is in Neo4j/Valkey
- Events are notifications, not commands
- Can recover from database on restart
- Simpler implementation for MVP

---

## 🚀 Target State: Event Sourcing

### Architecture
- **Pattern**: Event Sourcing + CQRS
- **Event Store**: NATS JetStream (durable streams)
- **State Storage**: Derived from events + Read models (Neo4j/Valkey)
- **NATS Consumers**: Durable (exactly-once processing)
- **Message Loss**: Zero tolerance
- **Audit Trail**: Complete event history with replay capability

### Key Principles

#### 1. **Events as Source of Truth**
```
Event Stream (Immutable):
  ContextCreated(story_id="S1", timestamp="...")
  → DecisionAdded(story_id="S1", decision_id="D1", ...)
  → SubtaskUpdated(story_id="S1", subtask_id="T1", status="completed")
  → ContextSnapshot(story_id="S1", version=10)
```

Current State = Replay(All Events)

#### 2. **Write Model vs Read Model (CQRS)**
```
Commands → Events → Event Store
                         ↓
                    Projections
                         ↓
              Read Models (Neo4j, Valkey)
```

#### 3. **Durable Consumers per Pod**
```python
# Future: Each pod has unique durable consumer
import socket

pod_name = socket.gethostname()  # "context-abc123"

await js.subscribe(
    "context.events.updates",
    durable=f"context-projector-{pod_name}",
    queue="context-workers",
)
```

---

## 📐 Implementation Phases

### **Phase 1: Event Store Setup** (Sprint N+1)
**Goal**: Establish event streaming infrastructure

**Tasks**:
1. Design event schema (Protobuf)
   ```protobuf
   message ContextEvent {
     string event_id = 1;
     string aggregate_id = 2;  // story_id
     int64 version = 3;
     google.protobuf.Timestamp timestamp = 4;
     oneof event_data {
       ContextCreatedEvent created = 10;
       DecisionAddedEvent decision_added = 11;
       SubtaskUpdatedEvent subtask_updated = 12;
       // ...
     }
   }
   ```

2. Create NATS JetStream streams
   - `CONTEXT_EVENTS`: Main event log
   - Retention: 30 days + compaction
   - Subjects: `context.events.{aggregate_id}.{event_type}`

3. Implement event publisher
   ```python
   class EventPublisher:
       async def publish_event(self, event: ContextEvent):
           await self.js.publish(
               f"context.events.{event.aggregate_id}.{event.type}",
               event.SerializeToString()
           )
   ```

**Success Criteria**:
- Events published to JetStream
- Event retention configured
- No breaking changes to existing API

---

### **Phase 2: Durable Consumers** (Sprint N+2)
**Goal**: Guarantee exactly-once event processing

**Tasks**:
1. Update NATS handler for durable consumers
   ```python
   class DurableContextHandler:
       def __init__(self):
           self.pod_name = os.getenv("HOSTNAME")  # K8s pod name
       
       async def subscribe(self):
           # Each pod gets unique durable consumer
           await self.js.subscribe(
               "context.events.>",
               durable=f"context-{self.pod_name}",
               queue="context-workers",
               deliver_policy=DeliverPolicy.ALL,
               ack_policy="explicit",
           )
   ```

2. Implement idempotent event handlers
   ```python
   @idempotent(key=lambda event: event.event_id)
   async def handle_event(self, event: ContextEvent):
       # Check if already processed
       if await self.is_processed(event.event_id):
           return
       
       # Process event
       await self._apply_event(event)
       
       # Mark as processed
       await self.mark_processed(event.event_id)
   ```

3. Add consumer offset management
   - Track last processed event per consumer
   - Store in Valkey: `consumer:{pod_name}:offset`

**Success Criteria**:
- No message loss during pod restarts
- Duplicate events are detected and skipped
- Consumer state persists across restarts

---

### **Phase 3: Event Projections** (Sprint N+3)
**Goal**: Build read models from events

**Tasks**:
1. Implement projection system
   ```python
   class Neo4jProjection:
       async def project(self, event: ContextEvent):
           match event.event_data:
               case ContextEvent.DecisionAddedEvent(decision):
                   await self._create_decision_node(decision)
               case ContextEvent.SubtaskUpdatedEvent(subtask):
                   await self._update_subtask_node(subtask)
   ```

2. Add snapshot mechanism
   - Create snapshots every N events
   - Store in Neo4j as `ContextSnapshot` nodes
   - Reduce replay time for large event streams

3. Implement event replay for recovery
   ```python
   async def rebuild_state(self, aggregate_id: str):
       # Fetch all events for aggregate
       events = await self.fetch_events(aggregate_id)
       
       # Replay from snapshot or beginning
       snapshot = await self.load_snapshot(aggregate_id)
       start_version = snapshot.version if snapshot else 0
       
       for event in events[start_version:]:
           await self.projection.project(event)
   ```

**Success Criteria**:
- Neo4j state matches event stream
- Snapshots reduce replay time by >90%
- Can rebuild entire state from events

---

### **Phase 4: Event Versioning & Migration** (Sprint N+4)
**Goal**: Handle schema evolution gracefully

**Tasks**:
1. Implement event upcasting
   ```python
   class EventUpcaster:
       def upcast(self, event: dict) -> ContextEvent:
           if event["schema_version"] == 1:
               event = self._upcast_v1_to_v2(event)
           return ContextEvent.parse(event)
   ```

2. Add backward compatibility layer
3. Document event evolution strategy

---

### **Phase 5: Temporal Queries** (Sprint N+5)
**Goal**: Query state at any point in time

**Tasks**:
1. Implement time-travel queries
   ```python
   async def get_context_at(self, story_id: str, timestamp: datetime):
       events = await self.fetch_events_until(story_id, timestamp)
       return self._replay_to_state(events)
   ```

2. Add temporal API endpoints
   ```protobuf
   rpc GetContextAtTime(GetContextAtTimeRequest) returns (GetContextResponse);
   ```

3. Performance optimization with indexed snapshots

---

## 🎯 Benefits of Event Sourcing

### **Operational**
- ✅ **Complete Audit Trail**: Every change is recorded
- ✅ **Time Travel**: Query state at any point in history
- ✅ **Debugging**: Replay events to reproduce bugs
- ✅ **Zero Data Loss**: Events are immutable and durable

### **Technical**
- ✅ **CQRS**: Separate read/write models for optimization
- ✅ **Event Replay**: Rebuild state from scratch
- ✅ **Scalability**: Read models can be optimized independently
- ✅ **Flexibility**: Add new projections without changing events

### **Business**
- ✅ **Compliance**: Full audit trail for regulatory requirements
- ✅ **Analytics**: Rich event data for ML/analytics
- ✅ **Experimentation**: Test new features on historical data

---

## ⚠️ Challenges & Mitigations

### **Challenge 1: Event Schema Evolution**
**Problem**: Changing event structure breaks old consumers

**Mitigation**:
- Use Protobuf for forward/backward compatibility
- Implement upcasters for old event versions
- Version events explicitly: `ContextEventV1`, `ContextEventV2`

### **Challenge 2: Event Replay Performance**
**Problem**: Replaying millions of events is slow

**Mitigation**:
- Regular snapshots (every 100-1000 events)
- Parallel projection rebuilding
- Indexed event streams by aggregate

### **Challenge 3: Eventual Consistency**
**Problem**: Read models lag behind event stream

**Mitigation**:
- UI shows "processing" state
- Version numbers in responses
- Optimistic UI updates

### **Challenge 4: Storage Growth**
**Problem**: Event streams grow indefinitely

**Mitigation**:
- Stream compaction (keep only latest state after N days)
- Archive old events to cold storage (S3)
- Retention policies per stream

---

## 📊 Success Metrics

| Metric | Target | Current (v0.2.3) |
|--------|--------|------------------|
| **Event Durability** | 99.99% | N/A (ephemeral) |
| **Message Loss Rate** | 0% | ~0.1% (pod restarts) |
| **Event Replay Speed** | <10s for 10K events | N/A |
| **Storage Efficiency** | <100MB per 1M events | N/A |
| **Audit Coverage** | 100% of changes | ~50% (DB logs only) |

---

## 🔗 Related Documents

- [NATS JetStream Documentation](https://docs.nats.io/nats-concepts/jetstream)
- [Event Sourcing Pattern](https://martinfowler.com/eaaDev/EventSourcing.html)
- [CQRS Pattern](https://martinfowler.com/bliki/CQRS.html)
- [Context Service Architecture](./CONTEXT_SERVICE.md)

---

## 📝 Decision Log

### **Decision 1: Why Ephemeral Now?**
**Date**: 2025-10-10  
**Status**: Temporary  
**Rationale**:
- MVP needs to ship quickly
- State is in Neo4j/Valkey (source of truth)
- Event loss is acceptable for notifications
- Will migrate to Event Sourcing in Phase 2

### **Decision 2: NATS vs Kafka for Event Store**
**Date**: 2025-10-10  
**Status**: Decided (NATS)  
**Rationale**:
- Already using NATS for other services
- JetStream provides persistence
- Simpler ops than Kafka
- Good enough for <1M events/day

### **Decision 3: Protobuf for Event Schema**
**Date**: 2025-10-10  
**Status**: Decided  
**Rationale**:
- Already using Protobuf for gRPC
- Strong typing and versioning
- Efficient serialization
- Cross-language support

---

## 🚦 Migration Path (Current → Event Sourcing)

### **Stage 1: Dual Write** (Week 1-2)
```
Command → Write to DB + Publish Event
           ↓              ↓
         Neo4j      NATS (new)
           ↓
      Read Model (current)
```

### **Stage 2: Event-First** (Week 3-4)
```
Command → Publish Event → Project to DB
                ↓              ↓
           NATS (primary)   Neo4j (derived)
                              ↓
                         Read Model (new)
```

### **Stage 3: Full Event Sourcing** (Week 5+)
```
Command → Event Store (source of truth)
              ↓
         Projections
              ↓
     Read Models (Neo4j, Valkey, etc.)
```

---

**Next Steps**:
1. Review this plan with the team
2. Prioritize Phase 1 tasks
3. Update sprint backlog
4. Design event schema (Protobuf)
5. Spike: NATS JetStream performance testing

**Owner**: Architecture Team  
**Last Updated**: 2025-10-10  
**Status**: 📝 Draft → Ready for Review

