# Backlog Review Processor Service

Dedicated microservice for converting backlog review deliberations into tasks.

## Responsibilities

1. **Accumulates agent deliberations**: Receives `agent.response.completed` events for backlog review, accumulates deliberations in memory and persists them to Neo4j for observability.

2. **Detects deliberation completion**: When all deliberations for a story are complete (ARCHITECT, QA, DEVOPS), publishes the `planning.backlog_review.deliberations.complete` event.

3. **Extracts tasks using vLLM**: Sends a job to Ray Executor with a specialized vLLM agent that analyzes all deliberations and extracts structured tasks.

4. **Creates tasks in Planning Service**: Processes agent results and creates tasks in Planning Service via gRPC, associating relevant deliberations with each task.

5. **Publishes progress events**: Publishes `planning.backlog_review.tasks.complete` events when all tasks for a story have been created, allowing Planning Service to track progress.

## Architecture

- **Event-Driven**: Listens to NATS events and processes asynchronously
- **Hexagonal Architecture**: Clear separation between domain, application, and infrastructure
- **DDD**: Immutable Value Objects, domain entities, use cases
- **Persistence**: Stores deliberations in Neo4j for observability and querying

## Flow

1. **Deliberation Accumulation**:
   - Backlog Review Processor Service receives `agent.response.completed` for backlog review
   - `BacklogReviewResultConsumer` processes the event
   - `AccumulateDeliberationsUseCase` accumulates the deliberation in memory and saves it to Neo4j
   - When all deliberations are complete (3 roles), publishes `planning.backlog_review.deliberations.complete`

2. **Task Extraction**:
   - `DeliberationsCompleteConsumer` receives the `planning.backlog_review.deliberations.complete` event
   - `ExtractTasksFromDeliberationsUseCase` builds the prompt with all deliberations and sends job to Ray Executor
   - Ray Executor executes vLLM agent that analyzes deliberations

3. **Task Creation**:
   - Agent publishes result in `agent.response.completed` (with `task_type: "TASK_EXTRACTION"`)
   - `TaskExtractionResultConsumer` processes the result and creates tasks in Planning Service
   - After creating all tasks, publishes `planning.backlog_review.tasks.complete` for Planning Service to track progress

## Persistence

Deliberations are stored in Neo4j as `AgentDeliberation` nodes with the following properties:
- `id`: Unique deliberation ID
- `agent_id`: Agent identifier
- `role`: Role (ARCHITECT, QA, DEVOPS)
- `proposal`: Full proposal (JSON string)
- `deliberated_at`: Deliberation timestamp
- `ceremony_id`: Ceremony identifier
- `story_id`: Story identifier

Relationships:
- `BELONGS_TO_CEREMONY`: To `BacklogReviewCeremony` (if exists)
- `FOR_STORY`: To `Story` (if exists)

This allows Planning Service to query deliberations when it needs to view progress or complete deliberations.

## Published Events

- `planning.backlog_review.deliberations.complete`: Published when all deliberations for a story are complete
  - Payload: `{ceremony_id, story_id, agent_deliberations: [...]}`
- `planning.backlog_review.tasks.complete`: Published when all tasks for a story have been created
  - Payload: `{ceremony_id, story_id, tasks_created: N}`

## Consumed Events

- `agent.response.completed`: vLLM agent responses (filtered by `task_id` starting with `ceremony-`)
- `planning.backlog_review.deliberations.complete`: Self-published event to trigger task extraction

## Configuration

Environment variables:

- `NATS_URL`: NATS URL (default: `nats://nats:4222`)
- `PLANNING_SERVICE_URL`: Planning Service gRPC URL (default: `planning:50054`)
- `RAY_EXECUTOR_URL`: Ray Executor gRPC URL (default: `ray-executor:50056`)
- `VLLM_URL`: vLLM service URL (default: `http://vllm-server:8000/v1`)
- `VLLM_MODEL`: Model to use (default: `meta-llama/Llama-3.1-8B-Instruct`)
- `NEO4J_URI`: Neo4j URI (default: `bolt://neo4j:7687`)
- `NEO4J_USER`: Neo4j user (default: `neo4j`)
- `NEO4J_PASSWORD`: Neo4j password (required)
- `NEO4J_DATABASE`: Neo4j database (default: `neo4j`)

## Build

```bash
# From project root
podman build -t backlog-review-processor:latest -f services/backlog_review_processor/Dockerfile .
```

## Run

```bash
docker run -e NATS_URL=nats://nats:4222 \
           -e PLANNING_SERVICE_URL=planning:50054 \
           -e RAY_EXECUTOR_URL=ray-executor:50056 \
           -e VLLM_URL=http://vllm-server:8000/v1 \
           -e VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct \
           -e NEO4J_URI=bolt://neo4j:7687 \
           -e NEO4J_USER=neo4j \
           -e NEO4J_PASSWORD=password \
           -e NEO4J_DATABASE=neo4j \
           backlog-review-processor:latest
```

## Dependencies

- **NATS**: For asynchronous events
- **Neo4j**: For deliberation persistence
- **Planning Service (gRPC)**: For creating tasks
- **Ray Executor (gRPC)**: For executing vLLM agents

## Observability

Deliberations stored in Neo4j can be queried by Planning Service to:
- View deliberation progress
- Query complete deliberations for a story
- Analyze proposals from different roles
- Rehydrate context in the future
