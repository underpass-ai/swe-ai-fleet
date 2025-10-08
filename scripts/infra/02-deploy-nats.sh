#!/bin/bash
# Step 2: Deploy NATS JetStream

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Step 2: Deploy NATS JetStream                               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check namespace exists
if ! kubectl get namespace swe-ai-fleet &>/dev/null; then
  echo "❌ Namespace swe-ai-fleet not found!"
  echo "Run: ./scripts/deploy-step-1-namespace.sh"
  exit 1
fi

echo "📝 Dry-run..."
kubectl apply -f ../../deploy/k8s/01-nats.yaml --dry-run=client
kubectl apply -f ../../deploy/k8s/02-nats-internal-dns.yaml --dry-run=client

echo ""
read -p "Deploy NATS? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
  echo "Aborted"
  exit 0
fi

echo ""
echo "🚀 Deploying NATS..."
kubectl apply -f ../../deploy/k8s/01-nats.yaml
kubectl apply -f ../../deploy/k8s/02-nats-internal-dns.yaml

echo ""
echo "⏳ Waiting for NATS pod to be ready (max 2 minutes)..."
kubectl wait --for=condition=ready pod -l app=nats -n swe-ai-fleet --timeout=120s

echo ""
echo "✅ Verifying..."
kubectl get pods -n swe-ai-fleet -l app=nats
kubectl get svc -n swe-ai-fleet -l app=nats
kubectl get pvc -n swe-ai-fleet

echo ""
echo "📋 NATS Logs:"
kubectl logs -l app=nats -n swe-ai-fleet --tail=15

echo ""
echo "🔍 Health check..."
./scripts/verify-cluster-health.sh

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              ✅ STEP 2 COMPLETE! ✅                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Rollback command (if needed):"
echo "  kubectl delete -f ../../deploy/k8s/01-nats.yaml"
echo "  kubectl delete -f ../../deploy/k8s/02-nats-internal-dns.yaml"
echo ""
echo "🚀 Next step:"
echo "  ./scripts/deploy-step-3-config.sh"
echo ""



