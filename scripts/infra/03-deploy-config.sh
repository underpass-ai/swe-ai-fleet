#!/bin/bash
# Step 3: Deploy ConfigMap (FSM + Rigor)

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Step 3: Deploy ConfigMap (FSM + Rigor Profiles)             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check namespace exists
if ! kubectl get namespace swe-ai-fleet &>/dev/null; then
  echo "❌ Namespace swe-ai-fleet not found!"
  exit 1
fi

echo "📝 Dry-run..."
kubectl apply -f ../../deploy/k8s/03-configmaps.yaml --dry-run=client

echo ""
read -p "Deploy ConfigMap? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
  echo "Aborted"
  exit 0
fi

echo ""
echo "🚀 Deploying ConfigMap..."
kubectl apply -f ../../deploy/k8s/03-configmaps.yaml

echo ""
echo "✅ Verifying..."
kubectl get configmap -n swe-ai-fleet
kubectl describe configmap fleet-config -n swe-ai-fleet | head -30

echo ""
echo "📋 FSM States:"
kubectl get configmap fleet-config -n swe-ai-fleet -o jsonpath='{.data.agile\.fsm\.yaml}' | grep -A 10 "states:"

echo ""
echo "🔍 Health check..."
./scripts/verify-cluster-health.sh

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              ✅ STEP 3 COMPLETE! ✅                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Rollback command (if needed):"
echo "  kubectl delete configmap fleet-config -n swe-ai-fleet"
echo ""
echo "🚀 Next step:"
echo "  ./scripts/deploy-step-4-planning.sh"
echo ""



