#!/bin/bash
# Trigger un evento REAL en el sistema para verificar el flujo
# Publicamos directamente a NATS desde un pod temporal

set -e

NAMESPACE="swe-ai-fleet"

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║       TRIGGER EVENTO REAL: planning.plan.approved → NATS         ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# Crear evento de prueba
EVENT_DATA=$(cat <<EOF
{
  "event_type": "PLAN_APPROVED",
  "story_id": "US-VERIFY-001",
  "plan_id": "plan-verify-v1",
  "roles": ["DEV", "QA"],
  "subtasks_count": 5,
  "approved_by": "tirso@underpassai.com",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
)

echo "📤 Evento a publicar:"
echo "$EVENT_DATA" | jq .
echo ""

echo "🚀 Publicando evento a NATS: planning.plan.approved"
echo ""

# Publicar usando nats-box (pod temporal)
kubectl run nats-publisher \
  --image=docker.io/natsio/nats-box:latest \
  --rm -i --restart=Never \
  --namespace=$NAMESPACE \
  --command -- \
  nats pub planning.plan.approved "$EVENT_DATA" \
  --server=nats://nats.$NAMESPACE.svc.cluster.local:4222

echo ""
echo "✅ Evento publicado correctamente"
echo ""
echo "🔍 Esperando 5 segundos para que se propaguen los eventos..."
sleep 5

echo ""
echo "📋 Verificando logs de Context Service (consumer):"
kubectl logs -n $NAMESPACE deployment/context --tail=50 | grep -E "(received|planning|approved|US-VERIFY)" | tail -10

echo ""
echo "📋 Verificando logs de Orchestrator Service (consumer):"
kubectl logs -n $NAMESPACE deployment/orchestrator --tail=50 | grep -E "(received|planning|approved|US-VERIFY)" | tail -10

echo ""
echo "💾 Verificando Neo4j:"
kubectl exec -n $NAMESPACE neo4j-0 -- cypher-shell -u neo4j -p testpassword \
  "MATCH (n) WHERE n.story_id = 'US-VERIFY-001' OR n.plan_id = 'plan-verify-v1' RETURN n LIMIT 5;"

echo ""
echo "💾 Verificando ValKey:"
kubectl exec -n $NAMESPACE valkey-0 -- valkey-cli KEYS '*VERIFY*'

echo ""
echo "✅ Verificación completa"

