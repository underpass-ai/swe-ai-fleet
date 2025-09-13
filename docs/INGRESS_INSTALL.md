# Ingress Controller Install (NGINX) — kubeadm + CRI‑O

This guide installs the community NGINX Ingress Controller on a kubeadm cluster.

## 1) Install Ingress NGINX via Helm (recommended)

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

kubectl create namespace ingress-nginx || true

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  -n ingress-nginx \
  --set controller.watchIngressWithoutClass=true \
  --set controller.admissionWebhooks.enabled=true

kubectl get pods -n ingress-nginx -o wide
kubectl get svc -n ingress-nginx
```

Note:
- On bare‑metal, the default Service is a `NodePort`. For a single‑node lab, access via `http://<nodeIP>:<nodePort>`. You can also switch to `hostNetwork=true` (not recommended) or deploy MetalLB to get a LoadBalancer IP.

## 2) Bare‑metal: MetalLB (optional)

```bash
helm repo add metallb https://metallb.github.io/metallb
helm repo update
kubectl create namespace metallb-system || true
helm upgrade --install metallb metallb/metallb -n metallb-system

# Create an address pool (example CIDR)
cat <<'EOF' | kubectl apply -n metallb-system -f -
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: default-pool
spec:
  addresses:
  - 192.168.1.240-192.168.1.250
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: default-l2
spec: {}
EOF
```

Then patch the ingress Service to `LoadBalancer`:

```bash
kubectl -n ingress-nginx patch svc ingress-nginx-controller -p '{"spec":{"type":"LoadBalancer"}}'
```

## 3) Sample Ingress for the demo (host‑based)

Assuming you expose the FastAPI demo behind a Service (or you port‑forward it), you can define an Ingress for path routing.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: swe-demo
  namespace: swe
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: swe.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: demo-frontend
            port:
              number: 8080
```

Notes:
- For local testing, add `swe.local` to `/etc/hosts` pointing to the node IP.
- If you run the frontend outside the cluster, prefer port‑forward and skip Ingress for the web until it’s packaged as a Service.

## 4) TLS (optional)

Use cert-manager for automated TLS. For lab use, self‑signed is fine.

```bash
# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm repo update
kubectl create namespace cert-manager || true
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --set installCRDs=true
```

Then define an Issuer/ClusterIssuer and annotate your Ingress with `cert-manager.io/cluster-issuer: <name>`.
