#!/bin/bash
# Run Agent Tooling E2E tests in Kubernetes cluster

set -e

NAMESPACE="swe-ai-fleet"
JOB_NAME="agent-tooling-e2e"

echo "🚀 Agent Tooling E2E Test in Kubernetes"
echo "========================================"
echo ""

# Check kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found"
    exit 1
fi

# Check cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot access Kubernetes cluster"
    exit 1
fi

echo "✓ kubectl ready"
echo "✓ Cluster accessible"
echo ""

# Delete previous job if exists
echo "🧹 Cleaning up previous test runs..."
kubectl delete job $JOB_NAME -n $NAMESPACE --ignore-not-found=true
kubectl wait --for=delete job/$JOB_NAME -n $NAMESPACE --timeout=60s 2>/dev/null || true
echo ""

# Create namespace if doesn't exist
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply K8s Job
echo "📝 Creating test job..."
kubectl apply -f "$(dirname "$0")/k8s-agent-tooling-e2e.yaml"
echo ""

# Wait for job to start
echo "⏳ Waiting for job to start..."
kubectl wait --for=condition=Ready pod -l app=agent-tooling-e2e -n $NAMESPACE --timeout=120s || true
echo ""

# Get pod name
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=agent-tooling-e2e -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD_NAME" ]; then
    echo "❌ Pod not found"
    exit 1
fi

echo "✓ Pod created: $POD_NAME"
echo ""

# Stream logs
echo "📋 Test execution logs:"
echo "======================="
kubectl logs -f $POD_NAME -n $NAMESPACE || true
echo ""

# Wait for job completion
echo "⏳ Waiting for job completion..."
kubectl wait --for=condition=Complete job/$JOB_NAME -n $NAMESPACE --timeout=300s 2>/dev/null && JOB_STATUS="complete" || JOB_STATUS="failed"
echo ""

# Get job status
echo "📊 Job Status:"
kubectl get job $JOB_NAME -n $NAMESPACE
echo ""

# Get final pod status
echo "📊 Pod Status:"
kubectl get pod $POD_NAME -n $NAMESPACE
echo ""

# Check if job succeeded
if kubectl get job $JOB_NAME -n $NAMESPACE -o jsonpath='{.status.succeeded}' | grep -q "1"; then
    echo "✅ E2E Test PASSED in cluster!"
    echo ""
    echo "Test completed successfully. Agent tools are working in Kubernetes!"
    EXIT_CODE=0
else
    echo "❌ E2E Test FAILED in cluster"
    echo ""
    echo "Showing pod logs:"
    kubectl logs $POD_NAME -n $NAMESPACE --tail=50
    EXIT_CODE=1
fi

echo ""
echo "🔍 To view full logs:"
echo "   kubectl logs $POD_NAME -n $NAMESPACE"
echo ""
echo "🧹 To cleanup:"
echo "   kubectl delete job $JOB_NAME -n $NAMESPACE"

exit $EXIT_CODE

