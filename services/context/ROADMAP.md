# Context Service Roadmap

## 🎯 Current State (v0.2.3)

### ✅ Implemented
- gRPC API for context management
- Neo4j integration for decision graphs
- Valkey (Redis) integration for planning cache
- NATS JetStream integration for async events
- Queue groups for load balancing (2 replicas)
- Prompt scope validation
- Session rehydration
- Kubernetes deployment with StatefulSets

### ⚙️ Architecture
```
Request → Context Service → Neo4j (graph state)
                          → Valkey (cache)
                          → NATS (ephemeral events)
```

**Event Model**: Ephemeral notifications
- Events are lost on pod restart (acceptable for MVP)
- State of truth is in Neo4j/Valkey
- No audit trail beyond DB logs

---

## 🚀 Future: Event Sourcing (Planned)

### 📋 See: [Event Sourcing Plan](../../docs/architecture/EVENT_SOURCING_PLAN.md)

### Why Event Sourcing?

The current architecture treats events as **notifications** (fire-and-forget). This is sufficient for MVP, but limits:

❌ **No complete audit trail**: Can't replay history  
❌ **No temporal queries**: Can't see state at past timestamps  
❌ **No guaranteed delivery**: Messages lost during restarts  
❌ **Limited debugging**: Can't reproduce issues from events  

Event Sourcing will transform the Context Service into an **event-driven system** where:

✅ **Events are source of truth**: All state derived from events  
✅ **Complete audit trail**: Every change recorded immutably  
✅ **Time travel**: Query state at any point in history  
✅ **Zero message loss**: Durable consumers guarantee delivery  
✅ **Event replay**: Rebuild state from scratch for debugging  

---

## 📅 Roadmap Phases

### **Phase 0: MVP** ✅ (Current - v0.2.3)
**Status**: Shipped  
**Duration**: Completed  

**Deliverables**:
- [x] gRPC API implementation
- [x] Neo4j + Valkey integration
- [x] NATS ephemeral events
- [x] Kubernetes deployment
- [x] E2E tests with Testcontainers
- [x] Queue groups for load balancing

**Architecture**:
```python
# Ephemeral consumers - simple, fast to implement
await js.subscribe(
    "context.update.request",
    queue="context-workers",  # No durability
)
```

---

### **Phase 1: Event Store Setup** 📅 (Sprint N+1)
**Goal**: Establish event streaming infrastructure

**Tasks**:
- [ ] Design event schema (Protobuf)
  - `ContextCreatedEvent`
  - `DecisionAddedEvent`
  - `SubtaskUpdatedEvent`
  - `MilestoneReachedEvent`
- [ ] Create NATS JetStream streams
  - `CONTEXT_EVENTS`: Main event log
  - Retention: 30 days + compaction
- [ ] Implement event publisher
  - Version control
  - Event ID generation
  - Timestamp management
- [ ] Dual write mode (DB + Events)

**Success Criteria**:
- Events published to JetStream ✓
- No breaking changes to API ✓
- Event retention working ✓

---

### **Phase 2: Durable Consumers** 📅 (Sprint N+2)
**Goal**: Guarantee exactly-once event processing

**Tasks**:
- [ ] Update NATS handler for durable consumers
  ```python
  # Each pod gets unique durable consumer
  pod_name = os.getenv("HOSTNAME")
  await js.subscribe(
      "context.events.>",
      durable=f"context-{pod_name}",
      queue="context-workers",
  )
  ```
- [ ] Implement idempotent event handlers
- [ ] Add consumer offset management
- [ ] Event replay on pod restart
- [ ] Monitoring and alerting

**Success Criteria**:
- Zero message loss ✓
- Duplicate detection ✓
- State persists across restarts ✓

---

### **Phase 3: Event Projections** 📅 (Sprint N+3)
**Goal**: Build read models from events (CQRS)

**Tasks**:
- [ ] Implement projection system
  - Neo4j projector (graph state)
  - Valkey projector (cache)
- [ ] Add snapshot mechanism
  - Every 100-1000 events
  - Store in Neo4j
- [ ] Event replay for recovery
- [ ] Projection lag monitoring

**Success Criteria**:
- Neo4j state matches events ✓
- Snapshots work ✓
- Replay time <10s for 10K events ✓

---

### **Phase 4: Event Versioning** 📅 (Sprint N+4)
**Goal**: Handle schema evolution gracefully

**Tasks**:
- [ ] Implement event upcasting
  - V1 → V2 migration
- [ ] Backward compatibility layer
- [ ] Event versioning strategy
- [ ] Migration tooling

**Success Criteria**:
- Old events still processable ✓
- New fields don't break old consumers ✓

---

### **Phase 5: Temporal Queries** 📅 (Sprint N+5)
**Goal**: Query state at any point in time

**Tasks**:
- [ ] Implement time-travel queries
  ```protobuf
  rpc GetContextAtTime(GetContextAtTimeRequest) returns (GetContextResponse) {
    option (google.api.http) = {
      get: "/v1/context/{story_id}/at/{timestamp}"
    };
  }
  ```
- [ ] Add temporal API endpoints
- [ ] Performance optimization
- [ ] UI for time travel

**Success Criteria**:
- Can query historical state ✓
- Performance acceptable (<500ms) ✓

---

## 🔄 Migration Strategy

### Current (Ephemeral)
```
Command → Update DB → Notify (best-effort)
           ↓
        Neo4j/Valkey (source of truth)
```

### Target (Event Sourcing)
```
Command → Publish Event → Project to DB
              ↓               ↓
        Event Store      Neo4j/Valkey (derived)
      (source of truth)
```

### Transition Plan
1. **Dual Write**: Write to DB + publish events (Phase 1-2)
2. **Event-First**: Events primary, DB derived (Phase 3)
3. **Full ES**: Remove direct DB writes (Phase 4+)

---

## 📊 Success Metrics

| Metric | Current (v0.2.3) | Target (Event Sourcing) |
|--------|------------------|-------------------------|
| **Message Loss** | ~0.1% (restarts) | 0% |
| **Audit Coverage** | 50% (DB logs) | 100% (events) |
| **Time Travel** | ❌ Not supported | ✅ Full history |
| **Event Replay** | ❌ Not possible | ✅ <10s for 10K |
| **Debugging** | Limited | Full event trace |

---

## 🔗 Related Documents

- [Event Sourcing Implementation Plan](../../docs/architecture/EVENT_SOURCING_PLAN.md)
- [Context Service API](../../specs/context.proto)
- [NATS Integration Guide](./NATS_INTEGRATION.md)
- [Deployment Guide](../../deploy/k8s/CONTEXT_DEPLOYMENT.md)

---

## 💡 Design Decisions

### **Why Not Event Sourcing from Day 1?**

**Decision**: Start with ephemeral events, migrate to ES later

**Rationale**:
1. **MVP Speed**: Ephemeral is simpler, faster to ship
2. **Learning**: Understand domain events before committing to ES
3. **Risk Mitigation**: Can validate event model before making it immutable
4. **State in DB**: Neo4j/Valkey already provide state persistence

**Trade-off**:
- ❌ Message loss during restarts (acceptable for notifications)
- ✅ Faster time to market
- ✅ Simpler initial implementation
- ✅ Can migrate incrementally

### **Why NATS over Kafka?**

**Decision**: Use NATS JetStream for event store

**Rationale**:
1. **Existing Infrastructure**: Already using NATS
2. **Simplicity**: Easier ops than Kafka
3. **Performance**: Good enough for <1M events/day
4. **Cost**: Lower resource footprint

### **Why Protobuf for Events?**

**Decision**: Use Protobuf for event schema

**Rationale**:
1. **Consistency**: Already using for gRPC
2. **Versioning**: Built-in forward/backward compatibility
3. **Performance**: Efficient serialization
4. **Type Safety**: Strong typing across languages

---

**Last Updated**: 2025-10-10  
**Owner**: Context Service Team  
**Status**: 🟢 Active Development

