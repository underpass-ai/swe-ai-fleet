# SWE AI Fleet - Roadmap Detallado

## 🎯 Visión del Proyecto

Construir una flota de agentes LLM especializados en ingeniería de software que simule un equipo humano real (desarrolladores, devops, QA, arquitecto, data engineer). Los agentes trabajan de forma coordinada, con contexto atómico por caso de uso, y con el humano como Product Owner (PO) que supervisa y aprueba.

**Diferenciales clave:**
- **Trazabilidad total** de decisiones y ejecuciones
- **Persistencia inteligente** en Redis (corto plazo) y Neo4j (largo plazo/grafo)
- **Contexto mínimo garantizado** para cada rol y subtarea
- **Simulación de procesos reales** de ingeniería de software
- **Ejecución de útiles** con sandboxing y auditoría completa

## 🚀 Estado Actual (M0-M1 Completado)

### ✅ Infraestructura Básica
- [x] Docker Compose para Redis + Neo4j
- [x] Makefile unificado para orquestación
- [x] Smoke test e2e validado (kg_smoke.py → neo4j_writer)
- [x] CI/CD inicial (GitHub Actions)
- [x] Helm charts para Kubernetes

### ✅ Sistema de Memoria
- [x] `RedisStoreImpl` para llamadas/respuestas LLM
- [x] TTL + Streams para persistencia efímera
- [x] `Neo4jDecisionGraphAdapter` con DTOs y constraints
- [x] Sincronización parcial Redis → Neo4j

### ✅ Contexto Inteligente
- [x] Contexto atómico por caso de uso
- [x] `PromptScopePolicy`: filtrado de info por rol
- [x] `ContextAssembler`: empaquetado para cada agente
- [x] Matriz de scopes por rol y fase (YAML configurable)

### ✅ Casos de Uso Implementados
- [x] Guardar llamadas y respuestas LLM (Redis)
- [x] Generar informe técnico de un caso de uso
- [x] Continuar un proyecto en curso (rehidratación de contexto)
- [x] Refinamiento de tarea / Sprint Planning

## 🎯 Roadmap de Milestones

### M2 - Contexto y Minimización (En Progreso)
**Objetivo:** Completar el sistema de contexto inteligente y optimización de memoria

#### Tareas Prioritarias
- [ ] **Compresión automática** de sesiones largas
- [ ] **Dashboard de contexto vivo** (UI básica)
- [ ] **Redactor avanzado** para secretos y datos sensibles
- [ ] **Optimización de consultas** Neo4j para dependencias críticas
- [ ] **Cache inteligente** para consultas frecuentes

#### Entregables
- Sistema de compresión de contexto automático
- UI básica para monitoreo de contexto
- Redactor configurable para diferentes tipos de datos sensibles
- Consultas optimizadas para análisis de dependencias

### M3 - Agentes y Roles (Próximo)
**Objetivo:** Implementar el sistema multi-agente con roles especializados

#### Tareas Prioritarias
- [ ] **Definición completa de roles**: Dev, DevOps, QA, Architect, Data
- [ ] **Multi-agentes por rol** con consulta interna (consenso)
- [ ] **PO humano como supervisor/decisor**
- [ ] **Simulación de Sprint Planning** → subtareas generadas automáticamente
- [ ] **Sistema de permisos** por rol y fase

#### Entregables
- Implementación completa de todos los roles
- Sistema de consenso entre agentes del mismo rol
- Interfaz para el PO humano
- Generador automático de subtareas

### M4 - Ejecución de Útiles (Crítico)
**Objetivo:** Implementar la infraestructura para ejecutar herramientas de desarrollo

#### Tareas Prioritarias
- [ ] **Tool Gateway** (HTTP/gRPC) con FastAPI
- [ ] **Sandbox de ejecución** para bash/python/go/js
- [ ] **Útiles de infraestructura**: kubectl, docker, psql, redis-cli
- [ ] **Ejecución de tests** (pytest, JUnit, Go test)
- [ ] **Control de permisos** y auditoría de ejecuciones

#### Entregables
- Tool Gateway completamente funcional
- Sistema de sandboxing seguro
- Integración con herramientas de desarrollo
- Sistema de auditoría completo

#### Arquitectura de Útiles
```
Tool Gateway (FastAPI) → Policy Engine → Sandbox Executor → Audit Log
     ↓
Redis Streams → Neo4j (trazabilidad completa)
```

#### Seguridad y Aislamiento
- Contenedores efímeros rootless
- Red de salida bloqueada por defecto
- Límites de CPU/Mem/PIDs
- Auditoría de cada ejecución

### M5 - Flujo E2E Simulado
**Objetivo:** Caso de uso completo end-to-end

#### Tareas Prioritarias
- [ ] **Flujo completo**: Diseño → Decisiones → Implementación → Test → Informe
- [ ] **Generación de informe técnico** desde grafo Neo4j
- [ ] **Continuación de proyectos previos** (rehidratación de contexto)
- [ ] **Trazabilidad total** (quién decidió qué y cuándo)
- [ ] **Métricas de calidad** y rendimiento

#### Entregables
- Pipeline completo de desarrollo
- Sistema de informes automáticos
- Métricas de rendimiento y calidad
- Documentación de casos de uso

### M6 - Comunidad y Open Source
**Objetivo:** Preparar el proyecto para la comunidad

#### Tareas Prioritarias
- [ ] **Landing page** (Next.js + Tailwind)
- [ ] **Documentación clara** y ejemplos de casos de uso
- [ ] **Guía para extender** con nuevos útiles
- [ ] **Publicación en GitHub** + difusión en foros OSS
- [ ] **Sistema de contribuciones** y governance

#### Entregables
- Landing page profesional
- Documentación completa
- Guías de contribución
- Comunidad activa

## 🔧 Implementación Técnica

### Stack Tecnológico
- **Backend**: Python 3.13+, FastAPI, Redis, Neo4j
- **Infraestructura**: Docker Compose (local), Kubernetes + Ray/KubeRay (producción)
- **Frontend**: Next.js + Tailwind (M6)
- **Testing**: pytest, e2e tests
- **CI/CD**: GitHub Actions

### Arquitectura de Componentes
```
UI/PO → Orchestrator → Context Assembler → Agents → Tools → Memory (Redis + Neo4j)
```

### Patrones de Diseño
- **Clean Architecture** con ports/adapters
- **Event Sourcing** con Redis Streams
- **CQRS** para consultas complejas
- **Policy-based** para control de acceso
- **Sandbox pattern** para ejecución segura

## 📊 Métricas de Éxito

### Técnicas
- [ ] **Tiempo de respuesta** < 2s para consultas de contexto
- [ ] **Compresión de contexto** > 60% para sesiones largas
- [ ] **Cobertura de tests** > 90%
- [ ] **Trazabilidad** 100% de decisiones y ejecuciones

### Funcionales
- [ ] **Casos de uso completos** implementados y funcionando
- [ ] **Integración con herramientas** de desarrollo reales
- [ ] **Sistema multi-agente** coordinado y eficiente
- [ ] **Documentación** clara y completa

## 🚨 Riesgos y Mitigaciones

### Riesgos Técnicos
- **Complejidad del grafo Neo4j**: Implementar consultas optimizadas y cache
- **Seguridad de útiles**: Sandboxing estricto y auditoría completa
- **Performance**: Monitoreo continuo y optimizaciones incrementales

### Riesgos de Proyecto
- **Scope creep**: Mantener foco en M4 (útiles) como prioridad
- **Dependencias externas**: Plan de contingencia para LLMs y herramientas
- **Comunidad**: Iniciar engagement temprano en M3-M4

## 🎯 Próximos Pasos Inmediatos

1. **Completar M2** (Contexto y Minimización)
2. **Iniciar M4** (Ejecución de Útiles) - **CRÍTICO**
3. **Preparar arquitectura** para M3 (Agentes y Roles)
4. **Validar casos de uso** existentes
5. **Optimizar consultas** Neo4j

## 📝 Notas de Implementación

### Prioridad Crítica: M4 (Útiles)
El salto de M3 a M4 es fundamental porque transforma el sistema de "hablar y razonar" a "ejecutar, validar y aprender" de forma autónoma, cerrando el ciclo completo de ingeniería de software real.

### Integración con Herramientas Existentes
- **kubectl_tool.py**: Base para herramientas de infraestructura
- **helm_tool.py**: Integración con Helm
- **psql_tool.py**: Herramientas de base de datos
- **validators.py**: Validación de herramientas

### Extensibilidad
El sistema está diseñado para ser extensible:
- Nuevos roles mediante configuración YAML
- Nuevas herramientas mediante el sistema de útiles
- Nuevos tipos de memoria mediante adaptadores
- Nuevos casos de uso mediante el orquestador