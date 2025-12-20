# E2E Tests Auxiliares

Esta carpeta contiene tests E2E auxiliares que validan funcionalidades específicas o casos de uso particulares, pero que no forman parte del flujo principal de tests E2E.

## Tests Disponibles

### 06-validate-single-deliberation

Valida que una deliberación única puede ser ejecutada y procesada correctamente:
- Envío de deliberación a Ray Executor
- Procesamiento por vLLM
- Separación de reasoning del contenido
- Limpieza de contenido (sin tags `<think>`)

**Uso:**
```bash
cd e2e/tests/auxiliary/06-validate-single-deliberation
make deploy
```

### 07-validate-review-results-persistence

Valida que los review results se persisten correctamente en Planning Service:
- Creación de ceremonia
- Persistencia de deliberaciones individuales (BRP → Planning Service)
- Aparición de review results en la ceremonia
- Transición de estado a `REVIEWING` cuando todas las stories están completas

**Uso:**
```bash
cd e2e/tests/auxiliary/07-validate-review-results-persistence
make deploy
```

## Flujo Principal vs Auxiliares

Los tests en la raíz de `e2e/tests/` (01-05) forman el flujo principal:
1. **01**: Preparación (UI, relaciones)
2. **02**: Creación de datos de test
3. **03**: Limpieza de datos
4. **04**: Inicio de ceremonia
5. **05**: Validación completa del flujo (deliberaciones + tareas)

Los tests auxiliares (06-07) son para validar funcionalidades específicas o debugging:
- **06**: Validación de una deliberación única (útil para debugging)
- **07**: Validación de persistencia de review results (útil para verificar implementación)

## Notas

- Estos tests pueden ejecutarse independientemente del flujo principal
- Son útiles para debugging y validación de funcionalidades específicas
- No son parte del pipeline de CI/CD principal (a menos que se configuren explícitamente)
