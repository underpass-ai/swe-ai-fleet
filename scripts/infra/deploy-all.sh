#!/bin/bash
# Deploy complete SWE AI Fleet infrastructure

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       🚀 SWE AI Fleet - Full Deployment                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "This will deploy the complete SWE AI Fleet system to Kubernetes."
echo ""
read -p "Continue? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1/5: Creating namespace..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./01-deploy-namespace.sh

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2/5: Deploying NATS JetStream..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./02-deploy-nats.sh

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3/5: Deploying ConfigMaps..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./03-deploy-config.sh

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4/5: Deploying Microservices..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./04-deploy-services.sh

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5/5: Verifying health..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./verify-health.sh

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         ✅ DEPLOYMENT COMPLETE! ✅                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "🎉 SWE AI Fleet is now running in Kubernetes!"
echo ""
echo "📊 System Status:"
kubectl get pods -n swe-ai-fleet
echo ""
echo "🌐 Internal Services Available:"
echo "  • NATS: internal.nats.underpassai.com:4222"
echo "  • Planning: internal-planning:50051 (gRPC)"
echo "  • StoryCoach: internal-storycoach:50052 (gRPC)"
echo "  • Workspace: internal-workspace:50053 (gRPC)"
echo ""
echo "📝 Optional Next Steps:"
echo "  1. Expose UI publicly:"
echo "     ./06-expose-ui.sh"
echo ""
echo "  2. Expose Ray Dashboard:"
echo "     ./07-expose-ray-dashboard.sh"
echo ""
echo "  3. Deploy RayCluster for agents:"
echo "     kubectl apply -f ../../deploy/k8s-optional/raycluster-agents.yaml"
echo ""
echo "📚 Documentation: docs/getting-started/README.md"
echo ""
