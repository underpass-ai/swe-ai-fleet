#!/bin/bash
# Setup Amazon WorkMail for underpassai.com
# Prerequisites: AWS CLI configured, Route 53 domain

set -e

DOMAIN="underpassai.com"
ORG_NAME="UnderpassAI"
REGION="eu-west-1"  # Ireland - closest to Spain with WorkMail support
EMAIL="contact@underpassai.com"
DISPLAY_NAME="Underpass AI Support"

echo "🚀 Setting up Amazon WorkMail for ${DOMAIN}"
echo ""

# Step 1: Create WorkMail Organization
echo "📦 Step 1: Creating WorkMail organization..."
ORG_ID=$(aws workmail create-organization \
  --alias underpassai \
  --region ${REGION} \
  --query 'OrganizationId' \
  --output text 2>&1)

if [[ $? -ne 0 ]]; then
  echo "⚠️  Organization may already exist. Listing organizations..."
  aws workmail list-organizations --region ${REGION}
  echo ""
  echo "Enter your Organization ID (or press Ctrl+C to exit):"
  read ORG_ID
fi

echo "✅ Organization ID: ${ORG_ID}"
echo ""

# Step 2: Add domain to WorkMail
echo "📧 Step 2: Adding domain ${DOMAIN} to WorkMail..."
aws workmail register-mail-domain \
  --organization-id ${ORG_ID} \
  --domain-name ${DOMAIN} \
  --region ${REGION} 2>&1 || echo "⚠️  Domain may already be registered"

echo "✅ Domain registered"
echo ""

# Step 3: Wait for domain verification
echo "⏳ Step 3: Waiting for domain verification..."
echo "   WorkMail is configuring DNS records in Route 53..."
sleep 10

# Check domain status
aws workmail describe-organization \
  --organization-id ${ORG_ID} \
  --region ${REGION}

echo ""
echo "✅ Domain configuration in progress"
echo ""

# Step 4: Create user
echo "👤 Step 4: Creating user mailbox..."
echo "   Email: ${EMAIL}"
echo "   Display Name: ${DISPLAY_NAME}"
echo ""
echo "Enter a password for ${EMAIL}:"
read -s PASSWORD
echo ""

aws workmail create-user \
  --organization-id ${ORG_ID} \
  --name contact \
  --display-name "${DISPLAY_NAME}" \
  --password "${PASSWORD}" \
  --region ${REGION}

echo "✅ User created"
echo ""

# Step 5: Register user to WorkMail
echo "📬 Step 5: Registering user to WorkMail..."
USER_ID=$(aws workmail list-users \
  --organization-id ${ORG_ID} \
  --region ${REGION} \
  --query "Users[?Name=='contact'].Id" \
  --output text)

aws workmail register-to-work-mail \
  --organization-id ${ORG_ID} \
  --entity-id ${USER_ID} \
  --email ${EMAIL} \
  --region ${REGION}

echo "✅ User registered"
echo ""

# Step 6: Show webmail access
echo "═══════════════════════════════════════════════════════"
echo "✅ Amazon WorkMail Setup Complete!"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "📧 Email: ${EMAIL}"
echo "🌐 Webmail: https://underpassai.awsapps.com/mail"
echo "📱 Mobile: Use AWS WorkMail app"
echo ""
echo "🔧 IMAP/SMTP Settings:"
echo "   IMAP Server: imap.mail.${REGION}.awsapps.com:993 (SSL)"
echo "   SMTP Server: smtp.mail.${REGION}.awsapps.com:465 (SSL)"
echo "   Username: ${EMAIL}"
echo ""
echo "📋 Next Steps:"
echo "   1. Wait 5-10 minutes for DNS propagation"
echo "   2. Login to webmail: https://underpassai.awsapps.com/mail"
echo "   3. Test sending/receiving emails"
echo ""
echo "💡 To create additional aliases:"
echo "   aws workmail create-alias --organization-id ${ORG_ID} --entity-id ${USER_ID} --alias info@underpassai.com --region ${REGION}"
echo ""
echo "═══════════════════════════════════════════════════════"

