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

Verification (bare‑metal without LoadBalancer):

```bash
# Wait for controller rollout
kubectl -n ingress-nginx rollout status deploy/ingress-nginx-controller --timeout=300s

# Inspect Service (NodePort/LoadBalancer)
kubectl -n ingress-nginx get svc ingress-nginx-controller -o wide
```

- If `EXTERNAL-IP` is `<pending>`, access via NodePort on the node IP:
  - HTTP: NodePort (e.g., 31847)
  - HTTPS: NodePort (e.g., 31464)
  - Example: `http://<NODE_IP>:<NODEPORT>`

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

Verify that `EXTERNAL-IP` is assigned from the configured pool.

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

Create a Service for the frontend (if you package the demo in‑cluster):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: demo-frontend
  namespace: swe
spec:
  selector:
    app: demo-frontend
  ports:
  - name: http
    port: 8080
    targetPort: 8080
```

Smoke tests:

```bash
# NodePort (no MetalLB)
curl -sS http://<NODE_IP>:<NODEPORT>/ -I | head -n 1

# Ingress (resolving swe.local)
curl -sS http://swe.local/ -I | head -n 1
```

## 6) Local access without exposing the cluster (port‑forward)

For lab setups without MetalLB or external exposure, you can reach the Ingress Controller locally via port‑forward.

### 6.1 /etc/hosts entries

Add hostnames to your local `/etc/hosts` so browser and curl resolve to localhost:

```bash
sudo sh -c 'printf "\n127.0.0.1 swe-ai-fleet.local\n127.0.0.1 demo.swe-ia-fleet.local\n" >> /etc/hosts'
```

These hostnames must match the `spec.rules[].host` values in your Ingress objects.

### 6.2 Port‑forward with sudo using your kubeconfig

When binding to privileged port 80, use sudo and pass your kubeconfig explicitly:

```bash
# Option A: set KUBECONFIG inline
sudo KUBECONFIG=/home/ia/.kube/config \
  kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 80:80

# Option B: preserve env with -E
export KUBECONFIG=/home/ia/.kube/config
sudo -E kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 80:80
```

Open another terminal and verify:

```bash
curl -s -H 'Host: swe-ai-fleet.local' http://127.0.0.1/ | cat
curl -s -H 'Host: demo.swe-ia-fleet.local' http://127.0.0.1/ | cat
```

Expected output for the demo echo service:

```
hello swe-ai-fleet from kubernetes!!
```

### 6.3 Alternative (non‑root) using high port

If you prefer avoiding sudo, forward to a high local port and use that on curl/browser:

```bash
kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8080:80 --address 127.0.0.1

curl -s -H 'Host: swe-ai-fleet.local' http://127.0.0.1:8080/
```

### 6.4 Common issues

- Connection refused on `kubectl port-forward` with sudo:
  - Ensure the effective kubeconfig is set: `sudo env | grep KUBECONFIG` should reflect `/home/ia/.kube/config`.
  - Use `sudo -E` or inline `KUBECONFIG=...` as above.
- 404 from default backend:
  - Confirm Ingress exists, `ingressClassName: nginx`, and host/path match the Service name/port.
- Host headers not routed:
  - Verify `/etc/hosts` entries and that you curl with `-H 'Host: <name>'`.
- Nothing on curl but pod healthy:
  - Check `kubectl -n ingress-nginx get pods,svc` and `describe ingress` for errors.

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

## 5) Troubleshooting

- `EXTERNAL-IP <pending>` on `ingress-nginx-controller`:
  - Install MetalLB and configure an `IPAddressPool`.
  - Alternatively, use NodePort for local access.

- 404 from default backend:
  - Ensure `ingressClassName: nginx` and path rules target the correct Service name/port.

- NodePort connection refused:
  - Check host firewall (open NodePorts).
  - Confirm `kube-proxy` without iptables/ipvs errors.

- Hostname resolution (swe.local):
  - Add `/etc/hosts` entry mapping to node IP or MetalLB `EXTERNAL-IP`.
