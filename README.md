# SWE AI Fleet

**A scrum team of AI agents that ship code — not a chatbot that writes it.**

Each agent is a specialist. One plans. One codes. One tests. One reviews.
One deploys. They coordinate through events, not prompts. They execute
in governed workspaces, not sandboxes. They learn from outcomes, not
instructions.

## The idea

What if your engineering team could scale by adding agents that actually
understand your codebase, respect your constraints, and get better over time?

Not a copilot. Not an autocomplete. A **fleet** of autonomous agents that:

- Run ceremonies (planning, backlog review, sprint retrospective)
- Break stories into tasks with dependency graphs
- Write, test, and review code in isolated workspaces
- Deploy through governed pipelines
- Learn which tools work best for each context

## Architecture

```
                    Ceremonies & Planning
                           |
                    Task Decomposition
                           |
              +------------+------------+
              |            |            |
          Architect    Developer     Tester
              |            |            |
              +-----+------+------+-----+
                    |             |
                 Reviewer        QA
                    |             |
              +-----+-------------+
              |
          Governed Execution (Underpass Runtime)
              |
    +----+----+----+----+
    |    |    |    |    |
  Code  Git  Test Build Deploy
```

Every agent gets:
- **Surgical context** from the [Rehydration Kernel](https://github.com/underpass-ai/rehydration-kernel) — only what matters for their role
- **99 governed tools** from the [Underpass Runtime](https://github.com/underpass-ai/underpass-runtime) — policy-checked, telemetry-recorded
- **Adaptive recommendations** — a 4-tier algorithm stack (heuristic to Neural Thompson Sampling) that learns which tools work

## Built on

| Component | What it provides |
|-----------|-----------------|
| [**Underpass Runtime**](https://github.com/underpass-ai/underpass-runtime) | Tool execution, policy enforcement, telemetry, adaptive learning |
| [**Rehydration Kernel**](https://github.com/underpass-ai/rehydration-kernel) | Knowledge graph traversal, explanatory context, token-bounded delivery |

## Status

Active development. The core infrastructure (runtime + kernel) is deployed
and validated through 15 E2E tests on live Kubernetes clusters with full mTLS.

Agent coordination protocols, ceremony execution, and multi-agent pipeline
orchestration are being developed internally. Components ship to the public
repositories as they mature and stabilize.

If you're interested in early access, collaboration, or just want to
talk about the architecture — reach out.

## Legal

Copyright © 2026 Tirso García Ibáñez.

This repository is part of the Underpass AI project.
Licensed under the Apache License, Version 2.0, unless stated otherwise.

Redistributions and derivative works must preserve applicable copyright,
license, and NOTICE information.

Original author: [Tirso García Ibáñez](https://github.com/tgarciai) · [LinkedIn](https://www.linkedin.com/in/tirsogarcia/) · [Underpass AI](https://github.com/underpass-ai)
