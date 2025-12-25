# E2E Test Runner - Mejoras Propuestas

Este documento describe las mejoras implementadas y propuestas para el runner de tests E2E.

## Mejoras Implementadas

### 1. Script de Ejecución Secuencial (`run-e2e-tests.sh`)

**Problema Original:**
- Tests E2E se ejecutaban manualmente uno por uno
- No había forma de asegurar que un test terminara antes de iniciar el siguiente
- Tests asíncronos (como el 05) requerían revisar logs manualmente

**Solución Implementada:**
- Script bash que ejecuta tests secuencialmente (01-06)
- Detección automática de tests síncronos vs asíncronos
- Para tests síncronos: usa `kubectl wait` para esperar completion
- Para tests asíncronos: monitorea logs buscando indicadores de completion
- Manejo de errores con detención automática en caso de fallo
- Resumen final con estadísticas

**Características:**
- ✅ Ejecución secuencial garantizada
- ✅ Timeouts configurables por test
- ✅ Opción de empezar desde un test específico
- ✅ Opción de saltar build/push
- ✅ Limpieza automática de jobs
- ✅ Logs detallados de progreso

### 2. Tratamiento de Tests

**Todos los tests se tratan como asíncronos:**
- El runner monitorea logs para detectar completion
- Verifica múltiples patrones de completion en logs
- También verifica el estado del pod (Succeeded/Failed)
- Esto asegura detección robusta independientemente del tipo de test

**Razón:**
- Incluso tests "síncronos" pueden tener procesos internos que toman tiempo
- Es más robusto monitorear logs que solo confiar en el estado del job
- Permite detectar completion antes de que el pod termine completamente
- Facilita debugging mostrando progreso en tiempo real

## Mejoras Propuestas (Futuras)

### 1. Exit Codes Estándar en Tests

**Problema:**
- Tests asíncronos no pueden usar exit codes para indicar completion
- Dependencia de parsing de logs es frágil

**Propuesta:**
- Todos los tests deberían escribir un archivo de estado al finalizar:
  ```python
  # Al final del test
  with open("/tmp/test_status.json", "w") as f:
      json.dump({
          "status": "success" | "failed",
          "exit_code": 0 | 1,
          "completed_at": datetime.now().isoformat(),
          "summary": {...}
      }, f)
  ```

- El runner puede verificar este archivo en lugar de parsear logs:
  ```bash
  kubectl exec -n swe-ai-fleet $pod -- cat /tmp/test_status.json
  ```

**Beneficios:**
- Más robusto que parsing de logs
- Permite extraer metadata estructurada
- Facilita debugging

### 2. Health Check Endpoint en Tests

**Problema:**
- Tests asíncronos requieren polling de logs
- No hay forma de verificar progreso sin logs

**Propuesta:**
- Cada test expone un endpoint HTTP simple (puerto 8080):
  ```python
  from http.server import HTTPServer, BaseHTTPRequestHandler

  class HealthHandler(BaseHTTPRequestHandler):
      def do_GET(self):
          if self.path == "/health":
              status = get_test_status()  # "running" | "completed" | "failed"
              self.send_response(200)
              self.send_header("Content-Type", "application/json")
              self.end_headers()
              self.wfile.write(json.dumps({"status": status}).encode())
  ```

- El runner puede hacer health checks:
  ```bash
  kubectl port-forward -n swe-ai-fleet $pod 8080:8080 &
  curl http://localhost:8080/health
  ```

**Beneficios:**
- Verificación de estado más rápida
- No requiere parsing de logs
- Permite ver progreso en tiempo real

### 3. Job Annotations para Metadata

**Problema:**
- No hay forma de pasar información entre tests
- No hay forma de rastrear qué test creó qué recursos

**Propuesta:**
- Usar annotations de Kubernetes para metadata:
  ```yaml
  metadata:
    annotations:
      e2e.test-id: "05"
      e2e.ceremony-id: "BRC-xxx"  # Pasado al siguiente test
      e2e.created-resources: '["project-123", "epic-456"]'
  ```

- Tests pueden leer annotations de jobs anteriores:
  ```bash
  kubectl get job e2e-validate-deliberations-and-tasks \
    -n swe-ai-fleet \
    -o jsonpath='{.metadata.annotations.e2e\.ceremony-id}'
  ```

**Beneficios:**
- Pasaje de datos entre tests
- Rastreabilidad de recursos creados
- Facilita debugging

### 4. Test Dependencies Declarativas

**Problema:**
- Dependencias entre tests están hardcodeadas
- No hay validación de que prerequisitos se cumplan

**Propuesta:**
- Archivo YAML de configuración de tests:
  ```yaml
  tests:
    - id: "01"
      name: "planning-ui-get-node-relations"
      type: "sync"
      dependencies: []

    - id: "02"
      name: "create-test-data"
      type: "sync"
      dependencies: []

    - id: "05"
      name: "validate-deliberations-and-tasks"
      type: "async"
      dependencies: ["02", "04"]
      completion_conditions:
        - type: "log_pattern"
          pattern: "Test Completed Successfully"
        - type: "ceremony_status"
          status: "REVIEWING"
  ```

- El runner valida dependencias antes de ejecutar:
  ```bash
  if ! validate_dependencies "05"; then
      echo "Test 05 dependencies not met"
      exit 1
  fi
  ```

**Beneficios:**
- Validación automática de prerequisitos
- Configuración centralizada
- Fácil agregar nuevos tests

### 5. Retry Logic Inteligente

**Problema:**
- Si un test falla, hay que ejecutarlo manualmente de nuevo
- No hay distinción entre fallos transitorios y permanentes

**Propuesta:**
- Retry automático con backoff exponencial:
  ```bash
  retry_test() {
      local test_num=$1
      local max_retries=3
      local retry=0

      while [[ $retry -lt $max_retries ]]; do
          if run_test "$test_num"; then
              return 0
          fi

          # Verificar si es error transitorio
          if is_transient_error; then
              wait_time=$((2 ** retry * 10))  # 10s, 20s, 40s
              echo "Transient error, retrying in ${wait_time}s..."
              sleep $wait_time
              retry=$((retry + 1))
          else
              return 1  # Error permanente, no retry
          fi
      done

      return 1
  }
  ```

**Beneficios:**
- Mayor resiliencia a fallos transitorios
- Menos intervención manual
- Mejor experiencia de uso

### 6. Parallel Execution con Dependencies

**Problema:**
- Ejecución secuencial es lenta
- Algunos tests podrían ejecutarse en paralelo

**Propuesta:**
- Análisis de dependencias para ejecución paralela:
  ```bash
  # Tests sin dependencias pueden ejecutarse en paralelo
  run_parallel_tests() {
      local independent_tests=("01" "02")

      for test_num in "${independent_tests[@]}"; do
          run_test "$test_num" &
      done

      wait  # Esperar a que todos terminen
  }
  ```

**Beneficios:**
- Ejecución más rápida
- Mejor uso de recursos
- Mantiene garantías de orden

### 7. Test Results Persistence

**Problema:**
- Resultados de tests se pierden después de ejecución
- No hay historial de ejecuciones

**Propuesta:**
- Guardar resultados en ConfigMap o base de datos:
  ```bash
  save_test_result() {
      local test_num=$1
      local status=$2
      local result_json=$(cat <<EOF
  {
    "test_id": "$test_num",
    "status": "$status",
    "timestamp": "$(date -Iseconds)",
    "duration": "$duration",
    "logs": "$(base64_encode logs)"
  }
  EOF
      )

      kubectl create configmap "e2e-result-${test_num}-$(date +%s)" \
        --from-literal=result="$result_json" \
        -n swe-ai-fleet
  }
  ```

**Beneficios:**
- Historial de ejecuciones
- Facilita análisis de tendencias
- Debugging de problemas recurrentes

### 8. Notificaciones y Alertas

**Problema:**
- No hay notificación cuando tests fallan
- No hay forma de saber cuándo tests completan

**Propuesta:**
- Integración con sistemas de notificación:
  ```bash
  send_notification() {
      local status=$1
      local message=$2

      # Slack
      curl -X POST "$SLACK_WEBHOOK" \
        -d "{\"text\": \"E2E Test: $message\"}"

      # Email
      echo "$message" | mail -s "E2E Test $status" team@example.com
  }
  ```

**Beneficios:**
- Visibilidad inmediata de fallos
- Mejor colaboración en equipo
- Alertas proactivas

## Priorización de Mejoras

### Alta Prioridad (Implementar Pronto)
1. ✅ **Script de ejecución secuencial** - IMPLEMENTADO
2. **Exit codes estándar** - Mejora robustez significativamente
3. **Test dependencies declarativas** - Facilita mantenimiento

### Media Prioridad
4. **Health check endpoint** - Mejora experiencia pero no crítico
5. **Job annotations** - Útil para debugging avanzado
6. **Retry logic** - Mejora resiliencia

### Baja Prioridad (Nice to Have)
7. **Parallel execution** - Optimización, no crítico
8. **Test results persistence** - Útil para análisis a largo plazo
9. **Notificaciones** - Conveniencia, no funcionalidad core

## Implementación Recomendada

### Fase 1: Robustez (Sprint Actual)
- ✅ Script de ejecución secuencial
- Exit codes estándar en todos los tests
- Test dependencies declarativas

### Fase 2: Experiencia (Siguiente Sprint)
- Health check endpoints
- Job annotations para metadata
- Retry logic inteligente

### Fase 3: Optimización (Futuro)
- Parallel execution
- Test results persistence
- Notificaciones

## Uso del Script Actual

```bash
# Ejecutar todos los tests
./e2e/run-e2e-tests.sh

# Empezar desde test 05
./e2e/run-e2e-tests.sh --start-from 05

# Saltar build (usar imágenes existentes)
./e2e/run-e2e-tests.sh --skip-build

# Limpiar jobs después de ejecución
./e2e/run-e2e-tests.sh --cleanup

# Timeout personalizado (30 minutos por test)
./e2e/run-e2e-tests.sh --timeout 1800
```

## Contribuciones

Si implementas alguna de estas mejoras, por favor:
1. Actualiza este documento
2. Agrega tests para la nueva funcionalidad
3. Documenta cambios en el README principal

---

**Última actualización**: 2025-12-20
**Mantenido por**: SWE AI Fleet Development Team

