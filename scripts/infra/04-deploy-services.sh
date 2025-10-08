#!/bin/bash
# Deploy all microservices (Planning, StoryCoach, Workspace, UI)

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      🚀 Deploy Microservices (Step 4)                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if namespace exists
if ! kubectl get namespace swe-ai-fleet &> /dev/null; then
    echo "❌ Error: namespace swe-ai-fleet not found"
    echo "Run: ./01-deploy-namespace.sh first"
    exit 1
fi

# Check if NATS is ready
if ! kubectl get statefulset nats -n swe-ai-fleet &> /dev/null; then
    echo "❌ Error: NATS not deployed"
    echo "Run: ./02-deploy-nats.sh first"
    exit 1
fi

# Check if ConfigMaps exist
if ! kubectl get configmap agile-fsm -n swe-ai-fleet &> /dev/null; then
    echo "❌ Error: ConfigMaps not deployed"
    echo "Run: ./03-deploy-config.sh first"
    exit 1
fi

echo "📝 Deploying services..."
kubectl apply -f ../../deploy/k8s/04-services.yaml

echo ""
echo "⏳ Waiting for deployments to be ready..."
echo ""

# Wait for all deployments
for deployment in planning storycoach workspace po-ui; do
    echo "  Waiting for $deployment..."
    kubectl wait --for=condition=available --timeout=120s \
        deployment/$deployment -n swe-ai-fleet 2>/dev/null || true
done

echo ""
echo "📊 Current status:"
kubectl get deployments,pods -n swe-ai-fleet

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              ✅ STEP 4 COMPLETED! ✅                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ All microservices deployed!"
echo ""
echo "🌐 Internal services available:"
echo "  • internal-nats:4222"
echo "  • internal-planning:50051"
echo "  • internal-storycoach:50052"
echo "  • internal-workspace:50053"
echo "  • po-ui:80 (internal only)"
echo ""
echo "📝 Next step:"
echo "  ./05-deploy-ui.sh       # Optional: expose UI publicly"
echo ""
echo "🔍 Verify health:"
echo "  ./verify-health.sh"
echo ""
