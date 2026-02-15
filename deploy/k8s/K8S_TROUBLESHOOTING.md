# 🔧 Troubleshooting Guide

> Comprehensive reference: Kubernetes (K8s) + CRI-O operational troubleshooting

---

## 🚀 Quick Diagnostics

### Kubernetes Cluster

```bash
# Namespace summary
kubectl -n swe-ai-fleet get all,ingress,secrets,events

# Focus on a component
kubectl -n swe-ai-fleet get deploy,rs,pod -l app=neo4j -o wide
kubectl -n swe-ai-fleet describe pod -l app=neo4j | sed -n '/Events:/,$p'

# Logs
kubectl -n swe-ai-fleet logs deploy/neo4j --tail=200 | cat
kubectl -n swe-ai-fleet logs -l app=neo4j --tail=200 --prefix | cat
kubectl -n swe-ai-fleet logs -l app=neo4j --previous --tail=200 | cat
```

---

## 🔴 Common Issues

- CrashLoopBackOff
- ImagePullBackOff
- Rollout timeouts
- Secrets validation
- ContainerStatusUnknown after node restart
- **vLLM Server: Error 803** (driver/CUDA mismatch) — see below
- **`curl (7) failed to open socket: Operation not permitted`** when calling `workspace` — see `WORKSPACE_CURL_SOCKET_ISSUE.md`

See the archived full guide for advanced CRI-O diagnostics if needed.

---

## 🖥️ vLLM Server: Error 803 (Driver / CUDA Mismatch)

**Symptom**: vLLM pods in `CrashLoopBackOff` with:

```text
RuntimeError: ... Error 803: system has unsupported display driver / cuda driver combination
```

**Cause**: The official image `vllm/vllm-openai:latest` is built with **CUDA 12.x**. If the **host** NVIDIA driver is newer (e.g. **590.x** reporting CUDA 13.1 after an OS update), the container’s CUDA 12 runtime can reject it with Error 803.

**Check host driver**:

```bash
nvidia-smi
# Driver Version and "CUDA Version" (max supported by driver) are shown
```

**Options**:

1. **Use a driver compatible with CUDA 12**  
   On the GPU node(s), install a driver version supported by CUDA 12 and avoid the 590+ branch if you keep using the official vLLM image. For the **open driver**, you can downgrade to **nvidia-open 570** from the Arch archive (see [30-microservices/VLLM_DRIVER_DOWNGRADE_CUDA12.md](30-microservices/VLLM_DRIVER_DOWNGRADE_CUDA12.md)). Reboot after changing the driver.

2. **Use a vLLM image built with CUDA 13**  
   Build vLLM from source with CUDA 13 and use that image in the vLLM deployment. See [30-microservices/VLLM_CUDA13_BUILD.md](30-microservices/VLLM_CUDA13_BUILD.md) for step-by-step instructions. Then set the deployment image to your built image (e.g. your registry) instead of `vllm/vllm-openai:latest`.

   ```bash
   make deploy-service-skip-build SERVICE=vllm-server \
     VLLM_SERVER_IMAGE=registry.example.com/your-namespace/vllm-openai:cu13
   kubectl rollout status deployment/vllm-server -n swe-ai-fleet --timeout=120s
   ```

   If CUDA 13 image still fails with Error 803, force host driver `libcuda` precedence:

   ```bash
   kubectl -n swe-ai-fleet set env deployment/vllm-server LD_LIBRARY_PATH=/usr/lib
   kubectl rollout status deployment/vllm-server -n swe-ai-fleet --timeout=120s
   ```

---

## 📋 Policy: Rollout Timeouts

Standard timeout for all rollout operations:

```bash
--timeout=120s
```

Use this consistently in:

- `kubectl rollout status`
- `kubectl wait --for=...`
- `kubectl scale`

---

## 🆘 When All Else Fails

### Nuclear Option: Full Reset

```bash
# Delete entire namespace and recreate
kubectl delete namespace swe-ai-fleet
kubectl wait --for=delete namespace/swe-ai-fleet --timeout=120s
# Recreate from scratch
./scripts/infra/fresh-redeploy-v2.sh --reset-nats
```

---

## 🔗 Related

- `DEPLOYMENT.md` - Deployment procedures
- `deploy/k8s/README.md` - K8s layout and tips
- `WORKSPACE_CURL_SOCKET_ISSUE.md` - Diagnóstico y solución para llamadas HTTP a `workspace`
- `WORKSPACE_PRODUCTION_RUNBOOK.md` - Validación operativa real de cluster/GPU + checklist de despliegue y smoke tests de `workspace`
