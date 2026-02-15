# Workspace Catalog TOP Backlog (Execution)

## Objetivo inmediato

Entregar P0 completo del catálogo con foco en gobernanza de conectividad, colas read-only y DB gobernada.

## TOP 10 (orden de implementación)

1. `CAT-001` Implementar `conn.list_profiles` y `conn.describe_profile`. `DONE`
2. `CAT-002` Extender metadata de policy: `ProfileFields`, `TopicFields`, `QueueFields`, `KeyPrefixFields`. `DONE`
3. `CAT-003` NATS read tools (`nats.request`, `nats.subscribe_pull`) con límites. `DONE`
4. `CAT-004` Kafka read tools (`kafka.consume`, `kafka.topic_metadata`) con límites. `DONE`
5. `CAT-005` Rabbit read tools (`rabbit.consume`, `rabbit.queue_info`) con límites. `DONE`
6. `CAT-006` Redis read tools (`get/mget/scan/ttl/exists`) con límites. `DONE`
7. `CAT-007` Mongo read tools (`find/aggregate`) con `limit` duro. `DONE`
8. `CAT-008` Redis write gobernado (`set/del`) con TTL/prefix/approval. `DONE`
9. E2E `21` profiles governance (allow/deny). `DONE`
10. E2E `22` queues readonly + E2E `23` db governed. `DONE`
11. `CAT-009` `security.scan_dependencies` + `sbom.generate`. `DONE`
12. E2E `24` security+sbom en workspace runtime. `DONE`
13. `CAT-010` `security.scan_container` + `security.license_check`. `DONE`
14. E2E `25` security container+license en workspace runtime. `DONE`
15. `CAT-011` `image.build` + `image.inspect` + `image.push`. `DONE`
16. E2E `26` image inspect en workspace runtime. `DONE`
17. E2E `27` image build en workspace runtime. `DONE`
18. E2E `28` image push en workspace runtime. `DONE`
19. `CAT-012` mínimo (`k8s.get_pods`, `k8s.get_images`, `k8s.get_services`, `k8s.get_deployments`, `k8s.get_logs`). `IN PROGRESS`
20. `CAT-013` `artifact.upload`, `artifact.download`, `artifact.list`. `DONE`
21. `CAT-014` `repo.test_failures_summary`, `repo.stacktrace_summary`. `DONE`
22. `CAT-015` `repo.changed_files`, `repo.symbol_search`, `repo.find_references`. `DONE`
23. `CAT-016` `quality.gate` integrado en `ci.run_pipeline`. `DONE`

## Plan de 3 sprints (P0)

### Sprint 1

- Scope: `CAT-001`, `CAT-002`.
- Entregables:
  - Nuevos capabilities `conn.*`.
  - Policy enforcement declarativo para profile/topic/queue/key-prefix.
  - Unit tests de policy y schemas.
- Criterio de cierre:
  - Tool sin profile sensible queda denegado por defecto.

### Sprint 2

- Scope: `CAT-003`, `CAT-004`, `CAT-005`.
- Entregables:
  - NATS/Kafka/Rabbit read-only operativos.
  - Timeouts + `max_messages` + `max_bytes`.
  - E2E `21` + `22`.
- Criterio de cierre:
  - Deny probado para subject/topic/queue fuera de allowlist.

### Sprint 3

- Scope: `CAT-006`, `CAT-007`, `CAT-008`.
- Entregables:
  - Redis/Mongo read en catálogo.
  - Redis write gobernado con approval.
  - E2E `23`.
- Criterio de cierre:
  - Escrituras fuera de prefijo o sin TTL/approval quedan denegadas.

## Primera iteración (hoy)

- Implementar base de `conn.*`:
  - agregar capabilities y handlers stub funcionales,
  - definir modelo de `ConnectionProfile` en adapter,
  - agregar validación policy por `profile_id`.
- Dejar tests:
  - catálogo expone `conn.list_profiles` y `conn.describe_profile`,
  - deny por profile inexistente/no permitido.

## Riesgos de arranque

- Ambigüedad de ownership de profiles.
  - Mitigación: fuente única (config + secret refs) y `conn.describe_profile` sin secretos.
- Fugas de credenciales en logs.
  - Mitigación: redacción en audit + output schemas sin campos secretos.
