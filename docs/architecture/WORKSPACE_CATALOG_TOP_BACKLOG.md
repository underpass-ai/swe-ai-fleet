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
8. `CAT-008` Redis write gobernado (`set/del`) con TTL/prefix/approval.
9. E2E `21` profiles governance (allow/deny). `DONE`
10. E2E `22` queues readonly + E2E `23` db governed.

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
