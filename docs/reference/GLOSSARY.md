# Glossary

**Status**: Living Document

Definitions of common terms used in the SWE AI Fleet project.

## A
- **Agent**: An autonomous entity capable of performing tasks using LLMs and Tools.
- **Architect**: A specialized agent role responsible for high-level design and planning.

## C
- **Context Rehydration**: The process of fetching relevant Knowledge Graph data and State to assemble a prompt for an agent.
- **Council**: A group of agents (usually 3) that deliberate on a problem to reach a consensus.

## D
- **Decision-Centric AI**: Our core philosophy. AI should be driven by the "Why" (Decisions) rather than just the "What" (Code snippets).
- **Deliberation**: The multi-turn process of Generate → Critique → Revise used by Councils.

## F
- **Fleet**: The collection of all available agents and services.

## H
- **Hexagonal Architecture**: The architectural pattern (Ports & Adapters) used to decouple domain logic from infrastructure.

## I
- **INVEST**: Acronym for good User Stories: Independent, Negotiable, Valuable, Estimable, Small, Testable.

## P
- **Planning Service**: The service responsible for managing the hierarchy of work (Epics, Stories).
- **Precision Context**: The result of Context Rehydration—a small, highly relevant context window (~2k-4k tokens).

## R
- **Ray Executor**: The service that bridges the K8s control plane with the GPU compute plane.

## S
- **Surgical Context**: Synonym for **Precision Context**.

## T
- **Task Derivation**: The automated process of breaking a Plan into executable Tasks using an LLM.

## W
- **Workflow Service**: The service that manages the lifecycle (FSM) of individual Tasks and enforces RBAC.

