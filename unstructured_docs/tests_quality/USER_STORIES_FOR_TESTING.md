# 📋 Historias de Usuario para Testing E2E

**Fecha**: 16 de Octubre de 2025  
**Propósito**: Historias reales de diferentes complejidades para probar el sistema completo

---

## 🟢 HISTORIA BÁSICA - US-001

**Título**: Agregar endpoint de health check al API

**Como**: DevOps Engineer  
**Quiero**: Un endpoint `/health` que devuelva el estado del servicio  
**Para**: Poder monitorear la disponibilidad del API desde Kubernetes

### Criterios de Aceptación

1. Endpoint GET `/health` responde 200 OK cuando el servicio está operativo
2. Respuesta JSON con formato: `{"status": "healthy", "timestamp": "..."}`
3. Endpoint no requiere autenticación
4. Responde en < 100ms

### Complejidad

- **Estimación**: 1 Story Point
- **Roles involucrados**: DEV (1 dev)
- **Subtareas esperadas**: 2-3
  1. DEV: Crear endpoint /health en API
  2. DEV: Agregar test para endpoint
  3. DEVOPS: Actualizar probes de Kubernetes

### Datos de Prueba

```json
{
  "story_id": "US-BASIC-001",
  "title": "Health check endpoint",
  "phase": "BUILD",
  "complexity": "LOW",
  "estimated_hours": 2,
  "roles": ["DEV", "DEVOPS"]
}
```

---

## 🟡 HISTORIA MEDIA - US-002

**Título**: Implementar autenticación JWT en API REST

**Como**: Usuario de la aplicación  
**Quiero**: Autenticarme con email/password y recibir un token JWT  
**Para**: Acceder de forma segura a los endpoints protegidos del API

### Criterios de Aceptación

1. Endpoint POST `/auth/login` acepta `{email, password}`
2. Valida credenciales contra base de datos PostgreSQL
3. Retorna JWT token válido por 24 horas si credenciales correctas
4. JWT incluye claims: user_id, email, roles
5. Endpoints protegidos validan JWT en header Authorization
6. Token expirado retorna 401 Unauthorized
7. Tests de integración cubren casos happy path y edge cases

### Complejidad

- **Estimación**: 5 Story Points
- **Roles involucrados**: ARCHITECT, DEV (2 devs), QA, DATA
- **Subtareas esperadas**: 8-12
  1. ARCHITECT: Diseñar arquitectura de autenticación (JWT vs sessions)
  2. DATA: Crear tabla users si no existe
  3. DATA: Diseñar schema para tokens/refresh
  4. DEV: Implementar endpoint /auth/login
  5. DEV: Implementar middleware de validación JWT
  6. DEV: Agregar hash de passwords (bcrypt)
  7. DEV: Implementar /auth/refresh endpoint
  8. QA: Tests unitarios de login
  9. QA: Tests de integración con DB
  10. QA: Tests de seguridad (SQL injection, brute force)
  11. DEVOPS: Configurar secrets para JWT_SECRET
  12. DEVOPS: Actualizar variables de entorno

### Datos de Prueba

```json
{
  "story_id": "US-MEDIUM-002",
  "title": "JWT Authentication",
  "phase": "DESIGN",
  "complexity": "MEDIUM",
  "estimated_hours": 40,
  "roles": ["ARCHITECT", "DEV", "QA", "DATA", "DEVOPS"],
  "dependencies": [],
  "acceptance_criteria": [
    "POST /auth/login validates credentials",
    "JWT token válido por 24h",
    "Middleware valida JWT en endpoints protegidos",
    "95% test coverage en auth module"
  ]
}
```

---

## 🔴 HISTORIA COMPLEJA - US-003

**Título**: Migrar de PostgreSQL monolítico a arquitectura multi-tenant con sharding

**Como**: CTO  
**Quiero**: Migrar la base de datos a una arquitectura multi-tenant con sharding por organización  
**Para**: Escalar a millones de usuarios manteniendo aislamiento de datos y compliance GDPR

### Criterios de Aceptación

1. **Arquitectura**:
   - Implementar router de shards que dirija queries según tenant_id
   - 3 shards iniciales (PostgreSQL instances) con replicación
   - Metadata store central para mapear tenant → shard
   - Connection pooling por shard

2. **Data Migration**:
   - Script de migración para mover datos existentes a shards
   - Zero-downtime migration con dual-write pattern
   - Rollback plan documentado
   - Data integrity checks post-migration

3. **Application Layer**:
   - Modificar ORM para incluir tenant_id en todas las queries
   - Implementar TenantContext middleware
   - Row-level security policies
   - API keys por tenant

4. **Observability**:
   - Métricas por shard (CPU, memory, connections, query latency)
   - Alertas para desbalanceo entre shards
   - Dashboard de distribución de tenants

5. **Testing**:
   - Tests de aislamiento entre tenants
   - Tests de failover de shards
   - Load testing con 1000 tenants simultáneos
   - Chaos engineering (kill random shard)

6. **Documentation**:
   - Arquitectura de sharding
   - Runbook de operaciones (add shard, rebalance, recovery)
   - DR plan (disaster recovery)

### Complejidad

- **Estimación**: 34 Story Points (2-3 sprints)
- **Roles involucrados**: ARCHITECT, DATA (2), DEV (3), QA (2), DEVOPS (2)
- **Subtareas esperadas**: 40-60
- **Dependencies**: 
  - Requiere aprobación de arquitectura
  - Requiere budget para 3 shards
  - Requiere testing environment

### Subtareas Detalladas (ejemplo)

#### ARCHITECT (8 subtasks)
1. Diseñar arquitectura de sharding (hash-based vs range-based)
2. Diseñar metadata store schema
3. Definir estrategia de rebalanceo
4. Diseñar dual-write pattern para zero-downtime
5. Documentar trade-offs y decisiones
6. Review de seguridad con equipo
7. Capacity planning (cuántos tenants por shard)
8. DR plan y runbooks

#### DATA (12 subtasks)
1. Diseñar schema de metadata store
2. Crear migration scripts para tenants existentes
3. Implementar data integrity checks
4. Configurar replicación en shards
5. Setup backups automáticos por shard
6. Implementar shard rebalancing scripts
7. Tests de migración en staging
8. Implementar rollback procedures
9. Data validation post-migration
10. Performance tuning de queries
11. Implementar row-level security
12. Documentar data architecture

#### DEV (15 subtasks)
1. Implementar ShardRouter class
2. Modificar database connection manager
3. Implementar TenantContext middleware
4. Agregar tenant_id a todos los modelos
5. Migrar queries para incluir tenant_id
6. Implementar metadata store client
7. Implementar connection pooling por shard
8. Crear API para tenant provisioning
9. Implementar tenant isolation checks
10. Refactorizar ORM queries
11. Implementar circuit breakers por shard
12. Health checks por shard
13. Metrics collection por shard
14. Error handling para shard failures
15. Integration tests

#### QA (10 subtasks)
1. Tests de aislamiento entre tenants
2. Tests de data integrity
3. Load testing (1000 concurrent tenants)
4. Failover testing (kill shard)
5. Performance regression tests
6. Security audit (tenant data leakage)
7. Chaos engineering tests
8. Migration validation tests
9. Rollback procedure testing
10. E2E tests con múltiples shards

#### DEVOPS (10 subtasks)
1. Provisionar 3 PostgreSQL instances
2. Configurar replicación
3. Setup monitoring por shard
4. Configurar alertas
5. Implementar automated backups
6. Setup staging environment con shards
7. CI/CD updates para multi-shard
8. Kubernetes manifests para shards
9. Secrets management para conexiones
10. Runbook documentation

### Datos de Prueba

```json
{
  "story_id": "US-COMPLEX-003",
  "title": "Multi-tenant Sharding Architecture",
  "phase": "DESIGN",
  "complexity": "VERY_HIGH",
  "estimated_hours": 680,
  "epic": "EPIC-SCALABILITY",
  "roles": ["ARCHITECT", "DATA", "DEV", "QA", "DEVOPS"],
  "num_subtasks_estimated": 55,
  "sprints_estimated": 3,
  "dependencies": [
    "INFRA-001: Provision additional database servers",
    "SEC-002: Security review for multi-tenancy"
  ],
  "risks": [
    "Data migration puede tomar 24h+ con downtime",
    "Rollback complejo si falla migration",
    "Requiere coordinación con clientes (maintenance window)"
  ],
  "acceptance_criteria": [
    "3 shards operacionales con replicación",
    "Zero data loss durante migración",
    "Query latency p95 < 100ms por shard",
    "100% aislamiento entre tenants verificado",
    "Automated failover funcional",
    "95% test coverage en código nuevo"
  ]
}
```

---

## 📊 COMPARACIÓN DE COMPLEJIDADES

| Aspecto | Básica (US-001) | Media (US-002) | Compleja (US-003) |
|---------|-----------------|----------------|-------------------|
| **Story Points** | 1 | 5 | 34 |
| **Horas estimadas** | 2h | 40h | 680h |
| **Roles** | 2 | 5 | 5 (múltiples personas) |
| **Subtareas** | 3 | 12 | 55 |
| **Sprints** | < 1 día | 1 sprint | 3 sprints |
| **Risk** | Bajo | Medio | Alto |
| **Dependencies** | Ninguna | Ninguna | 2 externas |
| **Rollback** | Trivial | Medio | Complejo |
| **Testing** | Unit | Unit + Integration | Unit + Integration + E2E + Chaos |

---

## 🧪 CASOS DE USO PARA TESTING

### Test con Historia Básica
**Objetivo**: Verificar flujo simple de 1 rol, 3 subtareas

**Flujo esperado**:
1. Planning publica `planning.plan.approved` con US-BASIC-001
2. Orchestrator deriva 3 subtareas
3. Agents ejecutan subtareas
4. Context guarda decisiones en Neo4j

---

### Test con Historia Media
**Objetivo**: Verificar coordinación multi-rol, deliberaciones complejas

**Flujo esperado**:
1. ARCHITECT delibera sobre arquitectura
2. DATA diseña schema
3. DEV implementa en paralelo
4. QA valida
5. DEVOPS deploya
6. Context mantiene grafo de decisiones y dependencies

---

### Test con Historia Compleja
**Objetivo**: Stress test completo del sistema

**Flujo esperado**:
1. ARCHITECT genera plan detallado (40-60 subtareas)
2. Planning deriva subtareas con dependencies
3. Orchestrator coordina 10+ agents en paralelo
4. Context mantiene contexto coherente entre 55 subtareas
5. Verificar que decisiones de ARCHITECT influyen en DEV/QA/DEVOPS

---

**Recomendación para testing inicial**: Empezar con **US-BASIC-001** para validar flujo completo, luego **US-MEDIUM-002** para multi-rol.

