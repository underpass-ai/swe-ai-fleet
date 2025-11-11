# Infrastructure Deployment Scripts

Scripts for deploying SWE AI Fleet to Kubernetes.

---

## 🚀 Quick Start

```bash
# Deploy to cluster (MAIN COMMAND)
./fresh-redeploy.sh

# Verify system health
./verify-health.sh

# Deploy with clean NATS streams
./fresh-redeploy.sh --reset-nats
```

---

## 📋 Main Scripts

### `fresh-redeploy.sh` ⭐ MAIN SCRIPT

**Use for:** Redeploying after code changes, git pull, feature merges

```bash
# Full rebuild and redeploy (default)
./fresh-redeploy.sh

# Skip building images (only redeploy)
./fresh-redeploy.sh --skip-build

# Also reset NATS streams (clean slate)
./fresh-redeploy.sh --reset-nats
```

**What it does:**
0. Cleans up zombie pods (Unknown status) - prevents vLLM restart issues
1. Scales down services with NATS consumers (releases durable consumers)
2. Rebuilds all service images (orchestrator, ray-executor, context, planning, monitoring)
3. Pushes images to registry (`registry.underpassai.com`)
4. Updates Kubernetes deployments
5. Scales services back up
6. Verifies pod health

**Duration:** ~8-12 minutes (full rebuild)
**Duration:** ~2-3 minutes (--skip-build)

**Services redeployed:**
- Orchestrator: `v3.0.0-{timestamp}`
- Ray-Executor: `v3.0.0-{timestamp}`
- Context: `v2.0.0-{timestamp}`
- Planning: `v2.0.0-{timestamp}`
- Workflow: `v1.0.0-{timestamp}`
- Monitoring: `v3.2.1-{timestamp}`

---

### `verify-health.sh`

**Use for:** Checking system status

```bash
./verify-health.sh
```

**Output:**
```
✓ NATS:         Running (1/1)
✓ Orchestrator: Running (1/1)
✓ Context:      Running (2/2)
✓ Planning:     Running (2/2)
✓ Ray-Executor: Running (1/1)
✓ Monitoring:   Running (1/1)
```

---

### `00-verify-prerequisites.sh`

**Use for:** Check cluster requirements before first deployment

```bash
./00-verify-prerequisites.sh
```

**Checks:**
- kubectl installed and configured
- Cluster accessible
- cert-manager ready
- ingress-nginx ready
- Podman installed

---

## 📂 Individual Step Scripts (Advanced)

These scripts are called by `deploy-all.sh`. Use only for debugging or manual deployments.

| Script | Description | When to Use |
|--------|-------------|-------------|
| `01-deploy-namespace.sh` | Create swe-ai-fleet namespace | Manual setup |
| `02-deploy-nats.sh` | Deploy NATS JetStream | Debugging NATS |
| `03-deploy-config.sh` | Deploy ConfigMaps | Config changes |
| `04-deploy-services.sh` | Deploy all microservices | Manual service deploy |
| `06-expose-ui.sh` | Expose UI via Ingress | UI setup |
| `07-expose-ray-dashboard.sh` | Expose Ray Dashboard | Ray debugging |
| `08-deploy-context.sh` | Deploy context service | Context-specific debug |

**For normal operations, always use `fresh-redeploy.sh` instead.**

---

## 🔧 Common Workflows

### After Merging Feature Branch

```bash
# 1. Update main
git checkout main
git pull origin main

# 2. Redeploy
./fresh-redeploy.sh

# 3. Verify
./verify-health.sh
```

### After Hotfix

```bash
# 1. Apply fix, commit, push
git commit -am "fix: bug"
git push origin main

# 2. Quick redeploy
./fresh-redeploy.sh

# 3. Verify
kubectl logs -n swe-ai-fleet -l app=orchestrator --tail=50
```

### Testing Feature Branch

```bash
# Deploy from feature branch
git checkout feature/my-feature
./fresh-redeploy.sh

# Test...

# If issues, fix and redeploy
git commit -am "fix: issue"
./fresh-redeploy.sh
```

---

## 🎯 Why fresh-redeploy.sh?

**Handles NATS consumer conflicts:**
- Services with NATS durable consumers can't do rolling updates
- Must scale to 0 first to release consumers
- `fresh-redeploy.sh` automates this ✅

**Services with NATS consumers:**
- Orchestrator (subscribes to planning events, agent responses)
- Context (subscribes to orchestration events)
- Planning (publishes story events)
- Monitoring (subscribes to all events)

**Without scaling to 0:**
```
Error: consumer is already bound to a subscription
Pod: CrashLoopBackOff
```

**With fresh-redeploy.sh:**
```
✓ Scales to 0 (releases consumers)
✓ Rebuilds and pushes images
✓ Updates deployments
✓ Scales back up (fresh subscriptions)
✓ Verifies health
```

---

## 📊 Deployment Checklist

### Before Deploying

- [ ] All tests passing (`make test-unit`)
- [ ] Coverage ≥ 85%
- [ ] Code committed and pushed
- [ ] In correct branch (main or feature)

### During Deployment

- [ ] Run `./fresh-redeploy.sh`
- [ ] Monitor logs in separate terminal
- [ ] Watch for CrashLoopBackOff

### After Deployment

- [ ] Run `./verify-health.sh`
- [ ] Check logs for errors
- [ ] Test basic functionality
- [ ] Monitor for 5-10 minutes

---

## ⚠️ Prerequisites

Before running any script:

1. **Kubernetes Cluster**
   - Version 1.28+
   - `kubectl` configured to correct context

2. **Installed Components**
   - cert-manager (for TLS)
   - ingress-nginx (for external access)

3. **Tools**
   - Podman (for building images)
   - bash shell
   - kubectl CLI

4. **Registry Access**
   - `registry.underpassai.com` accessible
   - Credentials configured (if private)

**Verify:**
```bash
./00-verify-prerequisites.sh
```

---

## 📚 Related Documentation

- [Deployment Operations](../../docs/operations/DEPLOYMENT.md) - Detailed deployment guide
- [K8S Troubleshooting](../../docs/operations/K8S_TROUBLESHOOTING.md) - Issue resolution
- [Getting Started](../../docs/getting-started/README.md) - First-time setup

---

**Maintained by**: Tirso García
**Last Updated**: 2025-11-11 (Added STEP 0: zombie pod cleanup, fixes vLLM restart issues)
