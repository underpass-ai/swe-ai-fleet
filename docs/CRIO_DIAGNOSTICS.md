## CRI-O Diagnostics: What the checks do and how to fix issues

This document explains each section of `scripts/check_crio_nvidia_env.sh`, what it validates, symptoms when it fails, and suggested remedies.

### 1) GPU / Driver (host)
Commands: `nvidia-smi`, `modinfo nvidia`, `/proc/driver/nvidia/version`, `/dev/nvidia*`
- Confirms installed driver, versions, and device nodes.
- If `nvidia-smi` fails: reinstall/update NVIDIA drivers and reboot.

### 2) NVIDIA Container Toolkit & CDI
Commands: `nvidia-container-cli -V/info`, `nvidia-ctk --version cdi list`, `/etc/cdi/nvidia.yaml`
- Validates toolkit installation and CDI device spec.
- If CDI lists `/dev/dri/*` entries: regenerate excluding DRM devices:
  ```bash
  sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml --format=yaml --csv.ignore-pattern '/dev/dri/.*'
  sudo systemctl restart crio
  ```

### 3) CRI-O / crictl
Commands: `crio --version`, `crictl version/info`, `ls -l /run/crio/crio.sock`
- Checks CRI-O API compatibility and socket permissions.
- If `permission denied`: use `sudo` or add user to appropriate group and relogin.

### 4) CRI-O config (runtimes, hooks, cdi)
Commands: grep in `/etc/crio/crio.conf` and `/etc/crio/crio.conf.d/*.conf`, list hooks.
- Confirms runtime handlers (e.g., `[crio.runtime.runtimes.nvidia]`) and CDI dirs.
- If runtime handler missing: install NVIDIA runtime configs or run pods with `--runtime nvidia`.

### 5) Containers-common
Commands: registries.conf sanity, containers-common packages
- Ensure `containers-common`, `conmon`, `crun` are installed and configured for CRI‑O.

### 6) CNI & sysctl
Commands: list `/etc/cni/net.d`, `sysctl` IP forward, `lsmod br_netfilter`
- Ensures networking prerequisites for containers.
- If forwarding disabled: `sudo sysctl -w net.ipv4.ip_forward=1` and/or enable IPv6 forwarding.

### 7) CRI-O logs
Commands: `journalctl -u crio -b` (tail)
- Surfaces runtime errors (e.g., hook failures, CDI errors).
- Use messages to adjust CDI/hook configs.

### 8) Images & storage
Commands: `crictl images`, `df -hT`, `du -sh /var/lib/containers/storage`
- Checks disk usage and image presence.
- If low disk: cleanup unused images and extend storage.

### 9) Docker Hub reachability
Commands: HEAD to Docker Hub v2 API
- Confirms outbound connectivity to pull images.
- If blocked: check DNS/proxy and corporate firewalls.

### 10) Smoke: CUDA with CRI‑O (optional)
Use `crictl` with runtime handler `nvidia` to run a CUDA container and execute `nvidia-smi`.
If fails: verify CDI and runtime handler configuration.

### 11) Smoke: CRI-O runtime 'nvidia' (optional)
Runs a CUDA container via CRI-O to execute `nvidia-smi`.
- If fails: verify runtime handler and CDI spec.

### 12) CRI-O pods/containers (status) — with `--check-services`
Lists running pods/containers.
- Use to confirm `vllm`, `redis`, `neo4j`, `redisinsight` are up.

### 13) vLLM health — with `--check-services`
Checks `http://127.0.0.1:8000/health` and lists `/v1/models`.
- If health fails: check vLLM logs (`crictl logs <vllm-cid>`) and CDI devices injection in `crictl inspect`.

### 14) Redis PING — with `--check-services`
Runs `redis-cli -a <password> PING` (host or in-container).
- If `Connection refused`: ensure Redis pod is running with host network and `--requirepass`.

### 15) Neo4j HTTP/Bolt — with `--check-services`
Checks HTTP header and runs `RETURN 1` via `cypher-shell` inside the Neo4j container.
- If `Unauthorized` on first run: set initial password from default:
  ```bash
  CID=$(sudo crictl ps -a --name neo4j -q | head -n1)
  sudo crictl exec "$CID" /var/lib/neo4j/bin/cypher-shell -d system -u neo4j -p neo4j \
    "ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO 'swefleet-dev'"
  ```
- If `AuthenticationRateLimit`: wait ~5 seconds and retry.

### 16) vLLM CDI devices in spec — with `--check-services`
Shows devices injected into vLLM container spec.
- If empty: ensure runtime `nvidia` used and CDI spec valid.

---

Quick run:
```bash
bash scripts/check_crio_nvidia_env.sh --check-services
```

Remediation summary:
- Regenerate CDI excluding `/dev/dri/*` and restart CRI-O.
- Use `--runtime nvidia` for GPU pods and verify devices in `crictl inspect`.
- Host networking for vLLM/Redis/Neo4j on localhost ports.
- Set Neo4j initial password before first use.


