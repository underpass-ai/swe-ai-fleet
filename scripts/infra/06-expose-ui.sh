#!/bin/bash
# Exponer UI vía ingress con dominio personalizable

set -e

DEFAULT_DOMAIN="swe-fleet.underpassai.com"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     🌐 Exponer PO Planner UI                                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Dominio actual: $DEFAULT_DOMAIN"
echo ""
read -p "¿Usar este dominio? (y/n): " USE_DEFAULT

if [ "$USE_DEFAULT" = "n" ]; then
  read -p "Ingresa tu dominio (ej: swe-fleet.midominio.com): " CUSTOM_DOMAIN
  
  echo ""
  echo "📝 Actualizando ingress con dominio: $CUSTOM_DOMAIN"
  
  sed -i "s|swe-fleet.underpassai.com|$CUSTOM_DOMAIN|g" ../../deploy/k8s/05-ui-ingress.yaml
  
  DOMAIN=$CUSTOM_DOMAIN
else
  DOMAIN=$DEFAULT_DOMAIN
fi

echo ""
echo "🚀 Desplegando ingress..."
kubectl apply -f ../../deploy/k8s/05-ui-ingress.yaml

echo ""
echo "📝 Creando DNS record en Route53..."

# Get ingress IP
INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Get Hosted Zone ID from environment or prompt user
if [ -z "$AWS_HOSTED_ZONE_ID" ]; then
  echo ""
  echo "⚠️  AWS_HOSTED_ZONE_ID not set"
  read -p "Enter your Route53 Hosted Zone ID: " HOSTED_ZONE_ID
  
  if [ -z "$HOSTED_ZONE_ID" ]; then
    echo "❌ Hosted Zone ID required for DNS setup"
    exit 1
  fi
else
  HOSTED_ZONE_ID="$AWS_HOSTED_ZONE_ID"
  echo "Using Hosted Zone ID from environment: $HOSTED_ZONE_ID"
fi

# Create DNS
aws route53 change-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "'"$DOMAIN"'",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "'"$INGRESS_IP"'"}]
      }
    }]
  }' --output text

echo ""
echo "✅ DNS record creado: $DOMAIN → $INGRESS_IP"
echo ""
echo "⏳ Esperando certificado TLS (1-2 minutos)..."

sleep 10

for i in {1..12}; do
  STATUS=$(kubectl get certificate po-ui-tls -n swe-ai-fleet -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
  if [ "$STATUS" = "True" ]; then
    echo "✅ Certificado TLS listo!"
    break
  fi
  echo "  Esperando certificado... ($i/12)"
  sleep 10
done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              ✅ UI EXPUESTA! ✅                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Accede a tu UI:"
echo "  https://$DOMAIN"
echo ""
echo "🔍 Verificar:"
echo "  curl -I https://$DOMAIN"
echo ""
