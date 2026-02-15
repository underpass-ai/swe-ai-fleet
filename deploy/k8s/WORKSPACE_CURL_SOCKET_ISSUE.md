# Workspace API: `curl (7) failed to open socket: Operation not permitted`

## Síntoma

Al validar el microservicio `workspace` puede aparecer:

```text
curl: (7) failed to open socket: Operation not permitted
```

## Causas típicas

1. **Entorno sandbox local (CLI/runner restringido)**
- El proceso que ejecuta `curl` no tiene permisos de red saliente.
- No es un problema del servicio en Kubernetes.

2. **`NetworkPolicy` con egress default-deny**
- El pod origen no puede abrir conexión hacia `workspace:50053`.

3. **Políticas de seguridad del cluster (PSA/OPA/Kyverno/CNI)**
- Reglas que bloquean sockets o namespaces de red para ciertos pods.

4. **DNS o Service incorrectos**
- `workspace.swe-ai-fleet.svc.cluster.local` no resuelve o apunta mal.

## Diagnóstico recomendado

### 1) Verificar servicio y endpoints

```bash
kubectl get svc -n swe-ai-fleet workspace -o wide
kubectl get endpoints -n swe-ai-fleet workspace -o wide
kubectl get pods -n swe-ai-fleet -l app=workspace -o wide
```

### 2) Probar conectividad desde un pod debug en el namespace

```bash
kubectl run -n swe-ai-fleet curl-debug --rm -it --restart=Never \
  --image=curlimages/curl:8.8.0 -- \
  sh -lc 'curl -sS http://workspace.swe-ai-fleet.svc.cluster.local:50053/healthz'
```

Si aquí funciona, el problema está en el pod/entorno desde donde probabas originalmente.

### 3) Revisar políticas de red activas

```bash
kubectl get networkpolicy -n swe-ai-fleet
kubectl describe networkpolicy -n swe-ai-fleet <policy-name>
```

## Solución (NetworkPolicy)

Si usas `default-deny`, permite egress TCP/50053 desde los pods consumidores hacia `workspace`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-egress-to-workspace
  namespace: swe-ai-fleet
spec:
  podSelector:
    matchLabels:
      app: orchestrator
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: workspace
      ports:
        - protocol: TCP
          port: 50053
```

Replica la misma regla para otros consumidores (`planning-cpu-jobs`, workers, etc.).

## Validación final

```bash
kubectl exec -n swe-ai-fleet deploy/orchestrator -- \
  curl -sS http://workspace.swe-ai-fleet.svc.cluster.local:50053/healthz
```

Debe devolver:

```json
{"status":"ok"}
```

## Nota sobre este repositorio

En este entorno de desarrollo, el error también puede aparecer por restricciones del sandbox del agente (sin sockets). En ese caso:
- valida con `go test`/tests de integración internos,
- y ejecuta los checks HTTP desde un pod de Kubernetes o desde tu host con permisos de red.
