# Security Review - Before Going Public

## ✅ What's Safe to Commit

### Domain Names
- `underpassai.com` - Your public domain (OK to share)
- `swe-fleet.underpassai.com` - Public UI URL (OK)
- `registry.underpassai.com` - Public registry URL (OK)
- `ray.underpassai.com` - Public dashboard URL (OK)

### Configuration
- Kubernetes manifests (no secrets embedded)
- Scripts (parametrized, no hardcoded credentials)
- Documentation (no private information)

## ⚠️ What Was Parametrized

### AWS Hosted Zone ID
**Before:** Hardcoded in scripts
**After:** Uses `$AWS_HOSTED_ZONE_ID` environment variable or prompts user

**Scripts updated:**
- `scripts/infra/06-expose-ui.sh`
- `scripts/infra/07-expose-ray-dashboard.sh`
- `scripts/expose-ui.sh`
- `scripts/expose-ray-dashboard.sh`

**Usage:**
```bash
# Set once
export AWS_HOSTED_ZONE_ID=Z0XXXXXXXXXXXXXXXXX

# Or script will prompt:
./scripts/infra/06-expose-ui.sh
# → Enter your Route53 Hosted Zone ID: Z0XXXXXXXXXXXXXXXXX
```

## 🔒 What's Protected

### .gitignore Includes
- `cluster-state/` - Your actual cluster configuration
- `.env` - Local environment variables
- `.venv/` - Python virtual environment
- `__pycache__/` - Python cache
- `*.pyc` - Compiled Python
- `.coverage` - Coverage reports

### Kubernetes Secrets
- TLS certificates managed by cert-manager
- AWS credentials in Secret `route53-credentials-secret` (not in repo)
- No secrets in manifests (all use cert-manager annotations)

## 📋 Files to Review Before Public

### Configuration Files
- [ ] `config.env.example` - Template for users (no real values)
- [ ] `deploy/k8s/*.yaml` - Domain names (yours are OK to share)
- [ ] `scripts/**/*.sh` - All parametrized

### Documentation
- [ ] No internal IPs or private network topology
- [ ] No AWS account IDs or credentials
- [ ] No private code examples

## 🛡️ Recommended .gitignore Additions

Already included:
```
cluster-state/
.env
.venv/
*.pyc
__pycache__/
.coverage
```

## ✅ Verification Checklist

Run before pushing:

```bash
# Check for AWS credentials
grep -r "AKIA" . --exclude-dir=.git --exclude-dir=node_modules

# Check for private IPs (beyond examples)
grep -r "192.168\|10\.\|172\.(1[6-9]|2[0-9]|3[0-1])\." . \
  --exclude-dir=.git --exclude-dir=node_modules \
  --include="*.yaml" --include="*.sh"

# Check for secrets
grep -ri "password.*=\|secret.*=\|token.*=" . \
  --exclude-dir=.git --exclude-dir=node_modules \
  --include="*.yaml" --include="*.env"

# Check for Hosted Zone IDs
grep -r "Z[0-9A-Z]\{15,\}" . \
  --exclude-dir=.git --exclude-dir=node_modules \
  --include="*.yaml" --include="*.sh" --include="*.md"
```

## 📝 User Configuration Guide

For new users, they should:

1. **Copy config template:**
   ```bash
   cp config.env.example .env
   ```

2. **Edit .env with their values:**
   ```bash
   AWS_HOSTED_ZONE_ID=Z0THEIR_ZONE_ID_HERE
   ```

3. **Edit ingress YAMLs with their domains:**
   ```yaml
   # deploy/k8s/05-ui-ingress.yaml
   - host: swe-fleet.theirdomain.com  # ← Change this
   ```

4. **Run deployment:**
   ```bash
   source .env
   ./scripts/infra/deploy-all.sh
   ```

## 🔐 AWS IAM Permissions Required

Document the minimum IAM policy users need:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "route53:ChangeResourceRecordSets",
        "route53:GetChange",
        "route53:ListHostedZones",
        "route53:ListResourceRecordSets"
      ],
      "Resource": "*"
    }
  ]
}
```

## ✅ Final Verification

All sensitive data has been:
- ✅ Parametrized (AWS Hosted Zone ID)
- ✅ Moved to .gitignore (cluster-state/)
- ✅ Documented for users (config.env.example)
- ✅ No hardcoded credentials
- ✅ No private network topology exposed
