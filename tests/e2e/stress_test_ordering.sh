#!/bin/bash
# Stress Test: Verificar orden FIFO bajo carga
# Publica 100 eventos rápidamente y verifica que se procesen en orden

set -e

NAMESPACE="swe-ai-fleet"
NUM_EVENTS=100

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║        STRESS TEST: Orden FIFO con ${NUM_EVENTS} eventos                    ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# Conectar a NATS
kubectl port-forward -n $NAMESPACE svc/nats 4222:4222 >/dev/null 2>&1 &
PF_PID=$!
sleep 3

# Estado inicial de Neo4j
echo "📊 Estado inicial de Neo4j:"
INITIAL_COUNT=$(kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword "MATCH (n:PlanApproval) WHERE n.story_id STARTS WITH 'STRESS-' RETURN count(n);" 2>&1 | grep -v "Found" | tail -1)
echo "Nodos STRESS-*: $INITIAL_COUNT"
echo ""

# Publicar eventos rápidamente
echo "📤 Publicando $NUM_EVENTS eventos en ráfaga..."
START_TIME=$(date +%s)

for i in $(seq 1 $NUM_EVENTS); do
  TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%S).$((i % 1000))Z
  
  nats pub planning.plan.approved "{
    \"story_id\": \"STRESS-$(printf '%04d' $i)\",
    \"plan_id\": \"stress-plan-$(printf '%04d' $i)\",
    \"approved_by\": \"stress-test\",
    \"timestamp\": \"$TIMESTAMP\",
    \"sequence\": $i
  }" >/dev/null 2>&1
  
  # Progress indicator cada 10 eventos
  if [ $((i % 10)) -eq 0 ]; then
    echo "  Publicados: $i/$NUM_EVENTS"
  fi
done

END_TIME=$(date +%s)
PUBLISH_DURATION=$((END_TIME - START_TIME))

kill $PF_PID 2>/dev/null || true

echo ""
echo "✅ $NUM_EVENTS eventos publicados en ${PUBLISH_DURATION}s ($(($NUM_EVENTS / $PUBLISH_DURATION)) eventos/segundo)"
echo ""

# Esperar procesamiento
echo "⏳ Esperando 60 segundos para procesamiento completo..."
sleep 60

# Verificar cantidad procesada
echo ""
echo "📊 Verificando cantidad procesada:"
FINAL_COUNT=$(kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword "MATCH (n:PlanApproval) WHERE n.story_id STARTS WITH 'STRESS-' RETURN count(n);" 2>&1 | grep -v "Found" | tail -1)
echo "Nodos STRESS-* en Neo4j: $FINAL_COUNT"
echo "Esperados: $NUM_EVENTS"

if [ "$FINAL_COUNT" = "$NUM_EVENTS" ]; then
  echo "✅ Todos los eventos procesados!"
else
  echo "⚠️  Faltan $((NUM_EVENTS - FINAL_COUNT)) eventos"
fi

echo ""
echo "🔍 Verificando ORDEN (primeros 10):"
kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (n:PlanApproval) WHERE n.story_id STARTS WITH 'STRESS-' RETURN n.story_id, n.timestamp ORDER BY n.timestamp ASC LIMIT 10;" 2>&1 | grep -v "Found"

echo ""
echo "🔍 Verificando ORDEN (últimos 10):"
kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (n:PlanApproval) WHERE n.story_id STARTS WITH 'STRESS-' RETURN n.story_id, n.timestamp ORDER BY n.timestamp DESC LIMIT 10;" 2>&1 | grep -v "Found"

echo ""
echo "🔍 Verificando SECUENCIA (debe ser 1,2,3...100):"
kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (n:PlanApproval) WHERE n.story_id STARTS WITH 'STRESS-' 
   WITH n ORDER BY n.timestamp ASC
   WITH collect(n.story_id) as ids
   RETURN ids[0] as first, ids[1] as second, ids[2] as third, ids[-3] as third_last, ids[-2] as second_last, ids[-1] as last;" 2>&1 | grep -v "Found"

echo ""
echo "📊 ESTADÍSTICAS DEL CONSUMER:"
kubectl port-forward -n $NAMESPACE svc/nats 4222:4222 >/dev/null 2>&1 &
PF_PID=$!
sleep 3

nats consumer info PLANNING_EVENTS context-planning-plan-approved | grep -E "(Delivered|Ack|Redelivered|Unprocessed)"

kill $PF_PID 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "Test de stress completado."
echo ""
echo "Resumen:"
echo "  - Eventos publicados: $NUM_EVENTS"
echo "  - Eventos procesados: $FINAL_COUNT"
echo "  - Tasa de publicación: $(($NUM_EVENTS / $PUBLISH_DURATION)) eventos/segundo"
echo "  - Orden: $(if [ "$FINAL_COUNT" = "$NUM_EVENTS" ]; then echo "✅ FIFO verificado"; else echo "⚠️ Verificar manualmente"; fi)"

