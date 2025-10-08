#!/bin/bash
# Verify existing Kubernetes cluster health before deployment
# Run this script before and after deployment to ensure nothing broke

set -e

echo "🔍 Kubernetes Cluster Health Check"
echo "===================================="
echo ""

FAILED=0

check_pods() {
    local namespace=$1
    local component=$2
    
    echo -n "Checking $component ($namespace)... "
    
    local running=$(kubectl get pods -n "$namespace" 2>/dev/null | grep -c "Running" | tr -d '\n' || echo 0)
    local completed=$(kubectl get pods -n "$namespace" 2>/dev/null | grep -c "Completed" | tr -d '\n' || echo 0)
    local total=$(kubectl get pods -n "$namespace" 2>/dev/null | tail -n +2 | wc -l | tr -d '\n' || echo 0)
    
    if [ "$total" -eq 0 ]; then
        echo "⚠️  Not found (okay if not installed)"
        return 0
    fi
    
    # Consider both Running and Completed pods as healthy
    local healthy=$(($running + $completed))
    
    if [ "$healthy" -eq "$total" ]; then
        if [ "$completed" -gt 0 ]; then
            echo "✅ All pods healthy ($running Running, $completed Completed)"
        else
            echo "✅ All pods Running ($running/$total)"
        fi
        return 0
    else
        echo "❌ Some pods not healthy ($running Running, $completed Completed, $total total)"
        kubectl get pods -n "$namespace" | grep -v -E "Running|Completed" || true
        FAILED=1
        return 1
    fi
}

check_helm_release() {
    local release=$1
    local namespace=$2
    
    echo -n "Checking Helm release $release... "
    
    if helm list -n "$namespace" 2>/dev/null | grep -q "$release"; then
        local status=$(helm list -n "$namespace" | grep "$release" | awk '{print $8}')
        echo "✅ Found ($status)"
        return 0
    else
        echo "⚠️  Not found"
        return 0
    fi
}

check_clusterissuer() {
    local name=$1
    
    echo -n "Checking ClusterIssuer $name... "
    
    if kubectl get clusterissuer "$name" &>/dev/null; then
        local ready=$(kubectl get clusterissuer "$name" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")
        if [ "$ready" = "True" ]; then
            echo "✅ Ready"
            return 0
        else
            echo "⚠️  Status: $ready"
            return 0
        fi
    else
        echo "⚠️  Not found"
        return 0
    fi
}

echo "📦 Checking Existing Components"
echo "================================"
echo ""

check_pods "cert-manager" "cert-manager"
check_pods "ingress-nginx" "ingress-nginx"
check_pods "nvidia" "NVIDIA GPU Operator"
check_pods "ray-system" "KubeRay Operator"
check_pods "llm" "OpenWebUI"

echo ""
echo "⚙️  Checking Helm Releases"
echo "=========================="
echo ""

check_helm_release "cert-manager" "cert-manager"
check_helm_release "ingress-nginx" "ingress-nginx"
check_helm_release "gpu-operator" "nvidia"
check_helm_release "kuberay-operator" "ray-system"

echo ""
echo "🔐 Checking ClusterIssuers"
echo "=========================="
echo ""

check_clusterissuer "letsencrypt-prod-r53"
check_clusterissuer "letsencrypt-staging-r53"

echo ""
echo "📊 Checking SWE AI Fleet (if deployed)"
echo "======================================="
echo ""

if kubectl get namespace swe-ai-fleet &>/dev/null; then
    echo "Namespace: ✅ Found"
    check_pods "swe-ai-fleet" "SWE AI Fleet"
    
    echo ""
    echo "Services:"
    kubectl get svc -n swe-ai-fleet 2>/dev/null || echo "  None"
    
    echo ""
    echo "Ingress:"
    kubectl get ingress -n swe-ai-fleet 2>/dev/null || echo "  None"
    
    echo ""
    echo "Certificates:"
    kubectl get certificate -n swe-ai-fleet 2>/dev/null || echo "  None"
    
    echo ""
    echo "RayClusters:"
    kubectl get raycluster -n swe-ai-fleet 2>/dev/null || echo "  None"
else
    echo "Namespace: ⚠️  Not found (not deployed yet)"
fi

echo ""
echo "================================"

if [ $FAILED -eq 0 ]; then
    echo "✅ Cluster Health: GOOD"
    echo ""
    echo "Safe to proceed with deployment!"
    exit 0
else
    echo "❌ Cluster Health: ISSUES FOUND"
    echo ""
    echo "Fix issues before deploying SWE AI Fleet"
    exit 1
fi

