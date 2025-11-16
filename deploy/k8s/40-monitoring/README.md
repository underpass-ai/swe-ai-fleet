# 40-monitoring - Observability Stack

## Purpose

Monitoring and observability stack for system health, metrics, and logs.

**Apply fifth** - After microservices are running.

---

## Files

| File | Resource | Purpose | Port |
|------|----------|---------|------|
| `monitoring-dashboard.yaml` | Deployment + Service + Ingress | System health UI | 8080 |
| `grafana.yaml` | Secret + Deployment + Service | Grafana dashboards | 3000 |
| `loki.yaml` | ConfigMap + Deployment + Service | Log aggregation | 3100 |

---

## Apply Order

```bash
kubectl apply -f monitoring-dashboard.yaml
kubectl apply -f grafana.yaml
kubectl apply -f loki.yaml

# Wait for rollouts
kubectl rollout status deployment/monitoring-dashboard -n swe-ai-fleet --timeout=120s
kubectl rollout status deployment/grafana -n swe-ai-fleet --timeout=120s
kubectl rollout status deployment/loki -n swe-ai-fleet --timeout=120s
```

---

## Access

### Monitoring Dashboard
- **URL**: https://monitoring-dashboard.underpassai.com (via Ingress)
- **Purpose**: Real-time system health, NATS monitoring
- **Auth**: None (internal only)

### Grafana
- **URL**: https://grafana.underpassai.com (via `50-ingress/grafana.yaml`)
- **User**: `admin` (from secret `grafana-admin`)
- **Password**: See secret `grafana-admin`

### Loki
- **Port**: 3100 (ClusterIP, internal only)
- **Purpose**: Log aggregation backend for Grafana
- **Query**: Via Grafana datasource

---

## Dependencies

**Requires**:
- ✅ Foundation applied
- ✅ Microservices running (for metrics)
- ✅ NATS running (for monitoring dashboard)
- ✅ Secret `grafana-admin` exists

---

## Verification

```bash
# Check pods
kubectl get pods -n swe-ai-fleet -l 'app in (monitoring-dashboard,grafana,loki)'

# Check endpoints
kubectl port-forward -n swe-ai-fleet svc/monitoring-dashboard 8080:8080
# Open: http://localhost:8080

kubectl port-forward -n swe-ai-fleet svc/grafana 3000:3000
# Open: http://localhost:3000
```

---

## Troubleshooting

### Monitoring Dashboard Not Ready

```bash
# Check NATS connectivity
kubectl logs -n swe-ai-fleet -l app=monitoring-dashboard --tail=20 | grep -i "nats\\|connection"

# Common issue: NATS streams not found
# Solution: Apply 20-streams/nats-streams-init.yaml
```

### Grafana Login Issues

```bash
# Get admin password
kubectl get secret grafana-admin -n swe-ai-fleet -o jsonpath='{.data.admin-password}' | base64 -d

# Reset password
kubectl delete secret grafana-admin -n swe-ai-fleet
kubectl create secret generic grafana-admin \
  --from-literal=admin-user=admin \
  --from-literal=admin-password=NEW_PASSWORD \
  -n swe-ai-fleet
kubectl rollout restart deployment/grafana -n swe-ai-fleet
```


