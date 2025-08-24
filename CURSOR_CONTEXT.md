# SWE AI Fleet - Contexto para Cursor

## 🎯 Descripción del Proyecto

**SWE AI Fleet** es un sistema multi-agente de código abierto para desarrollo de software e ingeniería de sistemas. Simula un equipo real de desarrollo con agentes LLM especializados (desarrolladores, devops, QA, arquitecto, data engineer) que trabajan de forma coordinada bajo supervisión humana.

## 🏗️ Arquitectura del Sistema

### Componentes Principales

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   UI/PO Humano  │───▶│   Orchestrator   │───▶│  Context        │
│                 │    │                  │    │  Assembler     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Agent Router   │    │  Prompt Scope   │
                       │                  │    │  Policy         │
                       └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  LLM Councils    │    │   Tools         │
                       │  (Dev, DevOps,   │───▶│   Gateway       │
                       │   QA, Arch,      │    │   (Sandbox)     │
                       │   Data)          │    │                 │
                       └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Memory Layer   │    │   Audit Log     │
                       │  Redis + Neo4j   │    │   (Streams)     │
                       └──────────────────┘    └─────────────────┘
```

### Capas de Memoria

1. **Redis (Tier-0)**: Memoria de trabajo efímera con TTL
   - Streams para eventos LLM
   - Cache para contexto frecuente
   - TTL automático para limpieza

2. **Neo4j (Tier-2)**: Grafo de decisiones y dependencias
   - Nodos: Decisions, Tasks, Dependencies, Milestones
   - Relaciones: DECIDES, DEPENDS_ON, IMPACTS, APPROVED_BY
   - Trazabilidad completa de casos de uso

## 📁 Estructura del Código

### Organización de Módulos

```
src/swe_ai_fleet/
├── __init__.py
├── cli/                    # Comandos de línea de comandos
├── context/               # Sistema de contexto inteligente
│   ├── adapters/         # Adaptadores para fuentes de datos
│   ├── domain/           # Modelos de dominio
│   ├── ports/            # Interfaces/Protocols
│   ├── context_assembler.py    # Ensamblador principal
│   ├── session_rehydration.py  # Rehidratación de sesiones
│   └── utils.py
├── memory/               # Sistema de memoria
│   ├── redis_store.py    # Store Redis implementado
│   ├── neo4j_store.py    # Store Neo4j (base)
│   ├── cataloger.py      # Catálogo de memoria
│   └── summarizer.py     # Resúmenes automáticos
├── models/               # Modelos de datos
├── orchestrator/         # Orquestación de agentes
│   ├── architect.py      # Agente arquitecto
│   ├── council.py        # Consejo de agentes
│   ├── router.py         # Enrutador de tareas
│   └── config.py         # Configuración
├── reports/              # Generación de informes
├── tools/                # Herramientas de ejecución
│   ├── kubectl_tool.py   # Herramienta kubectl
│   ├── helm_tool.py      # Herramienta Helm
│   ├── psql_tool.py      # Herramienta PostgreSQL
│   └── validators.py     # Validadores
└── evaluators/           # Evaluadores de calidad
```

## 🔧 Estado Actual de Implementación

### ✅ Completado (M0-M1)

- **Infraestructura**: Docker Compose para Redis + Neo4j
- **Memoria Redis**: `RedisStoreImpl` con Streams y TTL
- **Contexto**: `ContextAssembler` y `PromptScopePolicy`
- **Casos de uso**: Guardado de eventos LLM, rehidratación de sesiones
- **Testing**: Tests e2e para componentes principales

### 🚧 En Progreso (M2)

- **Optimización de contexto**: Compresión automática de sesiones largas
- **Redactor avanzado**: Para secretos y datos sensibles
- **Dashboard de contexto**: UI básica para monitoreo

### 📋 Próximo (M3-M4)

- **Sistema multi-agente**: Implementación completa de roles
- **Tool Gateway**: Ejecución segura de herramientas de desarrollo
- **Sandboxing**: Aislamiento de ejecuciones

## 🎨 Patrones de Diseño y Convenciones

### Arquitectura Limpia

- **Ports/Adapters**: Interfaces claras entre capas
- **Protocols**: Uso de `typing.Protocol` para contratos
- **DTOs**: Objetos de transferencia inmutables
- **Use Cases**: Lógica de negocio encapsulada

### Convenciones de Código

- **Python 3.13+**: Uso de features modernas
- **Type hints**: Completos en todo el código
- **Dataclasses**: Para estructuras de datos simples
- **Async/await**: Para operaciones I/O intensivas
- **Ruff**: Linter y formateador configurado

### Estructura de Tests

```
tests/
├── unit/           # Tests unitarios
├── integration/    # Tests de integración
└── e2e/           # Tests end-to-end
    ├── test_redis_store_e2e.py
    ├── test_context_assembler_e2e.py
    ├── test_session_rehydration_e2e.py
    └── test_decision_enriched_report_e2e.py
```

## 🚀 Guías de Desarrollo

### Agregando Nuevas Funcionalidades

1. **Definir el Protocol/Port** en el módulo correspondiente
2. **Implementar la funcionalidad** siguiendo patrones existentes
3. **Agregar tests** unitarios e integración
4. **Actualizar documentación** y casos de uso

### Ejemplo: Agregar Nueva Herramienta

```python
# 1. Definir el protocolo
class TerraformTool(Protocol):
    def validate_config(self, config_path: str) -> tuple[bool, str]: ...
    def plan_changes(self, config_path: str) -> tuple[bool, str]: ...

# 2. Implementar
class TerraformToolImpl:
    def validate_config(self, config_path: str) -> tuple[bool, str]:
        # Implementación con subprocess
        pass

# 3. Agregar a la configuración de roles
TERRAFORM_ALLOWLIST = ["terraform", "tf"]
```

### Manejo de Errores

- **Excepciones específicas**: Crear excepciones de dominio cuando sea necesario
- **Logging estructurado**: Usar logging con contexto
- **Fallbacks**: Implementar estrategias de fallback para operaciones críticas

## 🔒 Seguridad y Aislamiento

### Principios de Seguridad

1. **Principio de menor privilegio**: Cada agente solo accede a lo necesario
2. **Sandboxing**: Ejecución aislada de herramientas
3. **Auditoría completa**: Log de todas las operaciones
4. **Redacción de secretos**: Eliminación automática de datos sensibles

### Control de Acceso

- **RBAC por rol**: Diferentes permisos según el rol del agente
- **Scope policies**: Control granular del contexto disponible
- **Tool allowlists**: Listas blancas de comandos permitidos por rol

## 📊 Monitoreo y Observabilidad

### Métricas Clave

- **Tiempo de respuesta**: Para consultas de contexto
- **Compresión de contexto**: Eficiencia de la minimización
- **Uso de memoria**: Redis y Neo4j
- **Trazabilidad**: Cobertura de eventos auditados

### Logging

- **Structured logging**: JSON con contexto estructurado
- **Correlation IDs**: Para rastrear flujos completos
- **Log levels**: Configurables por componente

## 🧪 Testing y Calidad

### Estrategia de Testing

- **Tests unitarios**: Para lógica de negocio
- **Tests de integración**: Para adaptadores y servicios
- **Tests e2e**: Para flujos completos
- **Tests de performance**: Para operaciones críticas

### Cobertura Objetivo

- **Cobertura de código**: > 90%
- **Cobertura de casos de uso**: 100%
- **Tests de regresión**: Automatizados en CI/CD

## 🚀 Despliegue y Operaciones

### Entorno Local (Mac M2)

```bash
# Levantar infraestructura
make redis-up

# Ejecutar tests
make test-e2e

# Desarrollo
source scripts/dev.sh
```

### Entorno de Producción

- **Kubernetes**: Con Ray/KubeRay para escalabilidad
- **Helm charts**: Para despliegue automatizado
- **Monitoring**: Prometheus + Grafana
- **Logging**: Centralizado con ELK stack

## 📚 Recursos y Referencias

### Documentación

- **README.md**: Visión general del proyecto
- **ROADMAP.md**: Roadmap básico
- **ROADMAP_DETAILED.md**: Roadmap detallado (este documento)
- **docs/**: Documentación técnica detallada

### Casos de Uso

1. **Guardar eventos LLM**: Persistencia en Redis
2. **Rehidratación de sesiones**: Recuperación de contexto
3. **Generación de informes**: Desde grafo Neo4j
4. **Sprint Planning**: Generación automática de subtareas

### Herramientas de Desarrollo

- **Makefile**: Comandos de orquestación
- **Docker Compose**: Infraestructura local
- **Helm**: Charts para Kubernetes
- **GitHub Actions**: CI/CD pipeline

## 🎯 Próximos Pasos para Cursor

### Prioridades Inmediatas

1. **Completar M2**: Contexto y minimización
2. **Iniciar M4**: Implementación del Tool Gateway
3. **Optimizar consultas**: Neo4j para dependencias críticas
4. **Mejorar testing**: Cobertura y casos edge

### Áreas de Enfoque

- **Performance**: Optimización de consultas y cache
- **Seguridad**: Sandboxing y control de acceso
- **Testing**: Automatización y cobertura
- **Documentación**: Guías de uso y contribución

### Integración con Herramientas

- **LLMs locales**: Qwen, Llama, Mistral
- **Herramientas de desarrollo**: Git, Docker, kubectl
- **Testing frameworks**: pytest, JUnit, Go test
- **CI/CD**: GitHub Actions, GitLab CI

---

**Nota**: Este documento se actualiza regularmente. Para la información más reciente, consulta el código fuente y los issues de GitHub.