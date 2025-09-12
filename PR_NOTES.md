## PR: Align docs to CRI-O-first; English translation; Golden Path/Use Cases

### Summary

- Align documentation and examples to "CRI‑O now, Kubernetes next"; remove Podman/Docker guidance.
- Translate key docs to English for consistency and broader audience.
- Add Golden Path (10 min) and Use Cases docs; link from README and docs index.
- Normalize credentials across docs and code: Redis password `swefleet-dev`; Neo4j `neo4j/swefleet-dev`.
- Minor runner docs clean-up toward CRI‑O/K8s Jobs.

### Scope of Changes

- README: Quickstart (CRI‑O), links to Golden Path / Use Cases; consistent messaging.
- docs/INDEX.md: add entries for Golden Path and Use Cases.
- docs/GOLDEN_PATH.md: end-to-end steps to run demo locally with CRI‑O services.
- docs/USE_CASES.md: narrative, outcome-oriented examples (planning, traceability, QA handover, audit).
- docs/INFRA_ARCHITECTURE.md: bilingual → English; CRI‑O current / K8s next.
- docs/DEPLOYMENT.md: English; CRI‑O flow; brief K8s values; rationale for CRI‑O.
- docs/SECURITY_PRIVACY.md: runtime hardening line in English.
- docs/RUNNER_SYSTEM.md, CONTEXT_ARCHITECTURE.md, EXECUTIVE_SUMMARY.md, ROADMAP_DETAILED.md: phrasing to CRI‑O now; K8s next.
- Runner docs/examples: remove Podman/Docker socket mounts references in examples; clarify runtime posture.
- Code consistency: default Neo4j password `swefleet-dev` in adapters/server/seed to match manifests and docs.
- FastAPI demo strings: seed examples moved to English; no behavior change.

### Rationale

- Reduce cognitive load for new users by standardizing on CRI‑O locally (K8s in next phase) and English-only docs.
- Golden Path ensures a predictable time-to-value and reduces support friction.
- Credential normalization prevents auth mismatches between manifests, scripts, and docs.

### Testing

- Verified CRI‑O manifests reference matching credentials:
  - Redis requires `swefleet-dev`.
  - Neo4j started with `neo4j/swefleet-dev`.
- Seed script uses `REDIS_URL` and `NEO4J_*` envs; defaults aligned.
- FastAPI endpoints unchanged; demo seed endpoint returns OK with translated strings.

### Follow-ups (separate PRs)

- Runner: migrate local execution to CRI‑O via Kubernetes Jobs; remove Docker runtime. (tracked)
- Runner docs rewrite for CRI‑O/K8s Jobs only; update Containerfile/Makefile accordingly. (tracked)
- Optional: add screenshots/snippets of the Decision‑Enriched report in Golden Path.

### Risks/Mitigations

- Docs drift: added docs/INDEX.md and centralized links to reduce orphan docs.
- Password defaults visibility: clearly documented; recommend overriding via env in production.


