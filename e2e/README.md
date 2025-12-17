# E2E Tests

Este directorio contiene los tests end-to-end (E2E) del proyecto SWE AI Fleet.

## Visión General

Los tests E2E verifican el comportamiento completo del sistema en un entorno real (cluster de Kubernetes). A diferencia de los tests unitarios, los tests E2E:

- Se ejecutan en el cluster de Kubernetes
- Acceden a los servicios desplegados a través de la red interna
- No requieren port forwarding
- Verifican flujos completos entre múltiples servicios

## Estructura

```
e2e/
├── README.md                    # Este archivo
├── PROCEDURE.md                 # Guía detallada para crear nuevos tests
└── tests/
    ├── 01-planning-ui-get-node-relations/  # Test ejemplo
    │   ├── test_get_node_relations.py
    │   ├── Dockerfile
    │   ├── job.yaml
    │   ├── Makefile
    │   └── README.md
    └── NN-test-name/            # Otros tests (numerados secuencialmente)
        └── ...
```

## Tests Disponibles

### 01-planning-ui-get-node-relations

Verifica que Planning UI puede llamar a Context Service `GetGraphRelationships` para obtener relaciones de nodos desde Neo4j.

**Ver**: [README del test](tests/01-planning-ui-get-node-relations/README.md)

## Crear un Nuevo Test

Sigue el procedimiento detallado en [PROCEDURE.md](PROCEDURE.md) para crear nuevos tests E2E.

**Resumen rápido**:

1. Crea el directorio: `e2e/tests/NN-test-name/`
2. Crea los archivos necesarios:
   - `test_*.py` - Script de test
   - `Dockerfile` - Imagen del container
   - `job.yaml` - Kubernetes Job
   - `Makefile` - Build y deploy
   - `README.md` - Documentación
3. Build y deploy:
   ```bash
   cd e2e/tests/NN-test-name
   make build-push
   make deploy
   make logs
   ```

## Ejecutar Tests

### Desde el Directorio del Test

```bash
cd e2e/tests/01-planning-ui-get-node-relations

# Build
make build

# Deploy
make deploy

# Ver logs
make logs

# Ver status
make status

# Limpiar
make delete
```

### Desde la Raíz del Proyecto

```bash
# Build
cd e2e/tests/01-planning-ui-get-node-relations && make build

# Deploy
kubectl apply -f e2e/tests/01-planning-ui-get-node-relations/job.yaml

# Ver logs
kubectl logs -n swe-ai-fleet -l app=e2e-planning-ui-get-node-relations -f
```

## Prerrequisitos

- Kubernetes cluster con servicios desplegados
- Acceso al namespace `swe-ai-fleet`
- Docker/Podman para construir imágenes
- kubectl configurado
- Acceso al registry de imágenes

## Convenciones

- **Numeración**: Tests numerados secuencialmente (01, 02, 03, ...)
- **Nombres**: Descriptivos y en kebab-case
- **Estructura**: Cada test en su propio directorio con todos los archivos necesarios
- **Documentación**: Cada test debe tener su propio README.md

## Troubleshooting

Ver [PROCEDURE.md](PROCEDURE.md#troubleshooting) para troubleshooting detallado.

### Problemas Comunes

1. **Test falla con "Connection refused"**
   - Verifica que los servicios estén desplegados
   - Verifica DNS interno del cluster

2. **Test falla con "Node not found"**
   - Verifica que los datos de prueba existan en Neo4j
   - Crea datos de prueba si es necesario

3. **ImagePullBackOff**
   - Verifica que la imagen esté en el registry
   - Rebuild y push: `make build-push`

## Referencias

- [Procedimiento Detallado](PROCEDURE.md) - Guía completa para crear tests E2E
- [Backlog Review Flow](../../services/backlog_review_processor/BACKLOG_REVIEW_FLOW_NO_STYLES.md) - Diagrama de flujo arquitectónico

---

**Última actualización**: 2025-01-XX
**Mantenido por**: Equipo de Desarrollo SWE AI Fleet

