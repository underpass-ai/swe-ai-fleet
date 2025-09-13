# CRI-O Manifests — Critical Review (@crio/)

> Scope: `deploy/crio/` — Advanced/Experimental standalone CRI‑O path. Local, host‑networked runbooks for Redis, RedisInsight, Neo4j and vLLM.

## Summary
- Design favors simplicity (host networking, minimal security context) for local demos.
- Works for single‑host experiments but not production‑grade: no persistence, permissive networking, and environment‑specific paths.
- Main risks: secrets, durability, portability (hardcoded paths), GPU injection assumptions.

## File‑by‑file notes

### redis-pod.json
- Uses host networking via `namespace_options.network = 2`. Good for localhost access, but:
  - Risk: no network isolation; any process on host can reach Redis.
- `cgroup_parent: system.slice` ties into host systemd hierarchy; acceptable locally.
- Missing: CPU/memory limits, restart policy, annotations for traceability.

### redis-ctr.json
- Image: `redis:7-alpine` (good baseline).
- Args:
  - `--requirepass ${REDIS_PASSWORD:-swefleet-dev}` → default password in manifest is weak; risk if reused.
  - `--bind 0.0.0.0` + `--protected-mode no` → necessary for host‑net demo, but insecure by default.
  - No `--maxmemory` set; only policy (`allkeys-lru`). On constrained hosts, OOM risk.
- Missing: volumes for data persistence (AOF disabled), log rotation.
- Suggest: env var templating documented (ensure shell expansion happens before `crictl create`).

### redisinsight-pod.json
- Same host network approach; fine for local.
- Missing: resource limits and restart policy hints.

### redisinsight-ctr.json
- Image pinned to `latest`; prefer version pin for reproducibility.
- Mount to `/home/ia/redisinsight_data` (user‑specific absolute path):
  - Portability risk; fails on other machines/users.
  - Suggest using an env or `${PWD}/.data/redisinsight` with mkdir instructions.

### neo4j-pod.json
- Host network; OK for demo.
- Missing: explicit storage mount for `/data` and `/logs` → data loss on restart.

### neo4j-ctr.json
- `NEO4J_AUTH=neo4j/swefleet-dev`: static creds in manifest; acceptable for demo but risky generally.
- Explicit listen addresses (good). Missing:
  - Volume mounts for `/data`, `/logs`.
  - Resource limits.
  - Healthcheck guidance beyond README.

### vllm-pod.json
- Host network + IPC host (`ipc: 2`) to enable NCCL shared memory; appropriate for local multi‑GPU.
- Missing: resource constraints; but for GPU demos this is common.

### vllm-ctr.json
- Image: `docker.io/vllm/vllm-openai:latest` — use a tagged version for reproducibility.
- Args: TinyLlama model by default (good for smoke). `tensor-parallel-size: 2` assumes ≥2 GPUs.
  - Failure mode on 1‑GPU hosts.
- Env:
  - `CUDA_VISIBLE_DEVICES=0,1` and annotations `io.kubernetes.cri-o.Devices: ["nvidia.com/gpu=all"]` — depends on properly generated CDI and runtime handler; mismatches cause startup failures.
  - NCCL envs set to disable P2P/IB (good for single host without IB).
- Mounts: host‑specific `${HOME}/.cache/huggingface` path; portability risk.
- Missing: persistence for model cache if path absent; health/readiness script hints.

## Cross‑cutting issues and improvements

- Networking/security:
  - Host networking across all pods → simple but no isolation. Document explicitly and warn.
  - Redis runs with protected‑mode off and weak default password; call this out as demo‑only.
- Persistence:
  - Neo4j/Redis data not persisted; recommend example bind mounts with local `.data/` folder.
- Portability:
  - Hardcoded absolute paths (`/home/ia/...`). Replace with env‑driven or relative `${PWD}/.data/...`.
  - Image tags should be pinned (avoid `latest`).
- GPU setup:
  - Requires correct CDI spec and CRI‑O restart; README mentions it—keep it prominent.
  - `tensor-parallel-size` and `CUDA_VISIBLE_DEVICES` should be guided by detected GPU count; suggest two variants (1‑GPU, 2‑GPU).
- Resource management:
  - Consider adding `resources` in containers (cpu/mem) to avoid host starvation.
- Observability:
  - Add example `crictl logs`/`inspect` commands per service; already partially covered in README.

## Suggested manifest diffs (illustrative)

- Use relative data dirs (example for RedisInsight):

```json
"mounts": [{
  "container_path": "/data",
  "host_path": "${PWD}/.data/redisinsight",
  "readonly": false
}]
```

- Pin images:

```json
"image": {"image": "docker.io/redis/redisinsight:1.14.0"}
```

- Neo4j data mounts:

```json
"mounts": [
  {"container_path": "/data", "host_path": "${PWD}/.data/neo4j/data", "readonly": false},
  {"container_path": "/logs", "host_path": "${PWD}/.data/neo4j/logs", "readonly": false}
]
```

- vLLM 1‑GPU alternative:

```json
"args": ["--model","TinyLlama/TinyLlama-1.1B-Chat-v1.0","--tensor-parallel-size","1","--gpu-memory-utilization","0.85","--host","0.0.0.0","--port","8000"],
"envs": [{"name":"CUDA_VISIBLE_DEVICES","value":"0"}],
"annotations": {"io.kubernetes.cri-o.Devices": "[\"nvidia.com/gpu=1\"]"}
```

## Potential failure points

- Missing CDI or wrong CDI entries (e.g., includes `/dev/dri/*`) → vLLM fails to start (`Failed to infer device type`).
- Incorrect GPU count vs. `tensor-parallel-size`/`CUDA_VISIBLE_DEVICES` → NCCL/vLLM errors at boot.
- Hardcoded paths not present on host → container create fails (RedisInsight/vLLM cache).
- Neo4j/Redis data not persisted → data loss on restart; report generation fails if seed not re‑run.
- Weak/unchanged credentials (Redis/Neo4j) exposed on host network → local security risk.
- Using `latest` images → unexpected breaking changes on pull.

## Recommendations

- Keep CRI‑O path flagged as Advanced/Experimental (done).
- Replace absolute paths with env/relative paths and document `mkdir -p` pre‑steps.
- Provide 1‑GPU and 2‑GPU variants for vLLM.
- Pin image tags for reproducibility.
- Add optional persistence mounts for Redis/Neo4j.
- Consider minimal resource hints and simple health checks.

## Fix-it snippets (ready to paste)

Create local data dirs before running:

```bash
mkdir -p ${PWD}/.data/redisinsight \
         ${PWD}/.data/neo4j/data ${PWD}/.data/neo4j/logs \
         ${PWD}/.cache/huggingface
```

### Fix-it: redis-ctr.json (safer defaults + remove non-working env substitution)

```json
{
  "metadata": {"name": "redis"},
  "image": {"image": "docker.io/library/redis:7.2-alpine"},
  "command": ["redis-server"],
  "args": [
    "--appendonly","no",
    "--save","",
    "--requirepass","swefleet-dev",
    "--bind","0.0.0.0",
    "--protected-mode","no",
    "--maxmemory-policy","allkeys-lru"
  ],
  "log_path": "redis.log",
  "linux": {"security_context": {"privileged": false}}
}
```

Notes: CRI‑O does not expand `${VAR}` in JSON. To inject a password at runtime, generate the file with a templating step (e.g., `sed -e "s/swefleet-dev/$REDIS_PASSWORD/"`).

### Fix-it: redisinsight-ctr.json (pin image + relative mount)

```json
{
  "metadata": {"name": "redisinsight"},
  "image": {"image": "docker.io/redis/redisinsight:1.14.0"},
  "log_path": "redisinsight.log",
  "mounts": [
    {"container_path":"/data","host_path":"${PWD}/.data/redisinsight","readonly": false}
  ],
  "linux": { "security_context": { "privileged": false } }
}
```

### Fix-it: neo4j-ctr.json (add persistence mounts)

```json
{
  "metadata": {"name": "neo4j"},
  "image": {"image": "docker.io/neo4j:5.23.0"},
  "envs": [
    {"name":"NEO4J_AUTH","value":"neo4j/swefleet-dev"},
    {"name":"NEO4J_server_default__listen__address","value":"0.0.0.0"},
    {"name":"NEO4J_server_http__listen__address","value":"0.0.0.0:7474"},
    {"name":"NEO4J_server_bolt__listen__address","value":"0.0.0.0:7687"}
  ],
  "mounts": [
    {"container_path":"/data","host_path":"${PWD}/.data/neo4j/data","readonly": false},
    {"container_path":"/logs","host_path":"${PWD}/.data/neo4j/logs","readonly": false}
  ],
  "log_path": "neo4j.log",
  "linux": {"security_context": {"privileged": false}}
}
```

### Fix-it: vllm-ctr.json (1‑GPU variant; pinned image)

```json
{
  "metadata": {"name": "vllm"},
  "image": {"image": "docker.io/vllm/vllm-openai:0.6.2"},
  "args": [
    "--model","TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "--tensor-parallel-size","1",
    "--gpu-memory-utilization","0.85",
    "--dtype","auto",
    "--host","0.0.0.0",
    "--port","8000"
  ],
  "log_path": "vllm-openai.log",
  "envs": [
    {"name":"HF_HOME","value":"/root/.cache/huggingface"},
    {"name":"VLLM_DEVICE","value":"cuda"},
    {"name":"VLLM_LOGGING_LEVEL","value":"DEBUG"},
    {"name":"NVIDIA_VISIBLE_DEVICES","value":"all"},
    {"name":"NVIDIA_DRIVER_CAPABILITIES","value":"compute,utility"},
    {"name":"CUDA_VISIBLE_DEVICES","value":"0"},
    {"name":"HF_HUB_ENABLE_HF_TRANSFER","value":"1"},
    {"name":"NCCL_P2P_DISABLE","value":"1"},
    {"name":"NCCL_IB_DISABLE","value":"1"}
  ],
  "mounts": [
    {"container_path":"/root/.cache/huggingface", "host_path":"${PWD}/.cache/huggingface", "readonly": false}
  ],
  "linux": { "security_context": { "privileged": false } },
  "annotations": { "io.kubernetes.cri-o.Devices": "[\"nvidia.com/gpu=1\"]" }
}
```

### Fix-it: vllm-ctr.json (2‑GPU variant; pinned image)

```json
{
  "metadata": {"name": "vllm"},
  "image": {"image": "docker.io/vllm/vllm-openai:0.6.2"},
  "args": [
    "--model","TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "--tensor-parallel-size","2",
    "--gpu-memory-utilization","0.85",
    "--dtype","auto",
    "--host","0.0.0.0",
    "--port","8000"
  ],
  "log_path": "vllm-openai.log",
  "envs": [
    {"name":"HF_HOME","value":"/root/.cache/huggingface"},
    {"name":"VLLM_DEVICE","value":"cuda"},
    {"name":"VLLM_LOGGING_LEVEL","value":"DEBUG"},
    {"name":"NVIDIA_VISIBLE_DEVICES","value":"all"},
    {"name":"NVIDIA_DRIVER_CAPABILITIES","value":"compute,utility"},
    {"name":"CUDA_VISIBLE_DEVICES","value":"0,1"},
    {"name":"HF_HUB_ENABLE_HF_TRANSFER","value":"1"},
    {"name":"NCCL_P2P_DISABLE","value":"1"},
    {"name":"NCCL_IB_DISABLE","value":"1"}
  ],
  "mounts": [
    {"container_path":"/root/.cache/huggingface", "host_path":"${PWD}/.cache/huggingface", "readonly": false}
  ],
  "linux": { "security_context": { "privileged": false } },
  "annotations": { "io.kubernetes.cri-o.Devices": "[\"nvidia.com/gpu=all\"]" }
}
```
