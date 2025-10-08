#!/bin/bash
# Create Route53 DNS A record for registry.underpassai.com

set -e

DOMAIN="underpassai.com"
SUBDOMAIN="registry.underpassai.com"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     📝 Create DNS Record for registry.underpassai.com        ║"
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

# Get hosted zone ID
echo "🔍 Finding Route53 Hosted Zone for $DOMAIN..."
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name \
  --query "HostedZones[?Name=='${DOMAIN}.'].Id" \
  --output text | cut -d'/' -f3)

if [ -z "$HOSTED_ZONE_ID" ]; then
  echo "❌ Hosted zone for $DOMAIN not found!"
  exit 1
fi

echo "✓ Found hosted zone: $HOSTED_ZONE_ID"
echo ""

# Create change batch
CHANGE_BATCH=$(cat <<EOF
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "$SUBDOMAIN",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [
          {
            "Value": "$INGRESS_IP"
          }
        ]
      }
    }
  ]
}
EOF
)

echo "📝 DNS Record to create:"
echo "  Domain: $SUBDOMAIN"
echo "  Type: A"
echo "  Value: $INGRESS_IP"
echo "  TTL: 300"
echo ""

read -p "Create this DNS record? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
  echo "Aborted"
  exit 0
fi

# Save to temp file
TEMP_FILE="/tmp/route53-registry-$$.json"
echo "$CHANGE_BATCH" > "$TEMP_FILE"

# Apply the change
echo ""
echo "🚀 Creating DNS record..."
CHANGE_ID=$(aws route53 change-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --change-batch file://"$TEMP_FILE" \
  --query "ChangeInfo.Id" \
  --output text)

rm "$TEMP_FILE"

echo "✅ DNS record created!"
echo "Change ID: $CHANGE_ID"
echo ""

echo "⏳ Waiting for DNS propagation..."
aws route53 wait resource-record-sets-changed --id "$CHANGE_ID"

echo "✅ DNS propagated!"
echo ""
echo "🔍 Verify DNS:"
echo "  dig registry.underpassai.com"
echo "  nslookup registry.underpassai.com"
echo ""
echo "⏱️  Wait 2-3 minutes for global DNS propagation, then test:"
echo "  curl https://registry.underpassai.com/v2/"
echo ""



