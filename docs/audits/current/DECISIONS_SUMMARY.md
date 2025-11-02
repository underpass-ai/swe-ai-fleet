# Resumen de Decisiones Arquitecturales - 2 Nov 2025

**Arquitecto**: Tirso García Ibáñez
**Estado**: ✅ 3/4 decisiones confirmadas, ⏸️ 1 pendiente

---

## ✅ Decisiones Confirmadas

### ✅ Decision 1: Planning Service
**Opción**: **A - Nuevo Planning en Python** ✅ CONFIRMADA
- Timeline: 1-2 semanas
- Arquitectura: DDD + Hexagonal desde cero
- Separación de responsabilidades clara
- Justificación: Arquitectura limpia, evita deuda técnica del planner histórico WIP

### ✅ Decision 2: PO UI
**Opción**: **C - Revivir UI legacy** ✅ CONFIRMADA
- Timeline: 4 semanas (incluyendo API Gateway + adaptaciones)
- Código recuperado: `ui/po-react/` (commit c4fc4b5~)
- Stack: React 18.2 + TypeScript + Vite + Tailwind + SSE
- Gaps a resolver:
  - ❌ API Gateway no existe → crear nuevo servicio (FastAPI)
  - ❌ Planning Service eliminado → recrear (Decision 1)
  - ❌ SSE bridge no existe → implementar en API Gateway (NATS → SSE)
- Ahorro: 3-4 semanas vs desarrollo desde cero

### ✅ Decision 3: RBAC
**Opción**: **B - Distribuido con lógica DDD centralizada en Agent** ✅ CONFIRMADA
- Timeline: 1 semana
- Modelo DDD:
  - **Agent** (Aggregate Root)
  - **Role** (Value Object)
  - **Action** (Value Object)
- Arquitectura:
  - Validación distribuida: cada agent valida sus propias capacidades
  - Lógica centralizada: Role + Action viven en el dominio, no en infraestructura
  - Self-contained: `agent.can_execute(action)` sin dependencias externas
- Roles: architect, qa, po, developer, devops
- Scopes: technical, business, quality, operations
- Sin servicios externos, sin reflection, frozen dataclasses

### ✅ Decision 4: Timeline
**Opción**: **B - Incremental ajustado con vista al MVP** ✅ CONFIRMADA
- **P0 (6 semanas)**: Features completas con scope optimizado para MVP
  - Planning Service (Python, hexagonal)
  - API Gateway (FastAPI, REST → gRPC + SSE)
  - PO UI adaptado (React + adaptaciones)
  - RBAC embedded en Agent
  - Task Derivation básico
  - Tests unitarios >90%
- **P1 (4 semanas)**: Enhancements y features avanzadas
  - Rehydration extendida
  - Ceremonias ágiles
  - UI mejorada
  - E2E tests exhaustivos
- **Total**: 10 semanas con enfoque MVP-first

### Interpretación A: Timeline Comprimido (Paralelización)
- **P0**: 3.5-4 semanas (vs 6)
- **Estrategia**: 2 developers trabajando en paralelo
- **Scope**: Completo (RBAC + Task Derivation + Planning + API Gateway + UI + E2E)
- **Calidad**: ✅ Coverage >90%, tests exhaustivos
- **Riesgo**: 🟢 Bajo (requiere 2 devs)

### Interpretación B: Scope Reducido
- **P0**: 3 semanas
- **Estrategia**: Features mínimas
- **Scope eliminado**: SSE live updates, DeliberationViewer completo, E2E exhaustivo
- **Calidad**: ⚠️ Coverage ~70-80%, UX degradada
- **Riesgo**: 🟡 Medio (deuda técnica incrementada)

### Interpretación C: Ambas (Compresión + Reducción)
- **P0**: 2 semanas
- **Estrategia**: Paralelización + scope mínimo
- **Scope**: Solo happy path, sin tests exhaustivos
- **Calidad**: ❌ Coverage <70%, bugs esperados
- **Riesgo**: 🔴 Alto (viola quality gate)

---

## 📋 Recomendación del Asistente

**Opción A** - Timeline Comprimido con Scope Completo

**Justificación**:
1. ✅ Mantiene quality gate (>80% coverage)
2. ✅ UX completa (SSE, live updates)
3. ✅ Arquitectura limpia (sin deuda técnica crítica)
4. ✅ E2E tests exhaustivos
5. ⚠️ Requiere 2 developers (asumible)
6. ✅ Balance óptimo velocidad/calidad

**Timeline detallado**:
- **Sprint 1** (1 sem): RBAC + Task Derivation
- **Sprint 2** (1.5 sem): Planning Service + API Gateway (paralelo)
- **Sprint 3** (1 sem): UI Adaptaciones + E2E Tests
- **TOTAL**: 3.5-4 semanas

---

## 📊 Comparativa de Opciones

| Aspecto | Opción A | Opción B | Opción C |
|---------|----------|----------|----------|
| **Timeline** | 3.5-4 sem | 3 sem | 2 sem |
| **Coverage** | >90% ✅ | ~75% ⚠️ | <70% ❌ |
| **UX** | Completa ✅ | Mínima ⚠️ | Básica ❌ |
| **SSE** | Sí ✅ | No ❌ | No ❌ |
| **E2E Tests** | Exhaustivos ✅ | Happy path ⚠️ | Básicos ❌ |
| **Deuda Técnica** | Baja ✅ | Media ⚠️ | Alta ❌ |
| **Recursos** | 2 devs | 1 dev | 2 devs |
| **Riesgo** | Bajo 🟢 | Medio 🟡 | Alto 🔴 |
| **Quality Gate** | Pass ✅ | Marginal ⚠️ | Fail ❌ |

---

## 🚀 Próximos Pasos

### Inmediato
1. ✅ **Confirmar Decision 4** (Arquitecto debe elegir A, B, o C)

### Una Vez Confirmado
2. Crear feature branches
3. Asignar recursos (1-2 developers)
4. Iniciar Sprint 1 (RBAC + Task Derivation)
5. Setup CI/CD para nuevos servicios (Planning, API Gateway)

---

## 📁 Documentos Generados

1. ✅ **ARCHITECTURAL_DECISIONS_2025-11-02.md** (32 KB)
   - Decisiones completas con justificación
   - Modelo DDD para RBAC
   - Análisis de UI rescatado
   - Gaps identificados

2. ✅ **IMPLEMENTATION_ROADMAP_2025-11-02.md** (18 KB)
   - Roadmap por sprints
   - Acceptance criteria detallados
   - 3 interpretaciones de "rápido"
   - Definition of Done

3. ✅ **DECISIONS_SUMMARY.md** (este documento)
   - Resumen ejecutivo
   - Comparativa de opciones
   - Recomendación clara

4. ✅ **UI Rescatado** (`ui/po-react/`)
   - Código fuente completo del commit c4fc4b5~
   - React 18.2 + TypeScript + Vite + Tailwind
   - Listo para adaptaciones

---

## 🚀 SIGUIENTE PASO: IMPLEMENTACIÓN

**Todas las decisiones confirmadas. Listo para comenzar.**

### Roadmap Ejecutable

**Sprint 1 (Semanas 1-2): Foundation**
- Planning Service (Python + gRPC)
- RBAC Domain Model (Agent + Role + Action)
- Tests unitarios >90%

**Sprint 2 (Semanas 3-4): Infrastructure**
- API Gateway (FastAPI)
- SSE Bridge (NATS → Server-Sent Events)
- REST → gRPC translation layer

**Sprint 3 (Semanas 5-6): Integration**
- PO UI adaptado (deliberation approval)
- Task Derivation básico
- E2E flow completo (create story → approve decision)

**Total P0**: 6 semanas
**Total P0+P1**: 10 semanas

---

**Documentación completa. Ready to code.** 🚀

