> Status: Advanced/Experimental — Standalone CRI‑O troubleshooting
>
> Applies to the local‑only CRI‑O setup. For Kubernetes clusters, use the GPU Operator and standard K8s troubleshooting flows.

## Troubleshooting (CRI-O + NVIDIA + vLLM + Redis + Neo4j)

### vLLM: Failed to infer device type
Symptoms:
- vLLM exits with `RuntimeError: Failed to infer device type`
Fix:
- Ensure CDI regenerated without `/dev/dri/*` and CRI-O restarted:
```bash
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml --format=yaml --csv.ignore-pattern '/dev/dri/.*'
sudo systemctl restart crio
```
- Use CRI-O runtime handler `nvidia` for the pod: `crictl runp --runtime nvidia ...`
- Set envs in container JSON: `VLLM_DEVICE=cuda`, `NVIDIA_VISIBLE_DEVICES=all`, `CUDA_VISIBLE_DEVICES=0,1`.

### CDI: device injection errors (DRM paths)
Symptoms:
- Errors referencing `/dev/dri/card0` / `renderD*` not found.
Fix:
- Regenerate CDI excluding `/dev/dri/*` (see above).

### CRI-O: unknown flag --hooks-dir-path
Symptoms:
- Podman/CRI-O launched with unsupported flag.
Fix:
- Remove `--hooks-dir-path` and rely on CDI via `--device nvidia.com/gpu=all` or runtime `nvidia`.

### CRI-O permissions (crictl)
Symptoms:
- `permission denied` connecting to `/run/crio/crio.sock`.
Fix:
- Use `sudo` or add your user to the appropriate group and relogin.

### Neo4j authentication / initial password
Symptoms:
- `Unauthorized` or `AuthenticationRateLimit` after first start.
Fix:
- Set initial password before first use:
```bash
CID=$(sudo crictl ps -a --name neo4j -q | head -n1)
sudo crictl exec "$CID" /var/lib/neo4j/bin/cypher-shell -d system -u neo4j -p neo4j \
  "ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO 'swefleet-dev'"
```
- If already started with wrong attempts: wait a few seconds and retry.

### vLLM network timeouts to Hugging Face
Symptoms:
- Logs show `NameResolutionError: huggingface.co`.
Fix:
- Use host network for the pod and explicit DNS in pod JSON, or pre-populate HF cache on host and mount it into container at `/root/.cache/huggingface`.

### Python 3.13 vs. PyTorch/vLLM
Symptoms:
- Wheels not available or build failures.
Fix:
- Prefer Python 3.11 for vLLM host installs. In container, use upstream vLLM images.

### Redis connection refused
Symptoms:
- `Error 111 connecting to localhost:6379`.
Fix:
- Ensure Redis pod is running with host network and `--requirepass swefleet-dev`.
- Validate with: `redis-cli -a swefleet-dev PING`.


