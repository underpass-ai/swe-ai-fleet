# RFC-0001: Bootstrap

## Summary

Establish SWE AI Fleet initial architecture, licensing (Apache-2.0),
and minimal deployable stack (Redis, Neo4j, KubeRay).

## Goals

- Role-based multi-agent with peer councils and architect selector.
- Safe tool wrappers (dry-run by default).
- Auditable decisions (Neo4j).

## Non-Goals

- Full production hardening.

## Decision

Proceed with Python orchestrator on Ray, KubeRay for cluster, GGUF-capable loaders.
