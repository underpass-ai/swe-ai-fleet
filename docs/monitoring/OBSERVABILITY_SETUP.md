# SWE AI Fleet – Observability Setup (Grafana + Prometheus + Loki)

This guide documents the end-to-end setup of the observability stack in the cluster using fully qualified names, HTTPS, and automated Grafana provisioning.

---

## Prerequisites
- Kubernetes cluster with:
  - cert-manager installed with Route53 ClusterIssuer `letsencrypt-prod-r53`
  - ingress-nginx
  - MetalLB (if bare-metal) or cloud LB
- AWS CLI configured with permissions for your Route53 hosted zone
  - Find your hosted zone ID: `aws route53 list-hosted-zones --query "HostedZones[?Name=='yourdomain.com.'].Id" --output text`
- Helm installed

---

## Components and Namespaces
- Grafana (namespace: `swe-ai-fleet`)
- Prometheus (kube-prometheus-stack) (namespace: `monitoring`)
- Loki (namespace: `swe-ai-fleet`)
- Promtail (namespace: `logging`)

---

## Grafana (HTTPS + DNS)

### 1) Deploy Grafana (Deployment, Service, Secret)
Files:
- `deploy/k8s/30-grafana.yaml` – Deploys Grafana with admin secret (change the password in production).

Apply:
```bash
kubectl apply -f deploy/k8s/30-grafana.yaml
kubectl rollout status deploy/grafana -n swe-ai-fleet --timeout=120s
```

### 2) HTTPS Ingress + Let’s Encrypt (Route53 DNS-01)
Files:
- `deploy/k8s/31-grafana-ingress.yaml` – Ingress with ClusterIssuer `letsencrypt-prod-r53`, host `grafana.swe-ai-fleet.yourdomain.com`.

Apply:
```bash
kubectl apply -f deploy/k8s/31-grafana-ingress.yaml
kubectl rollout restart deploy/grafana -n swe-ai-fleet
kubectl rollout status deploy/grafana -n swe-ai-fleet --timeout=120s
```

### 3) Route53 DNS Record
**Find your hosted zone ID:**
```bash
export R53_HOSTED_ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='yourdomain.com.'].Id" --output text | sed 's|/hostedzone/||')
echo "Hosted Zone ID: ${R53_HOSTED_ZONE_ID}"
```

If using MetalLB or static LB IP (replace IP accordingly):
```bash
export R53_HOSTED_ZONE_ID="<YOUR_HOSTED_ZONE_ID>"  # From above
export LB_IP="192.168.1.241"  # Replace with your ingress-nginx LoadBalancer IP

aws route53 change-resource-record-sets \
  --hosted-zone-id "${R53_HOSTED_ZONE_ID}" \
  --change-batch "{
    \"Comment\":\"Grafana A\",
    \"Changes\":[{
      \"Action\":\"UPSERT\",
      \"ResourceRecordSet\":{
        \"Name\":\"grafana.swe-ai-fleet.yourdomain.com\",
        \"Type\":\"A\",
        \"TTL\":60,
        \"ResourceRecords\":[{\"Value\":\"${LB_IP}\"}]
      }
    }]}"
```
If your ingress exposes a cloud LB hostname, use a CNAME instead.

### 4) Verify Certificate
```bash
kubectl get certificate,order,challenge -n swe-ai-fleet
# Expect grafana-tls READY=True, order/challenge valid
```

Grafana URL: `https://grafana.swe-ai-fleet.yourdomain.com`

---

## Prometheus (kube-prometheus-stack)

### 1) Install via Helm (namespace `monitoring`)
```bash
kubectl create namespace monitoring || true
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set grafana.enabled=false
```

### 2) In-cluster FQDN and Readiness
Service FQDN:
```
http://kube-prometheus-stack-prometheus.monitoring.svc.cluster.local:9090
```
Readiness check:
```bash
kubectl run tmp-prom-curl --rm -i -t -n monitoring \
  --image=docker.io/curlimages/curl:8.10.1 --restart=Never -- \
  -sS http://kube-prometheus-stack-prometheus.monitoring.svc.cluster.local:9090/-/ready
```

---

## Loki (single-binary) + Promtail

### 1) Loki (namespace `swe-ai-fleet`)
Files:
- `deploy/k8s/32-loki.yaml` – ConfigMap (filesystem storage), Deployment, Service.

Apply and verify:
```bash
kubectl apply -f deploy/k8s/32-loki.yaml
kubectl rollout status deploy/loki -n swe-ai-fleet --timeout=120s
kubectl get svc loki -n swe-ai-fleet -o wide
```
FQDN:
```
http://loki.swe-ai-fleet.svc.cluster.local:3100
```
Readiness (optional):
```bash
kubectl run tmp-loki-curl --rm -i -t -n swe-ai-fleet \
  --image=docker.io/curlimages/curl:8.10.1 --restart=Never -- \
  -sS http://loki.swe-ai-fleet.svc.cluster.local:3100/ready
```

### 2) Promtail (namespace `logging`)
```bash
kubectl create namespace logging || true
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm upgrade --install promtail grafana/promtail \
  --namespace logging \
  --set-string "config.clients[0].url=http://loki.swe-ai-fleet.svc.cluster.local:3100/loki/api/v1/push" \
  --set "config.snippets.pipelineStages=null" \
  --set resources.requests.cpu=50m \
  --set resources.requests.memory=64Mi \
  --set resources.limits.cpu=200m \
  --set resources.limits.memory=256Mi
```
Verify Promtail:
```bash
kubectl get pods -n logging -l app.kubernetes.io/name=promtail -o wide
kubectl logs -n logging -l app.kubernetes.io/name=promtail --tail=100
```

---

## Grafana Provisioning (Datasources & Folder)

### 1) API Token and Script
Create an admin API token in Grafana and save it (example):
```bash
echo 'YOUR_TOKEN' > /tmp/grafana_token.txt
chmod 600 /tmp/grafana_token.txt
```
Script:
- `scripts/monitoring/configure_grafana.sh`

Run with FQDNs:
```bash
export GRAFANA_URL="https://grafana.swe-ai-fleet.yourdomain.com"
export GRAFANA_TOKEN="$(cat /tmp/grafana_token.txt)"
export PROM_URL="http://kube-prometheus-stack-prometheus.monitoring.svc.cluster.local:9090"
export LOKI_URL="http://loki.swe-ai-fleet.svc.cluster.local:3100"
# Optional: TEMPO_URL for tracing
bash scripts/monitoring/configure_grafana.sh
```
The script is idempotent: it upserts Prometheus, Loki datasources and ensures a folder `Microservices` exists.

---

## Grafana Usage
- Open Grafana: `https://grafana.swe-ai-fleet.yourdomain.com`
- Datasources: Prometheus (default), Loki
- Explore → Metrics: query Kubernetes metrics
- Explore → Logs: query Loki logs, e.g. `{kubernetes_namespace_name="swe-ai-fleet"}`

---

## Troubleshooting
- Certificate pending:
  - Check DNS propagation: `dig +short grafana.swe-ai-fleet.yourdomain.com`
  - Describe resources: `kubectl get certificate,order,challenge -n swe-ai-fleet`
- Loki empty:
  - Ensure Promtail is running and targets are detected
  - Check Promtail logs for DNS or connection errors
- Prometheus URL not found:
  - `kubectl get svc -n monitoring | grep -i prometheus`
- Grafana API returns unauthorized:
  - Ensure API token has Admin role; check `GRAFANA_URL` and TLS (use https)

---

## Security & Production Notes
- Change Grafana admin password and avoid storing secrets in git
- Replace emptyDir in Loki with persistent volumes for durability
- Restrict access to Grafana via network policies/IP allowlists
- Consider Helm values or Terraform for full GitOps provisioning
