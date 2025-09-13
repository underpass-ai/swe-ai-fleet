## Troubleshooting (CRI-O + NVIDIA + vLLM + Redis + Neo4j)

> Important (2025‑09): For the initial demo, a standalone CRI‑O setup is considered advanced. We have observed extra complexity (CNI/DNS, GPUs/NCCL, image and dependency resolution) that Kubernetes abstracts better. Prefer running the demo on Kubernetes (with CRI‑O or containerd as the runtime). Use this guide when you explicitly need low‑level CRI‑O.

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
- Set initial password (>=8 chars) before first use:
```bash
CID=$(sudo crictl ps -a --name neo4j -q | head -n1)
sudo crictl exec "$CID" /var/lib/neo4j/bin/cypher-shell -d system -u neo4j -p neo4j \
  "ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO 'swefleet-dev'"
```
- If already started with wrong attempts: wait a few seconds and retry.

### Neo4j config key mismatch
Symptoms:
- Logs show `Unrecognized setting: server.http_listen_address` and Neo4j exits.
Cause:
- Using old config keys; in Neo4j 5 use `server.default_listen_address` only.
Fix:
- Ensure CRI-O manifests set only `NEO4J_server_default__listen__address=0.0.0.0`.

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


### Redis auth mismatch (AUTH called but no password configured)
Symptoms:
- `redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user`
Cause:
- Client uses `redis://:password@host:6379/0` while Redis container was started without `--requirepass`.
Fix:
- Either remove password from client URL: `redis://host:6379/0`, or restart Redis with `--requirepass <pw>`.
- In this repo: use `.env` and `scripts/redis_crio.sh` which honors `REDIS_PASSWORD`.

### Neo4j auth mismatch (Unauthorized on seed)
Symptoms:
- `neo4j.exceptions.AuthError: The client is unauthorized due to authentication failure`
Cause:
- Container not using expected `NEO4J_AUTH`, or seeding uses a different password than container.
Fix:
- Start via `scripts/neo4j_crio.sh` and set `NEO4J_PASSWORD` in `.env` (defaults to `test`).
- If already running, reset inside container:
```bash
CID=$(sudo crictl ps -a --name neo4j -q | head -n1)
sudo crictl exec -i "$CID" /var/lib/neo4j/bin/neo4j-admin dbms set-initial-password test
```
- Then restart the pod and re-run seed with matching `NEO4J_PASSWORD`.

### Kong config mount path
Symptoms:
- Kong starts without routes or fails to read `kong.yml`.
Fix:
- Ensure `deploy/podman/kong/kong.yml` is mounted with an absolute host path in the container JSON. See `deploy/crio/kong-ctr.json`.

### vLLM CDI / GPU mapping and health
Symptoms:
- vLLM starts but `/v1/models` probe fails, or no GPU is visible.
Fix:
- Regenerate CDI YAML excluding `/dev/dri/*`, restart CRI-O, and use runtime `nvidia` or annotations `nvidia.com/gpu=all`.
- Verify with `crictl logs` and probe `http://127.0.0.1:8000/v1/models`.

### crictl: container not in created state: running
Symptoms:
- `rpc error: ... container <id> is not in created state: running` when starting.
Cause:
- Attempted to start an already running container ID.
Fix:
- Remove stale pods/containers: `sudo crictl ps -a -q | xargs -r sudo crictl rm -f; sudo crictl pods -a -q | xargs -r sudo crictl rmp -f`.
- Our helper scripts perform clean stop/start; prefer them over manual reuse of IDs.

### crictl requires sudo
Symptoms:
- `permission denied` on `/run/crio/crio.sock` when running `crictl`.
Fix:
- Use `sudo` (current default). For rootless, add your user to the CRI-O group and relogin, or expose a rootless socket.

### Web server env verification
Info:
- The FastAPI app logs a sanitized config snapshot at startup. Use `LOG_LEVEL=INFO` and view logs to confirm `.env` pickup.
- Endpoints: `/healthz`, `/healthz/llm`, `/api/report`, `/ui/report`.

### Web container: port 8080 not ready / slow startup
Symptoms:
- `/healthz` returns 000/timeout; no bind logs.
Cause:
- First-run dependency install inside container takes time; lack of clear uvicorn startup logs.
Fix:
- Use the helper script which enables dev mode automatically (`scripts/web_crio.sh start`). Dev mode:
  - Runs `python:3.13-slim`, bind‑mounts the repo at `/app`, installs `-e /app[web]`.
  - Starts uvicorn with the app factory and clear bind logs:
    `python -m uvicorn swe_ai_fleet.web.server:create_app --host 0.0.0.0 --port 8080 --factory --log-level info`.
  - Adds verbose pip output; tail logs: `sudo bash scripts/web_crio.sh logs` or `sudo crictl logs -f $(cat /tmp/swe-web/ctr.id)`.
- Ensure `.env` includes Redis/Neo4j URLs; `VLLM_ENDPOINT` is optional (LLM health will 503 if unset).


