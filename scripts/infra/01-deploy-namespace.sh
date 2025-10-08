#!/bin/bash
# Step 1: Deploy Namespace (SAFE - isolated)

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Step 1: Deploy Namespace swe-ai-fleet                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Pre-check
echo "🔍 Pre-deployment health check..."
./scripts/verify-cluster-health.sh || exit 1

echo ""
echo "📝 Dry-run..."
kubectl apply -f ../../deploy/k8s/00-namespace.yaml --dry-run=client

echo ""
read -p "Apply namespace? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
  echo "Aborted"
  exit 0
fi

echo ""
echo "🚀 Creating namespace..."
kubectl apply -f ../../deploy/k8s/00-namespace.yaml

echo ""
echo "✅ Verifying..."
kubectl get namespace swe-ai-fleet
kubectl describe namespace swe-ai-fleet

echo ""
echo "🔍 Post-deployment health check..."
./scripts/verify-cluster-health.sh

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              ✅ STEP 1 COMPLETE! ✅                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Rollback command (if needed):"
echo "  kubectl delete namespace swe-ai-fleet"
echo ""
echo "🚀 Next step:"
echo "  ./scripts/deploy-step-2-nats.sh"
echo ""



