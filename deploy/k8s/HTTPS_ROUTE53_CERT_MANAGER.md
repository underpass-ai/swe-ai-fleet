# HTTPS with Route53 and cert-manager

This guide documents the standard pattern to expose a public host over HTTPS using:

- `ingress-nginx`
- `cert-manager`
- `ClusterIssuer letsencrypt-prod-r53`
- AWS Route53 DNS records

## Scope

Use this for public UIs and dashboards.

For private APIs, keep services internal (`ClusterIP`) and avoid creating an Ingress.

## Prerequisites

1. Ingress controller is running and has an external address.
2. `cert-manager` is running.
3. `ClusterIssuer/letsencrypt-prod-r53` is `Ready`.
4. AWS CLI credentials can edit the target Route53 hosted zone.

Quick checks:

```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller
kubectl get pods -n cert-manager
kubectl get clusterissuer letsencrypt-prod-r53
```

## Standard Ingress TLS Pattern

Use this structure in your ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  namespace: swe-ai-fleet
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod-r53
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - app.example.com
      secretName: app-example-tls
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app-service
                port:
                  number: 80
```

## Route53 DNS Record (A)

After applying the ingress, map the host to the ingress external IP:

```bash
HOST="app.example.com"
ZONE_ID="<your-hosted-zone-id>"
INGRESS_IP="$(kubectl get ingress -n swe-ai-fleet example-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"

aws route53 change-resource-record-sets \
  --hosted-zone-id "${ZONE_ID}" \
  --change-batch "{
    \"Comment\":\"UPSERT ${HOST} to ingress\",
    \"Changes\":[{
      \"Action\":\"UPSERT\",
      \"ResourceRecordSet\":{
        \"Name\":\"${HOST}\",
        \"Type\":\"A\",
        \"TTL\":60,
        \"ResourceRecords\":[{\"Value\":\"${INGRESS_IP}\"}]
      }
    }]
  }"
```

## Certificate Verification

Cert-manager should create a `Certificate` object and issue the secret defined in `spec.tls.secretName`.

```bash
kubectl get ingress -n swe-ai-fleet example-ingress
kubectl get certificate,certificaterequest,order,challenge -n swe-ai-fleet
kubectl wait --for=condition=Ready certificate/app-example-tls -n swe-ai-fleet --timeout=300s
```

## HTTPS Verification

```bash
curl -I https://app.example.com
```

Expected:

- HTTPS responds with `200` or app-specific redirect/status.
- Ingress TLS secret exists and is referenced by the ingress.

## Private API Pattern (Recommended)

To keep an API private while publishing only a UI:

1. Expose API via internal `ClusterIP` service only.
2. Create ingress only for UI/console service.
3. Apply `NetworkPolicy` to restrict API port to allowed namespaces.

Example in this repo:

- MinIO API private service: `minio-workspace-svc` (`9000`)
- MinIO console public ingress host: `minio-console.underpassai.com` (`9001`)
