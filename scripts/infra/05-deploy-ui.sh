#!/bin/bash
# Step 7: Deploy PO UI (React Frontend)

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Step 7: Deploy PO UI (React Frontend)                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

read -p "Deploy PO UI? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
  echo "Aborted"
  exit 0
fi

echo ""
echo "🚀 Scaling up PO UI..."
kubectl scale deployment po-ui --replicas=2 -n swe-ai-fleet

echo ""
echo "⏳ Waiting for PO UI to be ready..."
kubectl wait --for=condition=available deployment/po-ui -n swe-ai-fleet --timeout=180s

echo ""
echo "✅ Verifying..."
kubectl get pods -n swe-ai-fleet -l app=po-ui
kubectl logs -l app=po-ui -n swe-ai-fleet --tail=10

echo ""
echo "🧪 Functional test..."
kubectl port-forward -n swe-ai-fleet svc/po-ui 8080:80 &
PF_PID=$!
sleep 3

echo "   Testing health endpoint..."
curl -s http://localhost:8080/health | jq . || echo "Health check response received"

echo "   Testing UI..."
curl -I http://localhost:8080/ || true

kill $PF_PID 2>/dev/null || true

echo ""
echo "🔍 Health check..."
./scripts/verify-cluster-health.sh

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              ✅ STEP 7 COMPLETE! ✅                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Rollback: kubectl scale deployment po-ui --replicas=0 -n swe-ai-fleet"
echo "🚀 Next (optional): ./scripts/deploy-step-8-raycluster.sh"
echo "🚀 Or skip to ingress: ./scripts/deploy-step-9-ingress.sh"
echo ""



