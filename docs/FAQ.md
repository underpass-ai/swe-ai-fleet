# FAQ

## Can it run fully offline?
Yes. EdgeCrew is local-first and can operate without external APIs.

## Do I need GPUs?
Recommended for LLM workloads. You can still develop and run tests on CPU.

## Which container runtime is supported?
Podman/CRI-O (preferred) and Docker. Kubernetes for cluster deployments.

## Is there a risk running tools?
Execution is sandboxed in containers with resource limits and audit logs.

## How are agents coordinated?
Role-based agents collaborate via councils; an architect selects final approaches.

## How is context managed?
Summaries and a knowledge catalog feed an assembler that builds role-specific prompts.

## How is memory stored?
Short-term in a key-value store; long-term in a graph store for auditability.

## What’s the quickest way to try it?
Create a venv, install with `pip install -e .`, run unit tests, then `swe_ai_fleet-e2e --help`.


