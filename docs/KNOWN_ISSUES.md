## Known Issues (CRI-O demo) and How We Fix Them

This document tracks issues observed while bringing up the CRI-O-only demo (Redis, Neo4j, vLLM, Web, Kong) and the corresponding fixes/workarounds.

### 1) Redis auth mismatch
- Symptoms: `redis.exceptions.AuthenticationError: AUTH <password> called without any password configured...`
- Root cause: Client uses a password in `REDIS_URL` but Redis was started without `--requirepass`.
- Fix (pick one):
  - No-auth local dev: set `REDIS_URL=redis://127.0.0.1:6379/0` and start Redis with no `--requirepass` (default in `scripts/redis_crio.sh` if `REDIS_PASSWORD` is unset).
  - Auth local dev: set `REDIS_PASSWORD=swefleet-dev` in `.env`, and keep `REDIS_URL=redis://:swefleet-dev@127.0.0.1:6379/0`. Restart Redis via `scripts/redis_crio.sh`.

### 2) Neo4j authentication drift
- Symptoms: `neo4j.exceptions.AuthError: The client is unauthorized due to authentication failure.`
- Root cause: Container not initialized with the intended password; or client/seeder uses a different password. Neo4j requires initial passwords to be ≥ 8 chars.
- Fix:
  - Use `.env` and `scripts/neo4j_crio.sh` so the container starts with `NEO4J_AUTH=neo4j/<NEO4J_PASSWORD>`. Recommended for CRI-O demo: `NEO4J_PASSWORD=swefleet-dev`.
  - If the password needs to be reset inside a running container:
    ```bash
    CID=$(sudo crictl ps -a --name neo4j -q | head -n1)
    sudo crictl exec -i "$CID" /var/lib/neo4j/bin/neo4j stop || true
    sudo crictl exec -i "$CID" /var/lib/neo4j/bin/neo4j-admin dbms set-initial-password swefleet-dev
    sudo crictl exec -i "$CID" /var/lib/neo4j/bin/neo4j start &
    ```
  - Ensure your environment for seeding/web has `NEO4J_PASSWORD=swefleet-dev`.
  - Note: Unit tests default to password `test` (short). The CRI-O demo uses `swefleet-dev` (≥ 8 chars) to satisfy container policy.

### 3) crictl: "container ... is not in created state: running"
- Symptoms: Error when attempting to start an already-running container ID.
- Fix: Fully remove containers/pods before re-creating:
  ```bash
  sudo crictl ps -a -q | xargs -r sudo crictl rm -f
  sudo crictl pods -a -q | xargs -r sudo crictl rmp -f
  ```
  Prefer the helper scripts (`scripts/*_crio.sh`) which perform clean stop/start.

### 4) vLLM GPU/CDI quirks
- Symptoms: GPU not visible; `/v1/models` probe fails; HF downloads slow/fail.
- Fix:
  - Regenerate NVIDIA CDI without `/dev/dri/*` and restart CRI-O:
    ```bash
    sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml --format=yaml --csv.ignore-pattern '/dev/dri/.*'
    sudo systemctl restart crio
    ```
  - Use runtime `nvidia` or `nvidia.com/gpu=all` annotation and mount host HF cache at `/root/.cache/huggingface`.

### 5) crictl permissions
- Symptoms: `permission denied` when using `crictl` as non-root.
- Fix: Use `sudo` (current flow). For rootless, configure group access to `/run/crio/crio.sock` and relogin.

### 6) Webserver env verification
- The FastAPI app logs a sanitized config snapshot on startup (REDIS_URL masked, NEO4J_*, VLLM_ENDPOINT). Tail logs to confirm `.env` was applied:
  - CRI-O: `sudo bash scripts/web_crio.sh logs`
  - Local: `LOG_LEVEL=INFO python -m swe_ai_fleet.web.server`

### Status and decision
- For the CRI-O demo, we standardize on:
  - Redis: `REDIS_PASSWORD=swefleet-dev` (auth) OR no auth with matching `REDIS_URL` (pick one and keep consistent)
  - Neo4j: `NEO4J_PASSWORD=swefleet-dev` (≥ 8 chars)
  - vLLM: `VLLM_ENDPOINT=http://127.0.0.1:8000/v1`
- Helper scripts read `.env` and generate CRI-O manifests accordingly.


