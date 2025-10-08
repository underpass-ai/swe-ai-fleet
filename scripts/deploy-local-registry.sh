#!/bin/bash
# Deploy local Docker Registry in Kubernetes with Ingress

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     🐳 Deploy Local Registry - registry.underpassai.com      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Get ingress IP
echo "🔍 Getting ingress-nginx LoadBalancer IP..."
INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

if [ -z "$INGRESS_IP" ]; then
  echo "❌ Could not get ingress IP!"
  exit 1
fi

echo "✓ Ingress IP: $INGRESS_IP"
echo ""

# Check storage class
echo "🔍 Checking available storage classes..."
kubectl get storageclass
echo ""

read -p "Enter storage class name [local-path]: " STORAGE_CLASS
STORAGE_CLASS=${STORAGE_CLASS:-local-path}

# Update manifest with storage class
sed -i "s|storageClassName: local-path|storageClassName: $STORAGE_CLASS|g" deploy/k8s/06-registry.yaml

echo ""
echo "📦 Deploying Docker Registry..."

# Deploy registry
kubectl apply -f deploy/k8s/06-registry.yaml

echo ""
echo "⏳ Waiting for registry pod to be ready..."
kubectl wait --for=condition=ready pod -l app=docker-registry -n container-registry --timeout=120s || true

echo ""
echo "🔒 Waiting for TLS certificate..."
echo "   (This may take 1-2 minutes for Let's Encrypt)"
sleep 10

# Check certificate
for i in {1..12}; do
  if kubectl get certificate -n container-registry registry-tls &>/dev/null; then
    STATUS=$(kubectl get certificate -n container-registry registry-tls -o jsonpath='{.status.conditions[0].status}')
    if [ "$STATUS" = "True" ]; then
      echo "✅ TLS certificate ready!"
      break
    fi
  fi
  echo "   Waiting for certificate... ($i/12)"
  sleep 10
done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 ✅ REGISTRY DEPLOYED! ✅                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Registry Details:"
echo "  • URL: https://registry.underpassai.com"
echo "  • Ingress IP: $INGRESS_IP"
echo "  • Namespace: container-registry"
echo "  • Storage: 100Gi PVC"
echo ""
echo "🔍 Check status:"
echo "  kubectl get all -n container-registry"
echo "  kubectl get ingress -n container-registry"
echo "  kubectl get certificate -n container-registry"
echo ""
echo "📝 Next Steps:"
echo "  1. Create Route53 DNS record:"
echo "     ./scripts/create-registry-dns.sh"
echo ""
echo "  2. Test registry:"
echo "     curl https://registry.underpassai.com/v2/"
echo ""
echo "  3. Push images:"
echo "     ./scripts/push-to-local-registry.sh"
echo ""



