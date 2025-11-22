# 🔧 Troubleshooting Guide

> Comprehensive reference: Kubernetes (K8s) + CRI-O operational troubleshooting

---

## 🚀 Quick Diagnostics

### Kubernetes Cluster

```bash
# Namespace summary
kubectl -n swe-ai-fleet get all,ingress,secrets,events

# Focus on a component
kubectl -n swe-ai-fleet get deploy,rs,pod -l app=neo4j -o wide
kubectl -n swe-ai-fleet describe pod -l app=neo4j | sed -n '/Events:/,$p'

# Logs
kubectl -n swe-ai-fleet logs deploy/neo4j --tail=200 | cat
kubectl -n swe-ai-fleet logs -l app=neo4j --tail=200 --prefix | cat
kubectl -n swe-ai-fleet logs -l app=neo4j --previous --tail=200 | cat
```

---

## 🔴 Common Issues

- CrashLoopBackOff
- ImagePullBackOff
- Rollout timeouts
- Secrets validation
- ContainerStatusUnknown after node restart

See the archived full guide for advanced CRI-O diagnostics if needed.

---

## 📋 Policy: Rollout Timeouts

Standard timeout for all rollout operations:

```bash
--timeout=120s
```

Use this consistently in:
- `kubectl rollout status`
- `kubectl wait --for=...`
- `kubectl scale`

---

## 🆘 When All Else Fails

### Nuclear Option: Full Reset

```bash
# Delete entire namespace and recreate
kubectl delete namespace swe-ai-fleet
kubectl wait --for=delete namespace/swe-ai-fleet --timeout=120s

# Recreate from scratch
./scripts/infra/fresh-redeploy.sh --reset-nats
```

---

## 🔗 Related

- `DEPLOYMENT.md` - Deployment procedures
- `deploy/k8s/README.md` - K8s layout and tips

