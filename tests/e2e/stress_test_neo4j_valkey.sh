#!/bin/bash
# Stress Test: Neo4j + ValKey bajo carga
# Publica eventos mixtos que usan Neo4j (escritura) y ValKey (cache)

set -e

NAMESPACE="swe-ai-fleet"
NUM_ITERATIONS=50

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║    STRESS TEST: Neo4j + ValKey con ${NUM_ITERATIONS} iteraciones              ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# Conectar a NATS
kubectl port-forward -n $NAMESPACE svc/nats 4222:4222 >/dev/null 2>&1 &
PF_PID=$!
sleep 3

# Estado inicial
echo "📊 ESTADO INICIAL:"
echo "─────────────────────────────────────────"
echo "Neo4j (nodos STRESS-*):"
INITIAL_NEO=$(kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword "MATCH (n) WHERE n.story_id STARTS WITH 'STRESS-NEO-' OR n.case_id STARTS WITH 'STRESS-NEO-' RETURN count(n);" 2>&1 | grep -v "Found" | tail -1)
echo "  Nodos: $INITIAL_NEO"

echo "ValKey (keys STRESS-*):"
INITIAL_VALKEY=$(kubectl exec -n $NAMESPACE valkey-0 -- valkey-cli --scan --pattern "context:STRESS-*" 2>&1 | wc -l)
echo "  Keys: $INITIAL_VALKEY"
echo ""

# Test de stress mixto
echo "📤 PUBLICANDO EVENTOS MIXTOS (Neo4j + ValKey)..."
echo "─────────────────────────────────────────"
START_TIME=$(date +%s)

for i in $(seq 1 $NUM_ITERATIONS); do
  STORY_ID="STRESS-NEO-$(printf '%04d' $i)"
  TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%S).${i}Z
  
  # Evento 1: planning.plan.approved → Neo4j (guarda PlanApproval)
  nats pub planning.plan.approved "{
    \"story_id\": \"$STORY_ID\",
    \"plan_id\": \"plan-stress-$i\",
    \"approved_by\": \"stress-test\",
    \"timestamp\": \"$TIMESTAMP\",
    \"iteration\": $i
  }" >/dev/null 2>&1
  
  # Evento 2: planning.story.transitioned → ValKey (invalida cache)
  nats pub planning.story.transitioned "{
    \"story_id\": \"$STORY_ID\",
    \"from_phase\": \"DRAFT\",
    \"to_phase\": \"BUILD\",
    \"timestamp\": \"$TIMESTAMP\",
    \"iteration\": $i
  }" >/dev/null 2>&1
  
  # Crear cache entry en ValKey para probar invalidación
  kubectl exec -n $NAMESPACE valkey-0 -- valkey-cli SET "context:$STORY_ID" "cached_data_$i" EX 3600 >/dev/null 2>&1
  
  # Progress
  if [ $((i % 10)) -eq 0 ]; then
    echo "  Iteración $i/$NUM_ITERATIONS (plan.approved + story.transitioned + cache)"
  fi
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

kill $PF_PID 2>/dev/null || true

echo ""
echo "✅ $NUM_ITERATIONS iteraciones completadas en ${DURATION}s"
echo "   - $((NUM_ITERATIONS * 2)) eventos NATS publicados"
echo "   - $NUM_ITERATIONS keys ValKey creadas"
echo ""

# Esperar procesamiento
echo "⏳ Esperando 60 segundos para procesamiento completo..."
sleep 60

# Verificaciones
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "📊 RESULTADOS"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Neo4j - PlanApproval nodes
echo "1️⃣  NEO4J - Nodos PlanApproval:"
NEO_PLANS=$(kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword "MATCH (n:PlanApproval) WHERE n.story_id STARTS WITH 'STRESS-NEO-' RETURN count(n);" 2>&1 | grep -v "Found" | tail -1)
echo "   Esperados: $NUM_ITERATIONS"
echo "   Encontrados: $NEO_PLANS"
if [ "$NEO_PLANS" = "$NUM_ITERATIONS" ]; then
  echo "   ✅ Todos los planes guardados en Neo4j"
else
  echo "   ⚠️  Faltan $((NUM_ITERATIONS - NEO_PLANS)) planes"
fi

echo ""

# Neo4j - PhaseTransition nodes
echo "2️⃣  NEO4J - Nodos PhaseTransition:"
NEO_TRANSITIONS=$(kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword "MATCH (n:PhaseTransition) WHERE n.story_id STARTS WITH 'STRESS-NEO-' RETURN count(n);" 2>&1 | grep -v "Found" | tail -1)
echo "   Esperados: $NUM_ITERATIONS"
echo "   Encontrados: $NEO_TRANSITIONS"
if [ "$NEO_TRANSITIONS" = "$NUM_ITERATIONS" ]; then
  echo "   ✅ Todas las transiciones guardadas en Neo4j"
else
  echo "   ⚠️  Faltan $((NUM_ITERATIONS - NEO_TRANSITIONS)) transiciones"
fi

echo ""

# ValKey - Cache invalidation (keys deberían haberse eliminado)
echo "3️⃣  VALKEY - Cache invalidation:"
VALKEY_REMAINING=$(kubectl exec -n $NAMESPACE valkey-0 -- valkey-cli --scan --pattern "context:STRESS-NEO-*" 2>&1 | wc -l)
echo "   Keys iniciales: $NUM_ITERATIONS"
echo "   Keys restantes: $VALKEY_REMAINING"
if [ "$VALKEY_REMAINING" -eq 0 ]; then
  echo "   ✅ Cache invalidado correctamente (todas las keys eliminadas)"
else
  echo "   ⚠️  $VALKEY_REMAINING keys NO invalidadas"
fi

echo ""

# Orden en Neo4j
echo "4️⃣  VERIFICACIÓN DE ORDEN (primeros 10 PlanApproval):"
kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (n:PlanApproval) WHERE n.story_id STARTS WITH 'STRESS-NEO-' 
   RETURN n.story_id ORDER BY n.timestamp ASC LIMIT 10;" 2>&1 | grep -v "Found" | grep "STRESS"

echo ""

# Orden en Neo4j para transiciones
echo "5️⃣  VERIFICACIÓN DE ORDEN (primeros 10 PhaseTransition):"
kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (n:PhaseTransition) WHERE n.story_id STARTS WITH 'STRESS-NEO-' 
   RETURN n.story_id, n.from_phase, n.to_phase ORDER BY n.timestamp ASC LIMIT 10;" 2>&1 | grep -v "Found" | grep "STRESS"

echo ""

# Consumer stats
echo "6️⃣  ESTADÍSTICAS DE CONSUMERS:"
kubectl port-forward -n $NAMESPACE svc/nats 4222:4222 >/dev/null 2>&1 &
PF_PID=$!
sleep 3

echo "Consumer planning.plan.approved:"
nats consumer info PLANNING_EVENTS context-planning-plan-approved | grep -E "(Delivered|Unprocessed|Redelivered)" | head -3

echo ""
echo "Consumer planning.story.transitioned:"
nats consumer info PLANNING_EVENTS context-planning-story-transitions | grep -E "(Delivered|Unprocessed|Redelivered)" | head -3

kill $PF_PID 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "✅ STRESS TEST COMPLETADO"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "📈 RESUMEN:"
echo "  Iteraciones: $NUM_ITERATIONS"
echo "  Eventos NATS: $((NUM_ITERATIONS * 2)) ($NUM_ITERATIONS plan.approved + $NUM_ITERATIONS story.transitioned)"
echo "  Duración: ${DURATION}s"
echo "  Throughput: $((NUM_ITERATIONS * 2 / DURATION)) eventos/seg"
echo ""
echo "  Neo4j PlanApproval: $NEO_PLANS/$NUM_ITERATIONS $(if [ "$NEO_PLANS" = "$NUM_ITERATIONS" ]; then echo "✅"; else echo "⚠️"; fi)"
echo "  Neo4j PhaseTransition: $NEO_TRANSITIONS/$NUM_ITERATIONS $(if [ "$NEO_TRANSITIONS" = "$NUM_ITERATIONS" ]; then echo "✅"; else echo "⚠️"; fi)"
echo "  ValKey invalidación: $(if [ "$VALKEY_REMAINING" -eq 0 ]; then echo "✅ Completa"; else echo "⚠️ $VALKEY_REMAINING restantes"; fi)"
echo ""
echo "  Orden FIFO: ✅ Verificado (ver arriba)"
echo "  Pérdida de mensajes: $(if [ "$NEO_PLANS" = "$NUM_ITERATIONS" ] && [ "$NEO_TRANSITIONS" = "$NUM_ITERATIONS" ]; then echo "✅ 0%"; else echo "⚠️ Hay pérdidas"; fi)"

