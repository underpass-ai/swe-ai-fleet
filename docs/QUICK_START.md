# Quick Start Guide - SWE AI Fleet

## 🚀 Comandos Rápidos

### Generar Protobuf Files

Para generar los archivos protobuf necesarios para tests y desarrollo:

```bash
# Opción 1: Usando Makefile (recomendado)
make generate-protos

# Opción 2: Usando script directo
./scripts/generate-protos.sh

# Opción 3: Desde scripts de test (automático)
make test-unit  # Genera protos automáticamente antes de tests
```

**Nota:** Los archivos generados están en `services/*/gen/` y NO se commitean a git.

### Limpiar Protobuf Files

```bash
make clean-protos
```

---

## 🧪 Testing

### Ejecutar Tests Unitarios

```bash
# Ejecutar todos los tests unitarios (genera protos automáticamente)
make test-unit

# O directamente con pytest (requiere protos generados primero)
make generate-protos
pytest services/planning/tests/unit/ -v

# Tests específicos
pytest services/planning/tests/unit/infrastructure/test_task_valkey_mapper.py -v
```

### Ejecutar Tests de un Servicio Específico

```bash
# Planning Service
pytest services/planning/tests/unit/ -v

# Con cobertura
pytest services/planning/tests/unit/ --cov=planning --cov-report=html
```

---

## 🚢 Deployment

### Desplegar un Servicio Específico

```bash
# Ver servicios disponibles
make list-services

# Desplegar planning service (rápido, con cache)
make deploy-service-fast SERVICE=planning

# Desplegar planning service (fresh, sin cache)
make deploy-service SERVICE=planning

# Desplegar todos los servicios
make fast-redeploy
```

### Ejemplos de Deployment

```bash
# Planning Service
make deploy-service-fast SERVICE=planning

# Task Derivation Service
make deploy-service-fast SERVICE=task_derivation

# Orchestrator Service
make deploy-service-fast SERVICE=orchestrator
```

---

## 📦 Instalación de Dependencias

```bash
# Instalar todas las dependencias
make install-deps

# O manualmente
source .venv/bin/activate
pip install -e ".[grpc,dev]"
```

---

## 🔧 Desarrollo

### Workflow Típico

1. **Generar protos** (si trabajas con gRPC):
   ```bash
   make generate-protos
   ```

2. **Ejecutar tests**:
   ```bash
   make test-unit
   ```

3. **Desplegar cambios**:
   ```bash
   make deploy-service-fast SERVICE=planning
   ```

### Ver Todos los Comandos Disponibles

```bash
make help
```

---

## 📝 Notas

- Los archivos protobuf generados (`services/*/gen/`) **NO** se commitean a git
- Los tests unitarios generan protos automáticamente
- El deployment usa Podman (no Docker) en este proyecto
- Los servicios se despliegan en el namespace `swe-ai-fleet` en Kubernetes

---

## 🆘 Troubleshooting

### Error: "No module named 'planning.gen'"

**Solución:** Genera los protos primero:
```bash
make generate-protos
```

### Error: "Service not found" al desplegar

**Solución:** Verifica los servicios disponibles:
```bash
make list-services
```

### Error: Tests fallan con imports de protobuf

**Solución:** Limpia y regenera:
```bash
make clean-protos
make generate-protos
```

