++ Begin File
## Infrastructure Consumers – Task Derivation Service

> DDD + Hexagonal Architecture guidelines for inbound adapters.
> _Status:_ implemented (NATS pull consumers with mapper-first validation).

---

### 1. TaskDerivationRequestConsumer
- **Source:** `task.derivation.requested` (JetStream stream `task_derivation`)
- **Purpose:** Trigger derivation whenever Planning emits a derivation request.
- **Operational flow:**
  - Pull subscription using `TaskDerivationRequestSubjects` constants
    (`subject="task.derivation.requested"`, `durable="task-derivation-request-consumer"`)
  - Background polling task (`asyncio.create_task`) fetches one message per cycle (timeout=5s) to avoid bursts.
  - Payload decoded → `TaskDerivationRequestMapper` → `TaskDerivationRequest` VO.
  - Delegates to `DeriveTasksUseCase` (application layer) with fail-fast validation.
  - ACK on success or invalid payload (mapper raises `ValueError`), NAK to retry up to `max_deliveries` (default 3) for transient failures.
- **Dependencies (constructor injection only):**
  - `nats_client`, `jetstream` (JetStreamContext)
  - `DeriveTasksUseCase`
  - `TaskDerivationRequestMapper`
- **Retries & DLQ policy:**
  - No local DLQ. After `max_deliveries`, the consumer ACKs and relies on Planning Service to re-issue if needed.
  - Mapper failures publish `task.derivation.failed` via the use case path so Planning can mark the story as “not planned”.

---

### 2. TaskDerivationResultConsumer
- **Source:** `agent.response.completed` (Ray Executor / Orchestrator replies)
- **Purpose:** Process vLLM output and persist derived tasks in Planning.
- **Operational flow:**
  - Pull subscription on executor response subject (durable defined per deployment).
  - Filters messages belonging to Task Derivation jobs (request ID prefix) before mapping.
  - Payload decoded → `LLMTaskDerivationMapper` → tuple of `TaskNode` VOs + `DependencyGraph`.
  - Delegates to `ProcessTaskDerivationResultUseCase`, which persists tasks, saves dependencies, and emits domain events (`TaskDerivationCompletedEvent` / `TaskDerivationFailedEvent`).
  - Failures in mapping or persistence lead to publishing `task.derivation.failed` (no DLQ).
- **Dependencies (constructor injection):**
  - `nats_client`, `jetstream`
  - `ProcessTaskDerivationResultUseCase`
  - `LLMTaskDerivationMapper`
- **Schema & DLQ notes:**
  - Payload currently mirrors Planning’s context schema (`plan_id`, `story_id`, `role`, `context`). Changes must be versioned, as bounded contexts evolve independently.
  - Mapper failure → publish failure event, do not retry indefinitely (no local DLQ).

---

### 3. Optional DLQ / Retry Consumers
- **Examples:** `task.derivation.failed`, `task.derivation.retry`
- **Purpose:** Alert stakeholders or requeue jobs needing manual intervention.
- **Implementation notes:**
  - Reuse same mapper stack but skip business logic (only publish alerts).
  - Consider integration with Monitoring dashboards or PO-UI.

---

### Shared requirements

1. **Dependency Injection:**
   No adapter instantiates use cases or ports internally; everything injected.

2. **Mappers at the edges:**
   DTO ↔ VO conversion must live in `infrastructure/mappers`, not in consumers.

3. **Backpressure / Flow control:**
   Use pull consumers with `fetch()` loops + ACK/NACK to avoid message loss.

4. **Logging & Observability:**
   - Log message IDs, plan/story IDs, role, and result status.
   - Surface metrics (processed, failed, retried) when observability stack is available.

5. **Configuration:**
   - Subject names and durable names should come from config (env or YAML).
   - Retry delays/backoff configurable (default 5s).

---

### Next steps
1. Finalize event contracts (AsyncAPI) with Planning Service & Ray Executor.
2. Parameterize subject/durable names via service configuration (env/YAML) if needed.
3. Add observability hooks (metrics + structured logs) once telemetry stack is ready.
4. Coordinate with Planning to ensure `task.derivation.failed` updates story status to “not planned”.

