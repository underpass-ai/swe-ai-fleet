#!/bin/bash
# Push images to local registry at registry.underpassai.com

set -e

REGISTRY="registry.underpassai.com"
VERSION="v0.1.0"
IMAGES="planning storycoach workspace worker ui agent-workspace"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     📤 Push Images to Local Registry                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Test registry connection
echo "🔍 Testing registry connection..."
if ! curl -f -k https://$REGISTRY/v2/ &>/dev/null; then
  echo "❌ Cannot connect to registry!"
  echo ""
  echo "Troubleshooting:"
  echo "  1. Check DNS: dig $REGISTRY"
  echo "  2. Check certificate: kubectl get certificate -n container-registry"
  echo "  3. Check pod: kubectl get pods -n container-registry"
  echo "  4. Check ingress: kubectl get ingress -n container-registry"
  exit 1
fi

echo "✅ Registry is accessible!"
echo ""

# Note: Local registry doesn't require login for now (no auth configured)
echo "ℹ️  No authentication configured (anonymous push/pull)"
echo ""

# Verify images exist locally
echo "🔍 Checking local images..."
for img in $IMAGES; do
  if ! podman images | grep -q "registry.underpassai.com/swe-fleet/$img.*$VERSION"; then
    echo "⚠️  Image not found: registry.underpassai.com/swe-fleet/$img:$VERSION"
    echo "   Re-tagging from localhost:5000..."
    if podman images | grep -q "localhost:5000/swe-fleet/$img.*$VERSION"; then
      podman tag localhost:5000/swe-fleet/$img:$VERSION registry.underpassai.com/swe-fleet/$img:$VERSION
      echo "   ✅ Tagged"
    else
      echo "   ❌ Source image not found!"
      exit 1
    fi
  fi
done

echo "✅ All images available locally"
echo ""

# Push images
echo "📤 Pushing images to $REGISTRY..."
echo "   (Total: ~5GB, estimated time: 5-10 minutes)"
echo ""

for img in $IMAGES; do
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📦 Pushing swe-fleet/$img:$VERSION"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  # Push with TLS skip for self-signed cert during initial testing
  podman push --tls-verify=true registry.underpassai.com/swe-fleet/$img:$VERSION
  
  echo "✅ Pushed swe-fleet/$img"
  echo ""
done

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║               ✅ ALL IMAGES PUSHED! ✅                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "🔍 Verify images in registry:"
echo "  curl https://registry.underpassai.com/v2/_catalog"
echo ""
echo "📋 List tags for an image:"
echo "  curl https://registry.underpassai.com/v2/swe-fleet/planning/tags/list"
echo ""
echo "📝 Kubernetes manifests already configured!"
echo "  • All services use registry.underpassai.com/swe-fleet/*"
echo ""
echo "🚀 Ready to deploy:"
echo "  kubectl apply -f deploy/k8s/"
echo ""



