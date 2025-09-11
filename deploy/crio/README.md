CRIO manifests for local services (host networking)

Requirements
- CRI-O running and `crictl` configured
- NVIDIA Container Toolkit with CDI (for vLLM with GPU)

Redis
```bash
sudo crictl runp deploy/crio/redis-pod.json | tee /tmp/redis.pod
POD=$(cat /tmp/redis.pod)
sudo crictl create "$POD" deploy/crio/redis-ctr.json deploy/crio/redis-pod.json | tee /tmp/redis.ctr
sudo crictl start $(cat /tmp/redis.ctr)
# Password default: swefleet-dev
```

RedisInsight
```bash
sudo crictl runp deploy/crio/redisinsight-pod.json | tee /tmp/ri.pod
POD=$(cat /tmp/ri.pod)
sudo crictl create "$POD" deploy/crio/redisinsight-ctr.json deploy/crio/redisinsight-pod.json | tee /tmp/ri.ctr
sudo crictl start $(cat /tmp/ri.ctr)
# UI: http://127.0.0.1:5540
```

vLLM (GPU)
```bash
# Ensure CDI is regenerated without /dev/dri and CRI-O restarted
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml --format=yaml --csv.ignore-pattern '/dev/dri/.*'
sudo systemctl restart crio

sudo crictl runp --runtime nvidia deploy/crio/vllm-pod.json | tee /tmp/vllm.pod
POD=$(cat /tmp/vllm.pod)
sudo crictl create "$POD" deploy/crio/vllm-ctr.json deploy/crio/vllm-pod.json | tee /tmp/vllm.ctr
sudo crictl start $(cat /tmp/vllm.ctr)
# Health: curl -fsS http://127.0.0.1:8000/health && echo ok
# Models: curl -sS http://127.0.0.1:8000/v1/models
```

Neo4j
```bash
sudo crictl pull docker.io/neo4j:5
sudo crictl runp deploy/crio/neo4j-pod.json | tee /tmp/neo4j.pod
POD=$(cat /tmp/neo4j.pod)
sudo crictl create "$POD" deploy/crio/neo4j-ctr.json deploy/crio/neo4j-pod.json | tee /tmp/neo4j.ctr
sudo crictl start $(cat /tmp/neo4j.ctr)
# HTTP: http://127.0.0.1:7474 (auth neo4j/test)
# Bolt: bolt://127.0.0.1:7687
```

Stop/Clean
```bash
for f in /tmp/{redis,ri,vllm,neo4j}.ctr; do [ -f "$f" ] && sudo crictl rm -f $(cat "$f"); done
for f in /tmp/{redis,ri,vllm,neo4j}.pod; do [ -f "$f" ] && sudo crictl rmp -f $(cat "$f"); done
```

