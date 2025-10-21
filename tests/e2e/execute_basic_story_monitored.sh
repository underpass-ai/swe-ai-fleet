#!/bin/bash
# Test E2E: Historia Básica con Monitoreo Completo
# Planifica US-BASIC-001 y monitorea todo el flujo

set -e

NAMESPACE="swe-ai-fleet"
STORY_ID="US-BASIC-001"
TIMESTAMP_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║  TEST E2E: Historia Básica US-BASIC-001 (Health Check Endpoint)  ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Historia:"
echo "  ID: $STORY_ID"
echo "  Título: Agregar endpoint de health check"
echo "  Complejidad: BAJA (1 SP)"
echo "  Roles: DEV, DEVOPS"
echo "  Subtareas estimadas: 3"
echo ""

# ═══════════════════════════════════════════════════════════════════
# FASE 1: ESTADO INICIAL
# ═══════════════════════════════════════════════════════════════════

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FASE 1: CAPTURA DE ESTADO INICIAL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📊 Neo4j - Estado inicial:"
NEO_INITIAL=$(kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (n) WHERE n.story_id = '$STORY_ID' RETURN count(n);" 2>&1 | tail -1)
echo "  Nodos para $STORY_ID: $NEO_INITIAL"

echo ""
echo "📊 ValKey - Estado inicial:"
VALKEY_INITIAL=$(kubectl exec -n $NAMESPACE valkey-0 -- valkey-cli --scan --pattern "context:$STORY_ID*" | wc -l)
echo "  Keys para $STORY_ID: $VALKEY_INITIAL"

echo ""
echo "📊 NATS - Mensajes en streams:"
kubectl port-forward -n $NAMESPACE svc/nats 4222:4222 >/dev/null 2>&1 &
PF_PID=$!
sleep 3

NATS_PLANNING_BEFORE=$(nats stream info PLANNING_EVENTS --json 2>/dev/null | jq -r '.state.messages' || echo "0")
NATS_ORCH_BEFORE=$(nats stream info ORCHESTRATOR_EVENTS --json 2>/dev/null | jq -r '.state.messages' || echo "0")

echo "  PLANNING_EVENTS: $NATS_PLANNING_BEFORE mensajes"
echo "  ORCHESTRATOR_EVENTS: $NATS_ORCH_BEFORE mensajes"

kill $PF_PID 2>/dev/null
wait $PF_PID 2>/dev/null || true

# ═══════════════════════════════════════════════════════════════════
# FASE 2: PUBLICAR EVENTO DE PLAN APROBADO
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FASE 2: PUBLICAR PLAN APROBADO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

kubectl port-forward -n $NAMESPACE svc/nats 4222:4222 >/dev/null 2>&1 &
PF_PID=$!
sleep 3

echo "📤 Publicando plan aprobado para $STORY_ID..."
PUBLISH_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

nats pub planning.plan.approved "{
  \"event_type\": \"PLAN_APPROVED\",
  \"story_id\": \"$STORY_ID\",
  \"plan_id\": \"plan-basic-001-monitored\",
  \"roles\": [\"DEV\", \"DEVOPS\"],
  \"subtasks_count\": 3,
  \"complexity\": \"LOW\",
  \"estimated_hours\": 2,
  \"approved_by\": \"tirso@underpassai.com\",
  \"timestamp\": \"$PUBLISH_TIME\",
  \"acceptance_criteria\": [
    \"GET /health returns 200 OK\",
    \"Response time < 100ms\",
    \"No authentication required\"
  ],
  \"technical_details\": {
    \"endpoint\": \"/health\",
    \"method\": \"GET\",
    \"response_format\": \"JSON\",
    \"dependencies\": []
  }
}"

kill $PF_PID 2>/dev/null
wait $PF_PID 2>/dev/null || true

echo "✅ Plan publicado a las $PUBLISH_TIME"

# ═══════════════════════════════════════════════════════════════════
# FASE 3: MONITOREO EN TIEMPO REAL (30s)
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FASE 3: MONITOREO EN TIEMPO REAL (30 segundos)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

for i in {1..6}; do
  echo "⏱️  Segundo $(($i * 5)):"
  
  # Logs de Context
  CONTEXT_LOGS=$(kubectl logs -n $NAMESPACE deployment/context --since=5s 2>/dev/null | grep -i "$STORY_ID" || echo "  Sin actividad")
  if [ "$CONTEXT_LOGS" != "  Sin actividad" ]; then
    echo "  Context: $(echo "$CONTEXT_LOGS" | head -1)"
  fi
  
  # Logs de Orchestrator
  ORCH_LOGS=$(kubectl logs -n $NAMESPACE deployment/orchestrator --since=5s 2>/dev/null | grep -i "$STORY_ID" || echo "  Sin actividad")
  if [ "$ORCH_LOGS" != "  Sin actividad" ]; then
    echo "  Orchestrator: $(echo "$ORCH_LOGS" | head -1)"
  fi
  
  # Ray Jobs
  RAY_JOBS=$(kubectl get rayjobs -n ray 2>/dev/null | grep -v NAME | wc -l)
  if [ "$RAY_JOBS" -gt 0 ]; then
    echo "  ⚡ Ray Jobs activos: $RAY_JOBS"
  fi
  
  sleep 5
done

# ═══════════════════════════════════════════════════════════════════
# FASE 4: ANÁLISIS POST-EJECUCIÓN
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FASE 4: ANÁLISIS POST-EJECUCIÓN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "1️⃣  NEO4J - Decisiones y tareas guardadas:"
echo ""
kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (n) WHERE n.story_id = '$STORY_ID' 
   RETURN labels(n)[0] as tipo, 
          coalesce(n.plan_id, n.decision_type, n.task_id, 'N/A') as id,
          coalesce(n.approved_by, n.decided_by, n.assigned_to, 'N/A') as quien,
          coalesce(n.timestamp, n.created_at, 'N/A') as cuando
   ORDER BY cuando;" 2>&1 | grep -v "Found" || echo "  Sin datos"

echo ""
echo "2️⃣  VALKEY - Datos cacheados:"
echo ""
kubectl exec -n $NAMESPACE valkey-0 -- valkey-cli --scan --pattern "*$STORY_ID*" 2>&1 | while read key; do
  if [ -n "$key" ]; then
    echo "  Key: $key"
    kubectl exec -n $NAMESPACE valkey-0 -- valkey-cli GET "$key" 2>&1 | head -3
  fi
done

echo ""
echo "3️⃣  NATS - Eventos procesados:"
echo ""
kubectl port-forward -n $NAMESPACE svc/nats 4222:4222 >/dev/null 2>&1 &
PF_PID=$!
sleep 3

NATS_PLANNING_AFTER=$(nats stream info PLANNING_EVENTS --json 2>/dev/null | jq -r '.state.messages' || echo "0")
NATS_ORCH_AFTER=$(nats stream info ORCHESTRATOR_EVENTS --json 2>/dev/null | jq -r '.state.messages' || echo "0")

echo "  PLANNING_EVENTS:"
echo "    Antes: $NATS_PLANNING_BEFORE | Después: $NATS_PLANNING_AFTER | Nuevos: $(($NATS_PLANNING_AFTER - $NATS_PLANNING_BEFORE))"

echo "  ORCHESTRATOR_EVENTS:"
echo "    Antes: $NATS_ORCH_BEFORE | Después: $NATS_ORCH_AFTER | Nuevos: $(($NATS_ORCH_AFTER - $NATS_ORCH_BEFORE))"

echo ""
echo "  Consumers que procesaron el evento:"
nats consumer list PLANNING_EVENTS 2>/dev/null | grep -E "Name|Delivered|Ack" || echo "  Error listando consumers"

kill $PF_PID 2>/dev/null
wait $PF_PID 2>/dev/null || true

echo ""
echo "4️⃣  LOGS DE RAZONAMIENTO (LLM Thoughts):"
echo ""
echo "  Context Service (últimos 20 logs relevantes):"
kubectl logs -n $NAMESPACE deployment/context --tail=100 | grep -E "($STORY_ID|Plan approved|Decision|Reasoning)" | tail -20 || echo "  Sin logs de razonamiento"

echo ""
echo "  Orchestrator Service (últimos 20 logs relevantes):"
kubectl logs -n $NAMESPACE deployment/orchestrator --tail=100 | grep -E "($STORY_ID|Deliberate|Council|Agent|Reasoning)" | tail -20 || echo "  Sin logs de razonamiento"

echo ""
echo "5️⃣  RAY JOBS (si se crearon):"
echo ""
kubectl get rayjobs -n ray 2>/dev/null || echo "  No hay Ray Jobs"

if kubectl get rayjobs -n ray 2>/dev/null | grep -q "NAME"; then
  echo ""
  echo "  Logs de Ray Jobs:"
  for job in $(kubectl get rayjobs -n ray -o name 2>/dev/null); do
    echo "  Job: $job"
    kubectl logs -n ray $job --tail=50 2>/dev/null | grep -E "(vLLM|Decision|Proposal)" | head -10 || echo "    Sin logs"
  done
fi

# ═══════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "✅ TEST E2E COMPLETADO - RESUMEN"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "📊 TIMELINE:"
echo "  Inicio: $TIMESTAMP_START"
echo "  Plan publicado: $PUBLISH_TIME"
echo "  Fin: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""
echo "📈 MÉTRICAS:"
NEO_FINAL=$(kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (n) WHERE n.story_id = '$STORY_ID' RETURN count(n);" 2>&1 | tail -1)
VALKEY_FINAL=$(kubectl exec -n $NAMESPACE valkey-0 -- valkey-cli --scan --pattern "*$STORY_ID*" | wc -l)

echo "  Nodos creados en Neo4j: $NEO_FINAL"
echo "  Keys creadas en ValKey: $VALKEY_FINAL"
echo "  Eventos NATS nuevos: $(($NATS_PLANNING_AFTER + $NATS_ORCH_AFTER - $NATS_PLANNING_BEFORE - $NATS_ORCH_BEFORE))"
echo ""
echo "🎯 PRÓXIMO PASO: Revisar logs detallados arriba"

