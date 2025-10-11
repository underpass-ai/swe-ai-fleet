# Documentation Standards - SWE AI Fleet

> **La documentación es TAN importante como el código.**

Este es un proyecto open-source de estado del arte en sistemas multi-agente que aspira a conseguir financiación e impactar en la comunidad. La documentación es nuestra **primera impresión** ante inversores, desarrolladores y usuarios.

---

## 🎯 Filosofía

La documentación debe ser:
- **Sencilla**: Cualquiera puede empezar en 5 minutos
- **Útil**: Resuelve problemas reales con ejemplos funcionales
- **Precisa**: Comandos verificados, versiones exactas, referencias correctas
- **Completa**: Si alguien quiere profundizar, puede hacerlo infinitamente

---

## 👥 Tres Audiencias, Tres Niveles

### 1. Ejecutivos e Inversores 💼

**Objetivo:** Entender el valor en 30 segundos, profundizar en 10 minutos

**Documentos clave:**
- `INVESTORS.md` - Propuesta de valor, mercado, diferenciación
- `VISION.md` - Visión del proyecto, roadmap estratégico
- `README.md` (sección hero) - Qué es, por qué importa
- `docs/USE_CASES.md` - Casos de uso del mundo real

**Requisitos:**
- ✅ Lenguaje business-friendly (no solo técnico)
- ✅ Métricas y comparaciones con competencia
- ✅ Roadmap claro con milestones
- ✅ ROI y beneficios cuantificables
- ❌ Sin jerga técnica innecesaria
- ❌ Sin TODOs o disclaimers que resten confianza

---

### 2. Desarrolladores 👨‍💻

**Objetivo:** Onboarding en <30 minutos, productivo en <2 horas

**Documentos clave:**
- `docs/getting-started/` - Quick start paso a paso
- `docs/architecture/` - Diseño del sistema, decisiones técnicas
- `services/*/README.md` - APIs, configuración, troubleshooting
- `CONTRIBUTING.md` - Cómo contribuir al proyecto
- `docs/DEVELOPMENT_GUIDE.md` - Setup local, testing, CI/CD

**Requisitos:**
- ✅ Quick start funcional (copy-paste ready)
- ✅ Ejemplos de código completos y verificados
- ✅ Comandos exactos con outputs esperados
- ✅ Troubleshooting de errores comunes
- ✅ Diagramas de arquitectura claros
- ✅ Referencias cruzadas entre documentos
- ❌ Sin comandos que no funcionen
- ❌ Sin referencias a archivos inexistentes

---

### 3. Usuarios Finales 🚀

**Objetivo:** Desplegar en producción en <1 hora, resolver 80% de problemas solos

**Documentos clave:**
- `README.md` - Overview y quick deploy
- `docs/getting-started/quickstart.md` - Deploy en 5 minutos
- `docs/operations/` - Monitoring, troubleshooting, updates
- `deploy/k8s/*/README.md` - Deployment guides específicos

**Requisitos:**
- ✅ Scripts automatizados (deploy-*.sh)
- ✅ Prerequisites claros (hardware, software)
- ✅ Verificación post-deploy
- ✅ Troubleshooting exhaustivo
- ✅ Comandos de rollback
- ❌ Sin asumir conocimiento avanzado
- ❌ Sin pasos ambiguos

---

## 📐 Principios de Calidad

### 1. Meticulosidad Extrema

Cada documento debe ser **impecable**:

#### ✅ SIEMPRE:
- Actualizar docs cuando cambies código (mismo PR)
- Verificar que archivos referenciados existen
- Probar comandos antes de documentarlos
- Usar versiones exactas (Python 3.13, NO 3.11+)
- Usar nombres correctos (swe-ai-fleet, NO swe)
- Usar URLs reales (underpassai.com, NO yourdomain.com)
- Incluir outputs esperados de comandos
- Cross-referenciar documentos relacionados

#### ❌ NUNCA:
- Dejar TODOs sin resolver en docs públicos
- Usar placeholders genéricos (localhost, yourserver, etc.)
- Referencias a archivos que no existen
- Comandos no verificados
- Versiones "aproximadas" (3.x, latest, etc.)
- Copiar/pegar sin adaptar al proyecto
- Documentos "WIP" en main branch

---

### 2. Estructura Pirámide Invertida

Cada documento debe seguir esta estructura:

```markdown
# [Título Claro]

## [Primer Párrafo - 30 segundos]
Qué hace, por qué existe, cuál es su propósito.

## Quick Start [5 minutos]
Comandos copy-paste que FUNCIONAN para el caso más común.

## Conceptos [10 minutos]
Explicación de cómo funciona internamente.

## Referencia Completa [profundidad infinita]
Todos los detalles técnicos, opciones avanzadas, edge cases.

## Troubleshooting
Errores comunes y cómo resolverlos.

## Referencias
Links a documentos relacionados.
```

**Ejemplo Real:**
- `services/context/README.md` (sigue este patrón ✅)
- `deploy/k8s/CONTEXT_DEPLOYMENT.md` (sigue este patrón ✅)

---

### 3. Precisión Técnica

#### Versiones
```markdown
❌ Python 3.11+       (vago, no verificable)
✅ Python 3.13        (exacto, verificable)

❌ Kubernetes 1.x     (demasiado amplio)
✅ Kubernetes 1.28+   (rango específico validado)
```

#### Comandos
```markdown
❌ kubectl get pods
✅ kubectl get pods -n swe-ai-fleet -l app=context

❌ docker build .
✅ podman build -t registry.underpassai.com/swe-fleet/context:v0.3.0 -f services/context/Dockerfile .
```

#### URLs
```markdown
❌ https://myapp.example.com
❌ https://app.yourdomain.com
✅ https://swe-fleet.underpassai.com

❌ localhost:8080
✅ kubectl port-forward -n swe-ai-fleet svc/context 50054:50054
   # Then: localhost:50054
```

#### Nombres de Archivos
```markdown
❌ "the context service yaml"
✅ deploy/k8s/08-context-service.yaml

❌ context.proto
✅ specs/context.proto
```

---

### 4. Ejemplos Funcionales

Todos los ejemplos deben ser **copy-paste ready**:

#### ✅ Buen Ejemplo:
```bash
# Deploy Context Service to Kubernetes
cd /path/to/swe-ai-fleet
kubectl apply -f deploy/k8s/07-neo4j-secret.yaml
kubectl apply -f deploy/k8s/09-neo4j.yaml
kubectl apply -f deploy/k8s/10-valkey.yaml
kubectl apply -f deploy/k8s/08-context-service.yaml

# Verify deployment
kubectl get pods -n swe-ai-fleet -l app=context
# Expected output:
# NAME                       READY   STATUS    RESTARTS   AGE
# context-7d9f8b6c5d-abcde   1/1     Running   0          30s
```

#### ❌ Mal Ejemplo:
```bash
# Deploy the service
kubectl apply -f <your-manifest>

# Check status
kubectl get pods
```

---

### 5. Mantenimiento Continuo

#### Due Diligence Periódica (Cada 2-3 meses o antes de major releases)

**Checklist:**
- [ ] Buscar TODOs sin resolver: `grep -r "TODO" --include="*.md" docs/`
- [ ] Verificar referencias a archivos: Script de audit
- [ ] Verificar versiones mencionadas: ¿Son actuales?
- [ ] Probar comandos quick start: ¿Funcionan?
- [ ] Revisar screenshots/diagramas: ¿Actualizados?
- [ ] Buscar docs obsoletos: ¿Branches mergeados?
- [ ] Verificar URLs: ¿Siguen funcionando?

**Ejemplo Reciente:**
- Due diligence 2025-10-11: 7 archivos obsoletos eliminados, 13 actualizados
- Ver: `DOCUMENTATION_DUE_DILIGENCE.md`

---

## 🚩 Red Flags - Indicadores de Problemas

### Nivel 1 - Crítico (Arreglar INMEDIATAMENTE)
- 🚨 Referencias a archivos eliminados
- 🚨 Comandos con namespace incorrecto
- 🚨 TODOs en docs de `README.md` o `docs/getting-started/`
- 🚨 URLs placeholder en documentación pública
- 🚨 Ejemplos que no funcionan

### Nivel 2 - Importante (Arreglar en <1 semana)
- ⚠️ Versiones inconsistentes entre documentos
- ⚠️ Links internos rotos
- ⚠️ Docs sin ejemplos funcionales
- ⚠️ Falta troubleshooting section
- ⚠️ Comandos sin outputs esperados

### Nivel 3 - Mantenimiento (Arreglar en próximo sprint)
- 🔸 Docs de >3 meses sin actualizar
- 🔸 Falta cross-references
- 🔸 Diagramas desactualizados
- 🔸 Falta información de versiones

---

## ✅ Checklist para Crear/Modificar Docs

Antes de commitear cualquier cambio de documentación:

### Contenido
- [ ] ¿El primer párrafo explica QUÉ hace y POR QUÉ existe? (30s)
- [ ] ¿Tiene una sección "Quick Start" funcional? (5min)
- [ ] ¿Los ejemplos son copy-paste ready?
- [ ] ¿Incluye troubleshooting de errores comunes?

### Referencias
- [ ] ¿Todas las referencias a archivos existen?
- [ ] ¿Los comandos usan el namespace correcto? (swe-ai-fleet)
- [ ] ¿Las versiones son exactas? (Python 3.13, NO 3.11+)
- [ ] ¿Las URLs son reales? (underpassai.com, NO placeholders)

### Navegación
- [ ] ¿Tiene enlaces a documentación relacionada?
- [ ] ¿Está referenciado desde INDEX.md o READMEs padres?
- [ ] ¿Los links internos funcionan?

### Audiencia
- [ ] ¿Es apropiado para la audiencia target?
- [ ] ¿El nivel técnico es consistente?
- [ ] ¿Hay contexto suficiente para nuevos usuarios?

### Calidad
- [ ] ¿Sin TODOs sin resolver?
- [ ] ¿Sin typos obvios?
- [ ] ¿Formato markdown correcto?
- [ ] ¿Código con syntax highlighting correcto?

---

## 📊 Métricas de Calidad

### Documentación Excelente (Target)
- ✅ 100% de comandos verificados funcionan
- ✅ 0 referencias a archivos inexistentes
- ✅ 0 TODOs en documentación pública
- ✅ 0 placeholders (yourdomain, localhost sin contexto)
- ✅ <30 días desde última actualización en docs críticos
- ✅ >80% de usuarios resuelven problemas sin soporte directo

### Documentación Aceptable (Mínimo)
- ⚠️ 90% de comandos verificados funcionan
- ⚠️ <3 referencias rotas
- ⚠️ <5 TODOs documentados con issues
- ⚠️ <2 placeholders genéricos
- ⚠️ <90 días desde última actualización
- ⚠️ >60% de usuarios pueden hacer deploy solos

### Documentación Inaceptable (Requiere Acción)
- 🚫 <80% de comandos funcionan
- 🚫 >5 referencias rotas
- 🚫 >10 TODOs sin resolver
- 🚫 >5 placeholders genéricos
- 🚫 >6 meses sin actualizar
- 🚫 <50% de usuarios exitosos sin soporte

---

## 🛠️ Herramientas y Automatización

### Scripts de Audit
```bash
# Buscar TODOs en docs
grep -r "TODO" --include="*.md" docs/

# Buscar placeholders
grep -r "yourdomain\|localhost\|example\.com" --include="*.md" docs/

# Buscar versiones inconsistentes
grep -r "Python 3\.[0-9]" --include="*.md" docs/

# Buscar namespace antiguo
grep -r "namespace.*swe[^-]" --include="*.md" --include="*.yaml" .
```

### Futuras Mejoras (Consideradas)
- [ ] Automated link checking en CI
- [ ] Documentation version en releases
- [ ] Spell checker en CI
- [ ] Auto-generate API docs from protobuf
- [ ] Documentation coverage metrics

---

## 📚 Jerarquía de Documentación

### Root Level (Máxima Visibilidad)
```
README.md               ← Hero, quick start, key links
VISION.md              ← Project vision y strategic goals
INVESTORS.md           ← Investment opportunity y market
CONTRIBUTING.md        ← How to contribute
LICENSE                ← Apache 2.0
SECURITY.md            ← Security policy
GOVERNANCE.md          ← Project governance
```

### docs/ (Documentación Organizada)
```
docs/
├── getting-started/   ← Nuevos usuarios (quick wins)
├── architecture/      ← Diseño del sistema (para entender)
├── infrastructure/    ← Setup de infra (K8s, CRI-O, GPU)
├── operations/        ← Deploy, monitoring, troubleshooting
├── reference/         ← Glossary, FAQ, RFCs, ADRs
└── microservices/     ← Docs específicos de servicios
```

### services/ (Documentación Técnica)
```
services/
├── context/
│   ├── README.md                  ← API, quick start, config
│   ├── USE_CASES_ANALYSIS.md      ← Internal architecture
│   ├── ROADMAP.md                 ← Service evolution
│   └── INTEGRATION_ROADMAP.md     ← Pending work
└── orchestrator/
    └── README.md                  ← API, quick start, config
```

### deploy/ (Deployment Docs)
```
deploy/k8s/
├── README.md                      ← Overview de manifests
├── CONTEXT_DEPLOYMENT.md          ← Context + Neo4j + Valkey
└── SONARQUBE_NOTES.md             ← Config específica de tooling
```

---

## 🎨 Templates y Ejemplos

### Template: Service README

```markdown
# [Service Name]

[One sentence: what this service does]

## 🎯 Purpose

[2-3 sentences explaining WHY this service exists and its role in the system]

## 🏗️ Architecture

- **Protocol**: [gRPC/HTTP/etc.] (port X)
- **Language**: Python 3.13
- **Storage**: [Databases/caches used]
- **Pattern**: [DDD/Clean Architecture/etc.]

## 🚀 Quick Start

### Deploy to Kubernetes
```bash
kubectl apply -f deploy/k8s/XX-service.yaml
kubectl get pods -n swe-ai-fleet -l app=service
```

## 📡 API Reference

[Métodos principales con ejemplos]

## 🔧 Configuration

[Env vars y opciones]

## 🧪 Testing

[Comandos para ejecutar tests]

## 🔍 Troubleshooting

[Errores comunes y soluciones]

## 📚 Related Documentation

- [Link to related doc 1]
- [Link to related doc 2]
```

### Template: Architecture Document

```markdown
# [Feature/System] Architecture

## Executive Summary

[3-4 líneas: qué es, por qué importa, estado actual]

## Problem Statement

[Qué problema resuelve este diseño]

## Design Goals

- Goal 1
- Goal 2
- Goal 3

## Architecture

[Diagrams, component descriptions]

## Design Decisions

### Decision 1: [Title]
- **Context**: [Why we faced this decision]
- **Options**: [Alternatives considered]
- **Decision**: [What we chose]
- **Rationale**: [Why we chose it]
- **Trade-offs**: [What we sacrificed]

## Implementation

[How it's implemented, with code refs]

## Testing Strategy

[How we verify it works]

## Future Work

[What's missing, future improvements]

## References

- [Related docs]
- [External resources]
```

---

## 🔄 Workflow de Documentación

### Cuando Creas Código Nuevo

```
1. ✅ Escribir el código
2. ✅ Escribir los tests
3. ✅ Escribir/actualizar README del servicio
4. ✅ Actualizar docs/architecture/ si cambia diseño
5. ✅ Actualizar INDEX.md si es documento nuevo
6. ✅ Cross-referenciar desde docs relacionados
7. ✅ Commit: code + tests + docs en mismo PR
```

### Cuando Modificas APIs

```
1. ✅ Actualizar .proto file
2. ✅ Regenerar código
3. ✅ Actualizar server implementation
4. ✅ Actualizar tests
5. ✅ Actualizar services/*/README.md (API section)
6. ✅ Actualizar ejemplos en getting-started/
7. ✅ Nota en CHANGELOG
```

### Cuando Haces Refactoring

```
1. ✅ Identificar docs afectados
2. ✅ Actualizar referencias de archivos movidos/renombrados
3. ✅ Actualizar imports en ejemplos de código
4. ✅ Verificar que comandos siguen funcionando
5. ✅ Commit: "refactor(X): ... + docs updated"
```

### Antes de Cada Release

```
1. ✅ Ejecutar due diligence completa (ver DOCUMENTATION_DUE_DILIGENCE.md)
2. ✅ Verificar TODOs: deben estar resueltos o documentados como issues
3. ✅ Probar quick starts en máquina limpia
4. ✅ Actualizar versiones en todos los docs
5. ✅ Generar/actualizar CHANGELOG
6. ✅ Review de inversores: ¿INVESTORS.md actualizado?
```

---

## 🎓 Ejemplos de Documentación Excelente en Este Proyecto

### ✅ Ejemplos a Seguir

1. **services/context/USE_CASES_ANALYSIS.md**
   - ✅ Executive summary claro
   - ✅ Diagramas de flujo completos
   - ✅ Código de ejemplo funcional
   - ✅ Cross-references extensas
   - ✅ Arquitectura en capas bien explicada

2. **deploy/k8s/CONTEXT_DEPLOYMENT.md**
   - ✅ Quick start AND manual steps
   - ✅ Troubleshooting exhaustivo
   - ✅ Verificación post-deploy
   - ✅ Comandos exactos con namespace correcto
   - ✅ Scripts automatizados disponibles

3. **docs/TESTING_STRATEGY.md**
   - ✅ Pirámide de tests explicada
   - ✅ Ejemplos de código completos
   - ✅ Comandos de ejecución verificados
   - ✅ Objetivos claros por nivel de test

4. **docs/architecture/NATS_CONSUMERS_DESIGN.md**
   - ✅ Diseño completo de streams
   - ✅ Ejemplos en Python y potencialmente Go
   - ✅ Políticas de retención documentadas
   - ✅ Consumer patterns explicados

---

## 🌟 Impact: Por Qué Esto Importa

### Para Inversores
- Documentación profesional = proyecto serio
- Docs claros = riesgo de adopción reducido
- Architecture docs = equipo competente visible

### Para la Comunidad OSS
- Quick start funcional = primeras contribuciones rápidas
- Troubleshooting completo = menos frustración
- Arquitectura documentada = más contribuciones de calidad

### Para el Proyecto
- Onboarding rápido = escalabilidad del equipo
- Docs actualizados = menos deuda técnica
- Precisión = menos bugs y malentendidos

---

## 📞 Contacto y Contribuciones

Si encuentras documentación desactualizada, incompleta o incorrecta:

1. **Inmediato**: Crea issue en GitHub con label `documentation`
2. **Mejor**: Crea PR con la corrección (siguiendo estos estándares)
3. **Critico**: Email a contact@underpassai.com si afecta adoption

**Recuerda:** Mejorar la documentación es TAN valioso como mejorar el código.

---

## 📖 Referencias

- [Documentation Due Diligence Report](DOCUMENTATION_DUE_DILIGENCE.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Documentation Index](docs/INDEX.md)
- [Investors Deck](docs/INVESTORS.md)

---

**Última actualización:** 2025-10-11  
**Próxima review:** 2026-01-11 (3 meses)  
**Responsable:** Mantainers y contributors

