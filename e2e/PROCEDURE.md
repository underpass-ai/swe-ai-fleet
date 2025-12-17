# Procedimiento para Crear Tests E2E

Este documento describe el procedimiento detallado para crear tests end-to-end (E2E) en el proyecto SWE AI Fleet.

## Índice

1. [Visión General](#visión-general)
2. [Estructura de Directorios](#estructura-de-directorios)
3. [Procedimiento Paso a Paso](#procedimiento-paso-a-paso)
4. [Plantilla de Archivos](#plantilla-de-archivos)
5. [Mejores Prácticas](#mejores-prácticas)
6. [Troubleshooting](#troubleshooting)

---

## Visión General

### ¿Qué son los Tests E2E?

Los tests E2E verifican el comportamiento completo del sistema en un entorno real (cluster de Kubernetes). A diferencia de los tests unitarios que prueban componentes aislados, los tests E2E:

- Se ejecutan en el cluster de Kubernetes
- Acceden a los servicios desplegados a través de la red interna
- No requieren port forwarding
- Verifican flujos completos entre múltiples servicios

### Arquitectura de Tests E2E

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │  E2E Test    │──────▶│   Services   │                     │
│  │   (Job)      │ gRPC  │  (Deployed)  │                     │
│  └──────────────┘      └──────────────┘                     │
│         │                                                     │
│         │                                                     │
│         ▼                                                     │
│  ┌──────────────┐                                            │
│  │   Neo4j      │                                            │
│  │   Valkey     │                                            │
│  └──────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

Cada test E2E:
1. Se ejecuta como un Kubernetes Job
2. Corre en un container que tiene acceso a la red interna del cluster
3. Llama a los servicios desplegados usando DNS interno (e.g., `context.swe-ai-fleet.svc.cluster.local:50054`)
4. Verifica el comportamiento end-to-end

---

## Estructura de Directorios

```
e2e/
├── PROCEDURE.md                          # Este documento
└── tests/
    ├── 01-planning-ui-get-node-relations/  # Test ejemplo
    │   ├── test_get_node_relations.py
    │   ├── Dockerfile
    │   ├── job.yaml
    │   ├── Makefile
    │   └── README.md
    ├── 02-next-test/                      # Siguiente test
    │   └── ...
    └── NN-test-name/                       # Tests numerados secuencialmente
        └── ...
```

### Convención de Nombres

- **Directorio**: `NN-description` donde `NN` es un número secuencial de 2 dígitos
  - Ejemplo: `01-planning-ui-get-node-relations`, `02-orchestrator-deliberation`, etc.
- **Archivo de test**: `test_*.py` (sigue convención pytest)
- **Dockerfile**: `Dockerfile` (sin extensión)
- **Kubernetes Job**: `job.yaml`
- **Makefile**: `Makefile` (sin extensión)
- **Documentación**: `README.md`

---

## Procedimiento Paso a Paso

### Paso 1: Crear Directorio del Test

```bash
# Desde la raíz del proyecto
mkdir -p e2e/tests/NN-test-name
cd e2e/tests/NN-test-name
```

**Nota**: Reemplaza `NN` con el siguiente número disponible y `test-name` con una descripción clara del test.

### Paso 2: Crear el Script de Test

Crea `test_*.py` con la siguiente estructura base:

```python
#!/usr/bin/env python3
"""E2E Test: [Descripción del test].

Este test verifica [qué se está probando].

Flow Verified:
1. [Servicio A] → [Servicio B] (Protocolo): [Acción]
2. [Servicio B] → [Base de Datos]: [Acción]
3. [Verificación]

Test Prerequisites:
- [Requisito 1]
- [Requisito 2]

Test Data:
- [Cómo obtener datos de prueba]
"""

import asyncio
import os
import sys
from typing import Optional

import grpc
from fleet.[service].v[version] import [service]_pb2, [service]_pb2_grpc


class Colors:
    """ANSI color codes for terminal output."""
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"


def print_step(step: int, description: str) -> None:
    """Print step header."""
    print()
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print(f"{Colors.BLUE}Step {step}: {description}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print()


def print_success(message: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.NC}")


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.NC}")


def print_info(message: str) -> None:
    """Print info message."""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.NC}")


class YourTestName:
    """E2E test for [descripción]."""

    def __init__(self) -> None:
        """Initialize test with service URLs from environment."""
        # Service URLs (Kubernetes internal DNS)
        self.service_url = os.getenv(
            "SERVICE_URL",
            "service.swe-ai-fleet.svc.cluster.local:50054"
        )

        # Test data
        self.test_param = os.getenv("TEST_PARAM", "").strip()

        # gRPC channels and stubs
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[ServiceStub] = None

    async def setup(self) -> None:
        """Set up gRPC connections."""
        print_info("Setting up connections...")

        # Create gRPC channel
        self.channel = grpc.aio.insecure_channel(self.service_url)
        self.stub = ServiceStub(self.channel)

        print_success("Setup completed")

    async def cleanup(self) -> None:
        """Clean up connections."""
        print_info("Cleaning up connections...")

        if self.channel:
            await self.channel.close()

        print_success("Cleanup completed")

    async def test_step_1(self) -> bool:
        """Test: [Descripción del paso]."""
        print_step(1, "[Descripción del paso]")

        try:
            # Build request
            request = ServiceRequest(
                param=self.test_param
            )

            # Call service
            print_info("Calling service...")
            response = await self.stub.ServiceMethod(request)

            # Verify response
            if not response.success:
                print_error(f"Service call failed: {response.message}")
                return False

            print_success("Service call succeeded")
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def run(self) -> int:
        """Run the complete E2E test."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}🚀 [Nombre del Test] E2E Test{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  Service URL: {self.service_url}")
        print()

        try:
            await self.setup()

            # Run test steps
            steps = [
                ("Step 1", self.test_step_1),
                # Add more steps as needed
            ]

            for step_name, step_func in steps:
                success = await step_func()
                if not success:
                    print_error(f"Step '{step_name}' failed")
                    return 1

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}✅ E2E test PASSED{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print()
            return 0

        except KeyboardInterrupt:
            print()
            print_warning("Test interrupted by user")
            return 130
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            await self.cleanup()


async def main() -> int:
    """Main entry point."""
    test = YourTestName()
    return await test.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
```

### Paso 3: Crear Dockerfile

El Dockerfile debe:

1. **Generar stubs de protobuf** (Stage 1)
2. **Instalar dependencias** (Stage 2)
3. **Copiar el test** (Stage 2)
4. **Configurar usuario no-root** (Stage 2)

**Plantilla base**:

```dockerfile
# ============================================================================
# Stage 1: Generate protobuf Python stubs
# ============================================================================
FROM python:3.13-slim AS proto-builder

WORKDIR /build

# Install protoc and grpc_tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# Install Python protobuf tools
RUN pip install --no-cache-dir \
    grpcio-tools==1.67.1 \
    protobuf==5.28.3

# Copy proto specs
COPY specs/fleet /build/specs/fleet

# Create output directory and generate Python stubs
RUN mkdir -p /build/gen && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --grpc_python_out=/build/gen \
    --pyi_out=/build/gen \
    /build/specs/fleet/[service]/v[version]/[service].proto

# Fix imports in generated files
RUN find /build/gen -name "*_pb2*.py" -exec sed -i \
    -e 's/^from [service]\.v[version]/from fleet.[service].v[version]/g' \
    {} \;

# ============================================================================
# Stage 2: Test Runner
# ============================================================================
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    grpcio==1.67.1 \
    grpcio-tools==1.67.1 \
    protobuf==5.28.3 \
    # Add other dependencies as needed
    # neo4j==5.26.0 \
    # valkey==6.0.2 \

# Copy generated protobuf stubs from builder stage
COPY --from=proto-builder /build/gen /app

# Copy test script
COPY e2e/tests/NN-test-name/test_*.py /app/test_*.py

# Set PYTHONPATH to include /app for imports
ENV PYTHONPATH=/app

# Create non-root user for security
RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

# Default command: run the E2E test
CMD ["python", "/app/test_*.py"]
```

**Importante**:
- Reemplaza `[service]`, `[version]`, `NN-test-name` con valores reales
- Añade solo las dependencias necesarias (neo4j, valkey, etc.)
- Asegúrate de copiar el archivo de test correcto

### Paso 4: Crear job.yaml

El job.yaml define el Kubernetes Job que ejecutará el test.

**Plantilla base**:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: e2e-test-name
  namespace: swe-ai-fleet
  labels:
    app: e2e-test-name
    version: v1.0.0
    test-type: end-to-end
    test-suite: [suite-name]  # e.g., planning-ui, orchestrator
spec:
  backoffLimit: 1  # Retry once on failure
  ttlSecondsAfterFinished: 3600  # Clean up after 1 hour
  activeDeadlineSeconds: 600  # Maximum execution time (adjust as needed)

  template:
    metadata:
      labels:
        app: e2e-test-name
        test-type: end-to-end
        test-suite: [suite-name]
    spec:
      restartPolicy: Never

      containers:
      - name: e2e-test-runner
        image: registry.underpassai.com/swe-ai-fleet/e2e-test-name:v1.0.0
        imagePullPolicy: Always

        env:
        # Service URLs (Kubernetes internal DNS)
        - name: SERVICE_URL
          value: "service.swe-ai-fleet.svc.cluster.local:50054"

        # Test data - REQUIRED parameters
        - name: TEST_PARAM
          value: ""  # Set required test parameters

        # Optional test parameters
        - name: TEST_OPTIONAL_PARAM
          value: "default-value"

        # Test execution options
        - name: PYTHONUNBUFFERED
          value: "1"

        # Resource limits (adjust based on test needs)
        resources:
          requests:
            cpu: "200m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"

        # Security context
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          capabilities:
            drop:
            - ALL

      dnsPolicy: ClusterFirst
```

**Importante**:
- Usa nombres descriptivos para el job
- Ajusta `activeDeadlineSeconds` según la duración esperada del test
- Ajusta recursos según necesidades
- Documenta todos los parámetros requeridos

### Paso 5: Crear Makefile

El Makefile facilita el build, push y deploy del test.

**Plantilla base**:

```makefile
# Makefile for [Test Name] E2E Test

REGISTRY ?= registry.underpassai.com/swe-ai-fleet
IMAGE_NAME = e2e-test-name
VERSION ?= v1.0.0
IMAGE = $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
LATEST = $(REGISTRY)/$(IMAGE_NAME):latest

# Detect container builder (podman preferred over docker)
BUILDER := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

.PHONY: build
build:
	@echo "🏗️  Building $(IMAGE)..."
	cd ../../../ && $(BUILDER) build \
		-f e2e/tests/NN-test-name/Dockerfile \
		-t $(IMAGE) \
		-t $(LATEST) \
		.
	@echo "✅ Built $(IMAGE)"

.PHONY: push
push:
	@echo "📤 Pushing $(IMAGE)..."
	$(BUILDER) push $(IMAGE)
	$(BUILDER) push $(LATEST)
	@echo "✅ Pushed $(IMAGE)"

.PHONY: build-push
build-push: build push

.PHONY: deploy
deploy:
	@echo "🚀 Deploying E2E test job..."
	kubectl apply -f e2e/tests/NN-test-name/job.yaml
	@echo "✅ Job deployed"

.PHONY: status
status:
	@echo "📊 Checking job status..."
	kubectl get job -n swe-ai-fleet e2e-test-name
	@echo ""
	@echo "📋 Pod status:"
	kubectl get pods -n swe-ai-fleet -l app=e2e-test-name

.PHONY: logs
logs:
	@echo "📜 Showing test logs..."
	kubectl logs -n swe-ai-fleet -l app=e2e-test-name --tail=100 -f

.PHONY: delete
delete:
	@echo "🗑️  Deleting job..."
	kubectl delete job -n swe-ai-fleet e2e-test-name || true
	@echo "✅ Job deleted"

.PHONY: run-local
run-local:
	@echo "🧪 Running e2e test locally..."
	@if [ -z "$(TEST_PARAM)" ]; then \
		echo "❌ ERROR: TEST_PARAM environment variable is required"; \
		exit 1; \
	fi
	$(BUILDER) run --rm \
		--network host \
		-e SERVICE_URL=localhost:50054 \
		-e TEST_PARAM=$(TEST_PARAM) \
		$(IMAGE)

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  build           - Build the container image"
	@echo "  push            - Push the image to registry"
	@echo "  build-push      - Build and push"
	@echo "  deploy          - Deploy the test job to Kubernetes"
	@echo "  status          - Check job status"
	@echo "  logs            - View test logs"
	@echo "  delete          - Delete the test job"
	@echo "  run-local       - Run test locally (requires TEST_PARAM)"
```

**Importante**:
- Ajusta las rutas según la ubicación del test
- Añade validaciones para parámetros requeridos
- Documenta todos los targets

### Paso 6: Crear README.md

El README documenta:
- Descripción del test
- Prerrequisitos
- Cómo ejecutar
- Variables de entorno
- Troubleshooting

**Plantilla base**:

```markdown
# E2E Test: [Nombre del Test]

[Descripción breve del test]

## Overview

[Descripción detallada del flujo que se prueba]

## Prerequisites

- [Requisito 1]
- [Requisito 2]

## Test Data

[Descripción de cómo obtener/configurar datos de prueba]

## Building

\`\`\`bash
make build
make build-push
\`\`\`

## Deployment

\`\`\`bash
make deploy
make status
make logs
\`\`\`

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SERVICE_URL` | Service endpoint | No | `service.swe-ai-fleet.svc.cluster.local:50054` |
| `TEST_PARAM` | Test parameter | **Yes** | - |

## Troubleshooting

[Sección de troubleshooting]
```

### Paso 7: Build y Deploy

```bash
# 1. Build la imagen
cd e2e/tests/NN-test-name
make build

# 2. Push a registry (si es necesario)
make build-push

# 3. Editar job.yaml para configurar parámetros requeridos
# (especialmente TEST_PARAM y otros parámetros requeridos)

# 4. Deploy el job
make deploy

# 5. Monitorear el test
make status
make logs

# 6. Limpiar cuando termine
make delete
```

---

## Plantilla de Archivos

### Estructura Completa

```
e2e/tests/NN-test-name/
├── test_*.py          # Script de test
├── Dockerfile         # Imagen del container
├── job.yaml           # Kubernetes Job
├── Makefile           # Build y deploy
└── README.md          # Documentación
```

---

## Mejores Prácticas

### 1. Nombres y Organización

- ✅ Usa números secuenciales para ordenar tests
- ✅ Usa nombres descriptivos y claros
- ✅ Mantén tests independientes (no dependencias entre tests)
- ✅ Un test = un flujo específico

### 2. Código del Test

- ✅ Usa funciones helper para imprimir (print_step, print_success, etc.)
- ✅ Valida todas las respuestas
- ✅ Maneja errores de forma clara
- ✅ Proporciona mensajes informativos
- ✅ Limpia recursos en `cleanup()`

### 3. Dockerfile

- ✅ Usa multi-stage build para protobuf
- ✅ Instala solo dependencias necesarias
- ✅ Usa usuario no-root
- ✅ Mantén la imagen pequeña

### 4. Kubernetes Job

- ✅ Ajusta `activeDeadlineSeconds` según duración esperada
- ✅ Ajusta recursos según necesidades
- ✅ Usa labels consistentes
- ✅ Documenta todos los parámetros requeridos

### 5. Documentación

- ✅ Documenta prerrequisitos claramente
- ✅ Explica cómo obtener datos de prueba
- ✅ Incluye ejemplos de uso
- ✅ Documenta troubleshooting común

### 6. Testing

- ✅ Prueba el test localmente antes de deployar
- ✅ Verifica que los servicios estén desplegados
- ✅ Verifica que los datos de prueba existan
- ✅ Revisa logs cuando el test falle

---

## Troubleshooting

### El test falla con "Connection refused"

**Causa**: El servicio no está desplegado o no es accesible.

**Solución**:
```bash
# Verificar que el servicio esté desplegado
kubectl get svc -n swe-ai-fleet

# Verificar que el pod del servicio esté corriendo
kubectl get pods -n swe-ai-fleet -l app=service-name

# Verificar DNS interno
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  nslookup service.swe-ai-fleet.svc.cluster.local
```

### El test falla con "Node not found"

**Causa**: Los datos de prueba no existen en Neo4j.

**Solución**:
```bash
# Verificar que el nodo exista
kubectl exec -it -n swe-ai-fleet statefulset/neo4j -- \
  cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (n {id: 'node-id'}) RETURN n"

# Crear datos de prueba si no existen
```

### El test falla con "ImagePullBackOff"

**Causa**: La imagen no existe en el registry o no se puede acceder.

**Solución**:
```bash
# Verificar que la imagen existe
podman images | grep e2e-test-name

# Rebuild y push
make build-push

# Verificar que el registry es accesible desde el cluster
```

### El test tarda mucho tiempo

**Causa**: Timeout o recursos insuficientes.

**Solución**:
- Aumenta `activeDeadlineSeconds` en job.yaml
- Aumenta recursos (CPU/memory) si es necesario
- Optimiza el test para reducir tiempo de ejecución

---

## Ejemplo Completo

Ver `e2e/tests/01-planning-ui-get-node-relations/` para un ejemplo completo de implementación.

---

## Referencias

- [Kubernetes Jobs Documentation](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [gRPC Python Documentation](https://grpc.io/docs/languages/python/)
- [Protobuf Python Guide](https://protobuf.dev/getting-started/pythontutorial/)

---

**Última actualización**: 2025-01-XX
**Mantenido por**: Equipo de Desarrollo SWE AI Fleet

