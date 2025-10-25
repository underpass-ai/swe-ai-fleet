# Architecture Evolution: How the Vision Shaped Every Decision

## 👤 Creator

**Tirso** - Founder & Software Architect

This document traces how the architectural vision—conceived by Tirso on August 9, 2025—evolved through intentional design decisions into a production-grade system by October 25, 2025.

---

## 🎯 The Unifying Thesis

```
Precision Context + Small Agents + Deliberation = Production AI

This wasn't invented mid-project. This was commit #0's DNA (August 9, 2025).
```

This single principle, articulated in **RFC-0002** (August 16, 2025 - just 7 days after project start), shaped:
- **Technology Choices** (Neo4j, Redis, Ray)
- **Architectural Patterns** (Hexagonal, Microservices, CQRS)
- **Design Decisions** (Agents, Ports, Adapters)
- **Testing Strategy** (Unit/Integration/E2E pyramid)
- **Infrastructure** (Kubernetes, GPU scaling, NATS messaging)

---

## 📊 Evolution Map: Thesis → Architecture

### Layer 1: Domain Theory (RFC-0002, August 16, 2025)
```
┌─────────────────────────────────────────────────┐
│ Problem: Small LLMs can't handle massive context │
├─────────────────────────────────────────────────┤
│ Solution: Surgical context assembly              │
│ ├─ Per-use-case isolation (scoped memory)       │
│ ├─ Persistent decision logging                  │
│ ├─ Role-based conversation indexing             │
│ └─ Reuse across similar cases                   │
└─────────────────────────────────────────────────┘
```

**Architectural Implication**: Need a **context assembly engine** that:
- Understands relationships (Neo4j)
- Scores relevance per role
- Assembles precise packs
- Persists for reuse (Redis)

---

### Layer 2: Orchestration Pattern (RFC-0003, August 16, 2025)
```
┌────────────────────────────────────────────────┐
│ Five-Phase Orchestration with Human Oversight  │
├────────────────────────────────────────────────┤
│ 1. Use Case Creation (human input)             │
│ 2. Agent Council Proposes (deliberation)       │
│ 3. Human Validates (approval gate)             │
│ 4. Controlled Execution (with checkpoints)     │
│ 5. Closure & Learning Capture                 │
└────────────────────────────────────────────────┘
```

**Architectural Implication**: Need an **orchestrator** that:
- Coordinates multi-agent consensus (not single-pass)
- Respects human checkpoints
- Logs every decision (for reuse)
- Isolates failures (one agent fails ≠ whole system fails)

---

### Layer 3: Clean Architecture (Hexagonal Pattern)
```
┌──────────────────────────────────────────────┐
│            Domain Layer (Core Logic)          │
│  - Entities: Agent, Task, DeliberationResult │
│  - Use Cases: Orchestrate, Deliberate        │
│  - NO external dependencies                  │
└────────────────┬─────────────────────────────┘
                 │ depends on
        ┌────────▼─────────┐
        │  Ports (Interfaces)│
        ├─────────────────────┤
        │ AgentPort           │
        │ ContextPort         │
        │ MessagingPort       │
        │ GraphQueryPort      │
        └────────┬────────────┘
                 │ implemented by
        ┌────────▼──────────────────┐
        │  Adapters (Implementations)│
        ├────────────────────────────┤
        │ VLLMAgent (LLM)           │
        │ NATSAdapter (messaging)    │
        │ Neo4jAdapter (graph)       │
        │ RedisAdapter (cache)       │
        │ RayAdapter (distribution)  │
        └────────────────────────────┘
```

**Why?** Because the thesis requires:
- ✅ **Testing small agents independently** (mock ports)
- ✅ **Swapping implementations** (Redis ↔ PostgreSQL)
- ✅ **Clear contracts** (ports define what agents need)
- ✅ **Decoupling from frameworks** (domain stays pure)

---

### Layer 4: Microservices (Bounded Contexts)

#### The Problem With Monoliths
```
❌ Monolithic Orchestrator
├─ All code in one place
├─ One deployment = all or nothing
├─ Hard to test individual agents
├─ Hard to scale selective components
└─ Tight coupling between agent logic and gRPC/NATS
```

#### The Microservices Solution
```
✅ Microservices = Orchestrated Hexagonal Services
├─ Planning Service (FSM for story lifecycle)
├─ StoryCoach Service (quality scoring)
├─ Workspace Service (agent work validation)
├─ Agent Orchestrator (deliberation coordination)
└─ Each with: Domain (pure) + Ports (contracts) + Adapters (gRPC/NATS)
```

**Why?** Because the thesis requires:
- ✅ **Independent scaling** (CPU-bound scoring ≠ IO-bound messaging)
- ✅ **Domain isolation** (each service focuses on one responsibility)
- ✅ **Technology flexibility** (planning in Go, orchestration in Python)
- ✅ **Team autonomy** (services owned independently)

---

### Layer 5: Communication Pattern (NATS JetStream)

#### Why Not HTTP/REST?
```
❌ Request/Response Pattern
├─ Coupling: Requester must wait for response
├─ Brittleness: Single point of failure
├─ Ordering: No guarantee of message ordering
└─ Replay: Can't replay history for debugging
```

#### Why NATS JetStream?
```
✅ Event Streams with Persistence
├─ Decoupling: Publish events, consumers handle async
├─ Resilience: JetStream persists → replay on recovery
├─ Auditability: All events logged with timestamps
├─ Ordering: Per-stream ordering guaranteed
├─ Scalability: Multiple consumers without impact
└─ Observability: Full event history available
```

**Why?** Because the thesis requires:
- ✅ **Async coordination** (agents work independently)
- ✅ **Audit trail** (every message = decision record)
- ✅ **Replay capability** (understand past decisions)
- ✅ **Resilience** (agent fails ≠ system fails)

---

### Layer 6: Data Persistence (Neo4j + Redis)

#### Why Neo4j for Context?
```
✅ Knowledge Graph = Relationships + Scoring
├─ Stores: Decisions, agents, tasks, dependencies
├─ Queries: "What agents worked on feature X?"
├─ Scoring: Rank relevance for context assembly
├─ Replay: Walk decision path to understand "why"
└─ Reuse: Find similar past cases
```

**Example Query**:
```cypher
MATCH (a:Agent)-[r:DELIBERATED]->(d:Decision)<-[:IMPLEMENTS]-(t:Task)
WHERE d.relevanceScore > 0.8 AND a.role = "QA"
RETURN d.description, d.rationale ORDER BY d.timestamp DESC
```

#### Why Redis for Scoped Memory?
```
✅ Scoped Cache = Fast + Isolated
├─ Per-use-case: Each task gets isolated namespace
├─ TTL: Auto-cleanup when use case completes
├─ Fast access: Sub-millisecond for context assembly
├─ Serializable: Snapshot for debugging
└─ Pub/Sub: Real-time notification of context changes
```

**Why?** Because the thesis requires:
- ✅ **Relationship awareness** (Neo4j shows HOW things relate)
- ✅ **Scoring capability** (Neo4j ranks relevance)
- ✅ **Isolation** (Redis namespace = use case boundary)
- ✅ **Performance** (Redis for hot context, Neo4j for cold analysis)

---

### Layer 7: Execution Engine (Ray + GPU Scaling)

#### The Challenge
```
Problem: Small agents need compute, but not all at once
├─ Agent 1 generates proposal (GPU needed)
├─ Agent 2 critiques (GPU needed)
├─ Agent 3 revises (GPU needed)
└─ Can't run all 3 in parallel on single GPU without queueing
```

#### The Solution: Ray with GPU Time-Slicing
```
✅ Ray Cluster (KubeRay) with Time-Sliced GPUs
├─ Head Node: No GPU (coordination only)
├─ Worker Nodes: 8 virtual GPUs per physical GPU (time-sliced)
├─ Queueing: Built-in work distribution
├─ Auto-scaling: Add nodes = add capacity linearly
└─ Fault-tolerance: Built-in retries + checkpointing
```

**Measured Performance**:
```
Hardware: 4× RTX 3090 (24GB each) + time-slicing
Capacity: 8 concurrent deliberations
Time: ~60s per 3-agent deliberation
Success: 100% (5/5 production runs)
GPU Util: Verified working, scheduled preemption
```

**Why?** Because the thesis requires:
- ✅ **Horizontal scaling** (add GPUs = add capacity)
- ✅ **Efficient utilization** (time-slicing maximizes GPU use)
- ✅ **Cost predictability** (CapEx not OpEx)
- ✅ **Decoupling agents** (each agent = independent Ray task)

---

### Layer 8: Testing Strategy (Pyramid)

#### Why This Shape?
```
        E2E Tests
       /          \  ← Full system, slow (5+ min)
      /            \
     /   Integration \  ← With containers, medium (45s)
    /                 \
   /        Unit        \  ← Mocked ports, fast (<300ms each)
  /_____________________ \

Coverage Breakdown:
├─ Unit Tests (fast)
│  ├─ Mock all ports (AgentPort, ContextPort, MessagingPort)
│  ├─ Validate domain logic in isolation
│  ├─ Target: 90%+ new code coverage
│  └─ Example: test_orchestrate_with_mocked_agents
│
├─ Integration Tests (medium)
│  ├─ Real adapters (NATS, Neo4j, Redis containers)
│  ├─ Validate seams (domain + infrastructure)
│  ├─ Example: test_orchestrate_with_real_nats
│  └─ Ensure message routing works
│
└─ E2E Tests (slow)
   ├─ Full Kubernetes cluster
   ├─ Real Ray workers + LLM models
   ├─ Validate complete workflows
   └─ Example: test_deliberation_end_to_end
```

**Why?** Because the thesis requires:
- ✅ **Proof agents work** (unit tests with mocks)
- ✅ **Proof infrastructure works** (integration tests with containers)
- ✅ **Proof system works** (E2E tests in production environment)
- ✅ **Fast feedback** (unit tests in milliseconds)
- ✅ **Traceability** (each layer proves something specific)

---

## 🔄 How Thesis → Architecture → Code

### Example: The Orchestrate Use Case

**From Thesis**:
> "Small agents need precise context + deliberation to achieve quality"

**Architecture Decision**:
```
Domain: OrchestrateUseCase (pure business logic)
  ├─ Accepts: TaskSpec + AgentPool + ContextPort + MessagingPort
  ├─ Does: Coordinate deliberation rounds (generate → critique → revise)
  └─ Returns: WinningProposal + DecisionArtifacts

Ports: Define contracts
  ├─ AgentPort.generate() → Proposal
  ├─ AgentPort.critique() → Critique
  ├─ ContextPort.assemble() → PreciseContext
  └─ MessagingPort.publish_event() → DomainEvent

Adapters: Implement ports
  ├─ VLLMAgentAdapter (real LLM with precise context)
  ├─ MockAgentAdapter (for unit testing)
  ├─ NATSMessagingAdapter (async event publishing)
  └─ Neo4jContextAdapter (surgical context assembly)

Tests:
  ├─ Unit: Mock all ports, test deliberation logic
  ├─ Integration: Real NATS + Neo4j, test message routing
  └─ E2E: Real Ray workers + LLM, test full flow
```

**Code Structure**:
```
services/orchestrator/
├── domain/
│   ├── entities/          ← Pure Python, zero dependencies
│   │   ├── agent.py       (Agent interface)
│   │   ├── task.py        (Task model)
│   │   ├── deliberation_result.py
│   │   └── role.py
│   │
│   ├── ports/             ← Contracts (abstractions)
│   │   ├── agent_port.py
│   │   ├── context_port.py
│   │   ├── messaging_port.py
│   │   └── ray_execution_port.py
│   │
│   └── usecases/          ← Pure business logic
│       ├── orchestrate.py (coordinates agents)
│       └── deliberate.py  (manages peer review)
│
├── infrastructure/
│   ├── adapters/          ← Implementations (external deps here)
│   │   ├── vllm_agent_adapter.py (real LLM)
│   │   ├── mock_agent_adapter.py (for testing)
│   │   ├── nats_messaging_adapter.py
│   │   ├── neo4j_context_adapter.py
│   │   └── ray_executor_adapter.py
│   │
│   ├── config/            ← Dependency injection
│   │   └── container.py   (wires adapters)
│   │
│   └── handlers/          ← gRPC/HTTP endpoints
│       └── orchestrator_handler.py
│
└── tests/
    ├── unit/              ← Mock adapters
    │   ├── test_orchestrate_usecase.py
    │   ├── test_deliberate_usecase.py
    │   └── fixtures/mocks.py
    │
    ├── integration/       ← Real adapters, containers
    │   ├── test_orchestrate_with_nats.py
    │   └── docker-compose.yml
    │
    └── e2e/              ← Full system, K8s
        └── test_deliberation_end_to_end.py
```

---

## 🎯 Decision Trace: Why Each Technology

| Decision | Thesis Requirement | Why | Alternative Rejected |
|----------|-------------------|-----|----------------------|
| **Neo4j** | Precision context + relationships | Knowledge graph = understand relationships + score relevance | PostgreSQL (no relationships), MongoDB (no graph querying) |
| **Redis** | Scoped memory isolation | Per-use-case cache = fast, isolated | PostgreSQL (slower for hot cache), file system (lost on restart) |
| **NATS JetStream** | Async coordination + auditability | Persistent streams = replay history + audit trail | HTTP/REST (blocking, harder to debug), Kafka (overkill, more ops overhead) |
| **Ray** | Horizontal GPU scaling | Distributed compute + GPU scheduling built-in | Kubernetes jobs (manual scheduling), SLURM (not cloud-native) |
| **Hexagonal** | Testable small agents | Ports/Adapters = mock infrastructure, test logic | Monolith (can't test agents independently), Layered (can't swap adapters) |
| **Microservices** | Bounded contexts + independent scaling | Each service = one responsibility = one reason to change | Monolith (all-or-nothing), Service mesh (overkill) |
| **gRPC** | Efficient agent communication | Protocol Buffers = typed contracts + performance | REST (less efficient), GraphQL (overkill) |
| **Kubernetes** | Production ops + auto-scaling | Cloud-native deployment + declarative config | Docker Compose (dev-only), VMs (manual scaling) |

---

## 🧠 How To Trace Any Decision Back To The Thesis

**Question**: "Why is context scoped per-use-case?"
```
Answer: RFC-0002 (August 16) says small agents need focused context
  ↓ So we isolate memory per task (Redis namespace)
  ↓ And score relevance per use case (Neo4j)
  ↓ So agents get only what's relevant
  ↓ Result: Smaller context window = 7B model works
```

**Question**: "Why use NATS instead of HTTP?"
```
Answer: RFC-0003 (August 16) requires auditability + coordination
  ↓ NATS JetStream persists all events (auditability)
  ↓ Multiple consumers = no blocking (coordination)
  ↓ Replay capability for debugging (transparency)
  ↓ Result: Full decision trail + resilient orchestration
```

**Question**: "Why Hexagonal Architecture?"
```
Answer: Thesis needs testable agents
  ↓ Ports = abstract dependencies
  ↓ Unit tests mock ports (test agent logic)
  ↓ Integration tests use real adapters (test infrastructure)
  ↓ Result: 92% coverage with fast, reliable tests
```

---

## 🚀 How This Enables Future Decisions

### Scaling Agents
```
Thesis: Small agents + horizontal scaling
  ↓ Architecture: Ray workers independent
  ↓ Infrastructure: GPU time-slicing
  ↓ Future: Add agents to council ✅
        Add GPUs to cluster ✅
        Scale without code changes ✅
```

### Adding New Domains
```
Thesis: Precision context = reusable across domains
  ↓ Architecture: Neo4j relationships agnostic to domain
  ↓ Infrastructure: NATS topics isolate domains
  ↓ Future: New use case = new contexts ✅
          Knowledge base shared ✅
          Same orchestrator reused ✅
```

### Swapping LLM Models
```
Thesis: Small models work with precision context
  ↓ Architecture: AgentPort abstracts LLM implementation
  ↓ Infrastructure: VLLMAgentAdapter = pluggable
  ↓ Future: Qwen 7B → Llama 13B ✅
          Just update adapter ✅
          No domain logic changes ✅
```

---

## ✨ The Coherence Check

Every major system component should answer:

> **"How do you enable the thesis: Precision Context + Small Agents + Deliberation = Production AI?"**

| Component | Answer |
|-----------|--------|
| **Neo4j** | I store relationships so context assembly can score relevance |
| **Redis** | I isolate scoped memory per use case so agents stay focused |
| **NATS** | I coordinate async agents and log every decision for replay |
| **Ray** | I distribute agents across GPUs so small models scale horizontally |
| **Hexagonal** | I abstract infrastructure so agents can be tested independently |
| **Microservices** | I isolate bounded contexts so each service evolves independently |
| **Testing Pyramid** | I prove agents work at unit, integration, and E2E levels |
| **Kubernetes** | I orchestrate services at scale with declarative config |

**If a component can't answer this question, it's not aligned with the thesis.**

---

## 🎬 How To Pitch This

**For Engineers**:
```
"Every line of code traces back to one principle: small agents with 
precise context work better than large models with massive context. 
Here's how we built that into the architecture in just 77 days (Aug 9 → Oct 25)."
```

**For Architects**:
```
"We didn't choose technologies randomly. Each choice enables the core 
thesis. Neo4j for relationships, Redis for scoping, Ray for scaling.
See how they fit together?"
```

**For Investors**:
```
"This is consistent, defensible architecture. Not pivots or experiments.
77 days of aligned decisions building toward one goal: production-grade 
AI that works on consumer hardware. From RFC to production is our speed."
```

---

**Branch**: `docs/project-genesis`  
**Document Version**: 2.0 (corrected dates)  
**Last Updated**: 2025-10-25  
**Timeline**: August 9, 2025 → October 25, 2025 (77 days)
