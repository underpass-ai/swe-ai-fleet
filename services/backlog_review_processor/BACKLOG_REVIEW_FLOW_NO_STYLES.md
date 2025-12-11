# Backlog Review Flow

**This is the designed source of the truth by owner Tirso Garcia**

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'background': '#1a1a1a', 'primaryColor': '#f9f9f9', 'primaryTextColor': '#333333', 'primaryBorderColor': '#cccccc', 'lineColor': '#333333', 'secondaryColor': '#f4f4f4', 'tertiaryColor': '#ffffff', 'subgraphBg': '#2a2a2a', 'subgraphBorder': '#888888', 'subgraphText': '#ffffff'}}}%%
flowchart LR
    subgraph MAIN_FLOW["Backlog Review Flow"]
        style MAIN_FLOW fill:#2a2a2a,stroke:#888888,stroke-width:3px,color:#ffffff
        UI(("Planning UI"))
        PL(("Planning Service"))
        DB(("Persistence Repository<br/>(Projects/Epics/Histories...)"))
        CTX_REPO(("Context Rehydration<br/>Repository"))
        CTX(("Context Service"))
        EXEC(("Ray Executor Service"))
        BRP(("Backlog Review Processor"))

        subgraph DELIBERATION_EXEC["Deliberation Execution"]
            RAYJOB(("Ray Job"))
            VLLM(("vLLM Service"))
        end
        style DELIBERATION_EXEC fill:#2a2a2a,stroke:#888888,stroke-width:2px,color:#ffffff

        subgraph TASK_CREATION_EXEC["Task Creation Execution"]
            RAYJOB_TASK(("Ray Job"))
            VLLM_TASK(("vLLM Service"))
        end
        style TASK_CREATION_EXEC fill:#2a2a2a,stroke:#888888,stroke-width:2px,color:#ffffff

        UI <-->|"1 gRPC<br/>Get node relations<br/>(Projects→Epics→Stories→Tasks)"| PL
        PL <-->|"1.1 Repository"| DB
        UI -->|"2 gRPC<br/>Deliberation request<br/>or list of stories"| PL
        PL -->|"3 gRPC<br/>Get context rehydration<br/>by RBAC and StoryId"| CTX
        CTX <-->|"3.1 Repository<br/>context rehydration<br/>by RBAC/StoryId"| CTX_REPO
        PL -->|"4 gRPC<br/>Trigger deliberation<br/>per RBAC agent and StoryId"| EXEC
        EXEC -->|"5 RAY<br/>Create Ray job"| RAYJOB
        RAYJOB -->|"6 REST<br/>Model invocation (OpenAI)<br/>for rehydrated context"| VLLM
        VLLM -.->|"7 NATS<br/>VLLM response<br/>StoryID, DeliberationId"| BRP
        BRP -->|"8 gRPC<br/>Save deliberation response"| CTX
        CTX <-->|"8.1 Save deliberations"| CTX_REPO
        BRP --> |"9 DELIBERATIONS<br/>COMPLETED"| PL
        PL -->|"9.1 gRPC/WebSocket<br/>Notify deliberations completed"| UI
        BRP --> |"10 gRPC<br/>Trigger task creation<br/>to TASK CREATOR agent and StoryId"| EXEC
        EXEC -->|"11 RAY<br/>Create Ray job"| RAYJOB_TASK
        RAYJOB_TASK -->|"12 REST<br/>Model invocation (OpenAI)<br/>with all deliberations"| VLLM_TASK

        subgraph TASK_SAVING_LOOP["Task Saving Loop (N times - one per task)"]
            direction LR
            VLLM_TASK -.->|"13 NATS<br/>VLLM response<br/>TaskId, StoryID (N events)"| BRP
            BRP -->|"13.1 gRPC<br/>Save TASK response<br/>(N times)"| CTX
        end
        style TASK_SAVING_LOOP fill:#2a2a2a,stroke:#888888,stroke-width:2px,color:#ffffff

        BRP -.->|"14 NATS<br/>ALL TASK CREATED<br/>(after all N tasks saved)"| PL
        PL -->|"14.1 gRPC/WebSocket<br/>Notify all tasks created"| UI
    end

    %% Estilos de colores
    %% Bidireccionales: Naranja oscurecido (#DD7A00)
    linkStyle 0 stroke:#DD7A00,stroke-width:4px,stroke-opacity:1
    linkStyle 1 stroke:#DD7A00,stroke-width:4px,stroke-opacity:1
    linkStyle 4 stroke:#DD7A00,stroke-width:4px,stroke-opacity:1
    linkStyle 10 stroke:#DD7A00,stroke-width:4px,stroke-opacity:1
    %% De ida: Azul oscurecido (#0055DD)
    linkStyle 2 stroke:#0055DD,stroke-width:4px,stroke-opacity:1
    linkStyle 3 stroke:#0055DD,stroke-width:4px,stroke-opacity:1
    linkStyle 5 stroke:#0055DD,stroke-width:4px,stroke-opacity:1
    linkStyle 6 stroke:#0055DD,stroke-width:4px,stroke-opacity:1
    linkStyle 7 stroke:#0055DD,stroke-width:4px,stroke-opacity:1
    linkStyle 8 stroke:#0055DD,stroke-width:4px,stroke-opacity:1
    linkStyle 14 stroke:#0055DD,stroke-width:4px,stroke-opacity:1
    linkStyle 15 stroke:#0055DD,stroke-width:4px,stroke-opacity:1
    linkStyle 16 stroke:#0055DD,stroke-width:4px,stroke-opacity:1
    linkStyle 17 stroke:#0055DD,stroke-width:4px,stroke-opacity:1
    %% De vuelta: Rojo oscurecido (#DD0000)
    linkStyle 11 stroke:#DD0000,stroke-width:4px,stroke-opacity:1
    linkStyle 12 stroke:#DD0000,stroke-width:4px,stroke-opacity:1
    linkStyle 13 stroke:#DD0000,stroke-width:4px,stroke-opacity:1
    linkStyle 18 stroke:#DD0000,stroke-width:4px,stroke-opacity:1
    linkStyle 19 stroke:#DD0000,stroke-width:4px,stroke-opacity:1



```

### Color Legend

- **Blue lines**: Forward arrows
- **Red lines**: Return arrows
- **Orange lines**: Bidirectional arrows
