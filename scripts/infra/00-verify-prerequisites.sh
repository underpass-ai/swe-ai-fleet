#!/bin/bash
# Verify prerequisites for deploying SWE AI Fleet

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     🔍 Verify Prerequisites                                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

ERRORS=0

# Check kubectl
echo "Checking kubectl..."
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found"
    ERRORS=$((ERRORS + 1))
else
    KUBECTL_VERSION=$(kubectl version --client --short 2>/dev/null || kubectl version --client | grep "Client Version" | cut -d: -f2)
    echo "✅ kubectl found: $KUBECTL_VERSION"
fi

# Check cluster connection
echo ""
echo "Checking Kubernetes cluster connection..."
if kubectl cluster-info &> /dev/null; then
    echo "✅ Connected to cluster"
    kubectl cluster-info | head -1
else
    echo "❌ Cannot connect to Kubernetes cluster"
    ERRORS=$((ERRORS + 1))
fi

# Check nodes
echo ""
echo "Checking nodes..."
NODE_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
if [ "$NODE_COUNT" -gt 0 ]; then
    echo "✅ Found $NODE_COUNT node(s)"
    kubectl get nodes
else
    echo "❌ No nodes found"
    ERRORS=$((ERRORS + 1))
fi

# Check GPU support
echo ""
echo "Checking GPU support..."
GPU_COUNT=$(kubectl get nodes -o json 2>/dev/null | grep "nvidia.com/gpu" | wc -l)
if [ "$GPU_COUNT" -gt 0 ]; then
    echo "✅ GPU support detected"
    kubectl describe nodes | grep -A 5 "nvidia.com/gpu"
else
    echo "⚠️  No GPU support detected (optional for basic deployment)"
fi

# Check cert-manager
echo ""
echo "Checking cert-manager..."
if kubectl get namespace cert-manager &> /dev/null; then
    echo "✅ cert-manager found"
else
    echo "❌ cert-manager not found (required for TLS certificates)"
    ERRORS=$((ERRORS + 1))
fi

# Check ingress-nginx
echo ""
echo "Checking ingress-nginx..."
if kubectl get namespace ingress-nginx &> /dev/null; then
    echo "✅ ingress-nginx found"
else
    echo "❌ ingress-nginx not found (required for external access)"
    ERRORS=$((ERRORS + 1))
fi

# Check for existing deployment
echo ""
echo "Checking for existing deployment..."
if kubectl get namespace swe-ai-fleet &> /dev/null; then
    echo "⚠️  swe-ai-fleet namespace already exists"
    echo "    To redeploy, first run: kubectl delete namespace swe-ai-fleet"
else
    echo "✅ No existing deployment found"
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$ERRORS" -eq 0 ]; then
    echo "✅ All prerequisites met! Ready to deploy."
    echo ""
    echo "Next step:"
    echo "  ./deploy-all.sh"
else
    echo "❌ $ERRORS prerequisite(s) missing. Please fix before deploying."
    exit 1
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
