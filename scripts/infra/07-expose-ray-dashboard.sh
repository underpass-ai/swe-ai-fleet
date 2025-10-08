#!/bin/bash
# Exponer Ray Dashboard vía ingress con TLS

set -e

DEFAULT_DOMAIN="ray.underpassai.com"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     📊 Exponer Ray Dashboard                                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Dominio por defecto: $DEFAULT_DOMAIN"
echo ""
read -p "¿Usar este dominio? (y/n): " USE_DEFAULT

if [ "$USE_DEFAULT" = "n" ]; then
  read -p "Ingresa tu dominio (ej: ray.midominio.com): " CUSTOM_DOMAIN
  
  echo ""
  echo "📝 Actualizando ingress con dominio: $CUSTOM_DOMAIN"
  
  sed -i "s|ray.underpassai.com|$CUSTOM_DOMAIN|g" ../../deploy/k8s/06-ray-dashboard-ingress.yaml
  
  DOMAIN=$CUSTOM_DOMAIN
else
  DOMAIN=$DEFAULT_DOMAIN
fi

echo ""
echo "🚀 Desplegando servicio e ingress..."
kubectl apply -f ../../deploy/k8s/06-ray-dashboard-ingress.yaml

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
  STATUS=$(kubectl get certificate ray-dashboard-tls -n ray -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
  if [ "$STATUS" = "True" ]; then
    echo "✅ Certificado TLS listo!"
    break
  fi
  echo "  Esperando certificado... ($i/12)"
  sleep 10
done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         ✅ RAY DASHBOARD EXPUESTO! ✅                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Accede al dashboard:"
echo "  https://$DOMAIN"
echo ""
echo "📊 Features del dashboard:"
echo "  • Estado del cluster (head + workers)"
echo "  • Jobs en ejecución"
echo "  • Uso de CPU/GPU/Memoria"
echo "  • Logs de tasks"
echo "  • Métricas en tiempo real"
echo ""
echo "🔍 Verificar:"
echo "  curl -I https://$DOMAIN"
echo ""
