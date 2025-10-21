# 🔄 Propuesta: Renombrado de Directorios para Mayor Claridad

**Fecha**: 20 de Octubre de 2025  
**Estado**: 📝 PROPUESTA (NO EJECUTADA)  
**Objetivo**: Hacer OBVIO qué es CORE vs MICROSERVICIO

---

## 🎯 Problema Actual

La estructura actual causa confusión:

```
swe-ai-fleet/
├── src/swe_ai_fleet/           ← ¿Qué es esto? No es obvio que es CORE
│   ├── orchestrator/
│   ├── agents/
│   └── context/
│
└── services/                   ← OK, claramente microservicios
    ├── orchestrator/
    ├── context/
    └── ray-executor/
```

**Confusión**:
- No es obvio que `src/` es el CORE reutilizable
- Parece código "fuente" genérico
- No diferencia clara de responsabilidades

---

## ✅ Propuesta de Renombrado

### Opción 1: Renombrar `src/` a `core/`

```
swe-ai-fleet/
├── core/swe_ai_fleet/          ← 🔵 CLARÍSIMO: Lógica de negocio reutilizable
│   ├── orchestrator/           ← Core orchestration logic
│   ├── agents/                 ← Core agent implementations  
│   ├── context/                ← Core context logic
│   └── ray_jobs/               ← Core Ray job logic
│
└── services/                   ← 🟢 CLARÍSIMO: Microservicios gRPC/HTTP
    ├── orchestrator/           ← Orchestrator MS (Hexagonal)
    ├── context/                ← Context MS (Hexagonal)
    ├── ray-executor/           ← Ray Executor MS
    └── monitoring/             ← Monitoring Dashboard
```

**Ventajas**:
- ✅ **OBVIO** que `core/` es lógica de negocio
- ✅ **CLARA** separación de responsabilidades
- ✅ **INTUITIVO** para nuevos developers
- ✅ **ESTÁNDAR** en industria (muchos proyectos usan `core/`)

**Desventajas**:
- ⚠️ Requiere actualizar imports en ~200 archivos
- ⚠️ Requiere actualizar `pyproject.toml`
- ⚠️ Requiere actualizar Dockerfiles
- ⚠️ Breaking change para consumers del package

---

### Opción 2: Renombrar `src/` a `lib/`

```
swe-ai-fleet/
├── lib/swe_ai_fleet/           ← 🔵 Librería compartida
│   └── ...
└── services/                   ← 🟢 Microservicios
    └── ...
```

**Ventajas**:
- ✅ Común en Python (lib = library)
- ✅ Claro que es código compartido

**Desventajas**:
- ⚠️ Menos claro que `core/`
- ⚠️ Mismos cambios que Opción 1

---

### Opción 3: Agregar README.md en `src/`

**Mantener** `src/` pero agregar `src/README.md` clarificando:

```markdown
# SWE AI Fleet - Core Business Logic

This directory contains the **CORE business logic** of SWE AI Fleet.

## What is CORE?

- ✅ Reusable business logic
- ✅ Domain algorithms
- ✅ Pure Python (no infrastructure)
- ✅ Shared between microservices

## What is NOT here:

- ❌ gRPC servers (see `services/`)
- ❌ HTTP APIs (see `services/`)
- ❌ Event handlers (see `services/`)
- ❌ Database adapters (see `services/`)

## Structure:

- `orchestrator/` - Orchestration core logic
- `agents/` - Agent implementations
- `context/` - Context management logic
- `ray_jobs/` - Ray job execution logic
```

**Ventajas**:
- ✅ **SIN breaking changes**
- ✅ **Documentación clara**
- ✅ **Rápido de implementar**

**Desventajas**:
- ⚠️ Menos obvio que renombrar
- ⚠️ Depende de que developers lean README

---

## 📋 Cambios Requeridos (Opción 1: Renombrar a `core/`)

### 1. Renombrar directorio

```bash
git mv src core
```

### 2. Actualizar `pyproject.toml`

```toml
[project]
name = "swe-ai-fleet"

[tool.setuptools]
package-dir = {"" = "core"}  # ← Cambiar de "src" a "core"

[tool.setuptools.packages.find]
where = ["core"]             # ← Cambiar de "src" a "core"
```

### 3. Actualizar imports (~200 archivos)

```python
# ANTES:
from src.swe_ai_fleet.orchestrator import ...

# DESPUÉS:
from core.swe_ai_fleet.orchestrator import ...
```

**Archivos afectados**:
- `services/**/*.py` (~100 archivos)
- `tests/**/*.py` (~80 archivos)
- `scripts/**/*.py` (~20 archivos)

### 4. Actualizar Dockerfiles

```dockerfile
# ANTES:
COPY src/ /app/src/
ENV PYTHONPATH=/app/src:/app

# DESPUÉS:
COPY core/ /app/core/
ENV PYTHONPATH=/app/core:/app
```

**Archivos afectados**:
- `services/orchestrator/Dockerfile`
- `services/context/Dockerfile`
- `services/ray-executor/Dockerfile`
- `services/monitoring/Dockerfile`
- `jobs/*/Dockerfile`

### 5. Actualizar scripts de test

```bash
# scripts/ci-test-with-grpc-gen.sh
# Actualizar sys.path.insert si es necesario
```

---

## ⏱️ Estimación de Esfuerzo

| Tarea | Archivos | Tiempo Estimado |
|-------|----------|-----------------|
| **Renombrar directorio** | 1 comando | 1 minuto |
| **Actualizar pyproject.toml** | 1 archivo | 2 minutos |
| **Actualizar imports (find/replace)** | ~200 archivos | 10 minutos |
| **Actualizar Dockerfiles** | 8 archivos | 5 minutos |
| **Actualizar scripts** | 5 archivos | 3 minutos |
| **Testing completo** | All tests | 5 minutos |
| **Rebuild containers** | 5 images | 15 minutos |
| **Redeploy a K8s** | All services | 10 minutos |
| **Verificación E2E** | System test | 5 minutos |
| **TOTAL** | ~220 archivos | **~1 hora** |

---

## 🚦 Plan de Ejecución (Cuando se Decida)

### Paso 1: Preparación
```bash
# Crear branch para refactor
git checkout -b refactor/rename-src-to-core

# Backup (por si acaso)
git tag before-rename-to-core
```

### Paso 2: Renombrado
```bash
# Renombrar directorio
git mv src core

# Actualizar pyproject.toml
# (edit manual)
```

### Paso 3: Find & Replace
```bash
# Find all imports de "from src." y replace con "from core."
find . -name "*.py" -type f -exec sed -i 's/from src\./from core\./g' {} +

# Find all "sys.path.*src" y replace
find . -name "*.py" -type f -exec sed -i 's/sys\.path.*src/sys.path.insert(0, "core")/g' {} +
```

### Paso 4: Dockerfiles
```bash
# Find all COPY src/ y replace
find . -name "Dockerfile" -exec sed -i 's|COPY src/|COPY core/|g' {} +

# Find all PYTHONPATH.*src y replace  
find . -name "Dockerfile" -exec sed -i 's|/app/src:|/app/core:|g' {} +
```

### Paso 5: Testing
```bash
# Generar stubs y correr tests
make test-unit

# Verificar 611 tests passing
```

### Paso 6: Rebuild & Redeploy
```bash
# Rebuild todas las imágenes
# (usar script rebuild-and-deploy.sh)

# Redeploy a K8s
kubectl rollout restart deployment/orchestrator -n swe-ai-fleet
# ... (todos los deployments)
```

### Paso 7: Verificación
```bash
# E2E test
kubectl apply -f deploy/k8s/99-e2e-test-job.yaml

# Verificar logs
kubectl logs -n swe-ai-fleet -l app=e2e-test
```

---

## 💭 Decisión Pendiente

### Opción A: ✅ **RECOMENDADA** - Renombrar a `core/`
- **Pros**: Claridad máxima, estándar de industria
- **Cons**: 1 hora de trabajo, breaking change
- **Cuándo**: Cuando tengamos tiempo dedicado para refactor

### Opción B: ✅ **RÁPIDA** - Agregar README.md
- **Pros**: Sin breaking changes, implementación inmediata
- **Cons**: Menos obvio, depende de documentación
- **Cuándo**: AHORA (mientras planeamos Opción A)

### Opción C: ❌ **NO HACER NADA**
- **Pros**: Ninguno
- **Cons**: Confusión permanente
- **Cuándo**: Nunca

---

## 🎯 Recomendación Final

### Acción Inmediata (HOY):
📝 **Implementar Opción B** - Crear READMEs clarificadores:
- `src/README.md` - Explicando que es CORE
- `services/README.md` - Explicando que son MICROSERVICIOS
- `ARCHITECTURE_CORE_VS_MICROSERVICES.md` - Ya creado ✅

### Acción Futura (Próxima Iteración):
🔄 **Implementar Opción A** - Renombrar `src/` → `core/`
- Planificar sesión dedicada de 1-2 horas
- Hacer en branch separado
- Testing exhaustivo antes de merge

---

## ✅ Conclusión

**La confusión es real y válida.**

**El renombrado `src/` → `core/` haría TODO mucho más claro.**

**Pero NO es urgente** - podemos hacerlo en la próxima iteración después de que las deliberaciones funcionen.

**Prioridad AHORA**: 
1. 🔴 Fix planning_consumer auto-dispatch
2. 🔴 Testear deliberaciones end-to-end
3. 🟡 Luego refactor de directorios

**TODO apuntado para referencia futura!** 📝


