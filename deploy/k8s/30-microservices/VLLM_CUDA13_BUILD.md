# Building vLLM with CUDA 13 for Driver 590+ (Error 803 Fix)

When the **host** has an NVIDIA driver that reports CUDA 13.x (e.g. **590.48.01** after an OS update), the official image `docker.io/vllm/vllm-openai:latest` (built with CUDA 12.x) can fail with:

```text
RuntimeError: ... Error 803: system has unsupported display driver / cuda driver combination
```

This guide describes two options: **install vLLM with official CUDA 13.0 wheels** (recommended when available) or **build from source** with CUDA 13.

---

## Option 1: Official wheels for CUDA 13.0 (recommended)

vLLM publishes pre-built binaries for **CUDA 12.8, 12.9, and 13.0**. For driver 590 / CUDA 13.1, use the **CUDA 13.0** wheel so you avoid building from source.

**Install vLLM with CUDA 13.0 (host or in a container):**

```bash
# Resolve latest vLLM version and install wheel for CUDA 13.0
export VLLM_VERSION=$(curl -s https://api.github.com/repos/vllm-project/vllm/releases/latest | jq -r .tag_name | sed 's/^v//')
export CUDA_VERSION=130   # 130 = CUDA 13.0
export CPU_ARCH=$(uname -m)   # x86_64 or aarch64

uv pip install \
  "https://github.com/vllm-project/vllm/releases/download/v${VLLM_VERSION}/vllm-${VLLM_VERSION}+cu${CUDA_VERSION}-cp38-abi3-manylinux_2_35_${CPU_ARCH}.whl" \
  --extra-index-url "https://download.pytorch.org/whl/cu${CUDA_VERSION}"
```

Then run the server (e.g. `vllm serve ...` or your OpenAI-compatible entrypoint). To run this in Kubernetes, build a **custom Docker image** that uses a CUDA 13 base, runs the above install, and starts the vLLM server; push that image and set it in `vllm-server.yaml`.

---

## Option 2: Build from source with CUDA 13

Use this if you need a specific vLLM commit or the CUDA 13.0 wheel is not available for your platform.

---

### Prerequisites (Option 2)

- Docker (or Podman) with NVIDIA Container Toolkit on a machine that can build x86_64 images.
- Clone of [vllm-project/vllm](https://github.com/vllm-project/vllm) (or use a one-off clone below).

### Build the OpenAI image with CUDA 13

vLLM’s official [Dockerfile](https://github.com/vllm-project/vllm/blob/main/docker/Dockerfile) supports building with CUDA 13 via build args (see [vLLM Docker docs](https://docs.vllm.ai/en/stable/deployment/docker.html)).

**1. Clone vLLM (if you do not have it):**

```bash
git clone --depth 1 https://github.com/vllm-project/vllm.git
cd vllm
```

**2. Build the OpenAI image with CUDA 13:**

```bash
DOCKER_BUILDKIT=1 docker build . \
  --build-arg CUDA_VERSION=13.0.1 \
  --build-arg BUILD_BASE_IMAGE=docker.io/nvidia/cuda:13.0.1-devel-ubuntu22.04 \
  --build-arg max_jobs=8 \
  --build-arg nvcc_threads=2 \
  --target vllm-openai \
  --tag docker.io/vllm/vllm-openai:cu13 \
  -f docker/Dockerfile
```

Adjust `max_jobs` / `nvcc_threads` to your machine. Build can take a long time.

**3. (Optional) Precompiled wheels to speed up build**

To avoid full C++/CUDA compilation, you can use precompiled wheels (see vLLM docs). This may not offer a CUDA 13 wheel for every commit; if available:

```bash
# Example: use precompiled wheels (version/commit may need adjustment)
DOCKER_BUILDKIT=1 docker build . \
  --build-arg CUDA_VERSION=13.0.1 \
  --build-arg BUILD_BASE_IMAGE=docker.io/nvidia/cuda:13.0.1-devel-ubuntu22.04 \
  --build-arg VLLM_USE_PRECOMPILED=1 \
  --target vllm-openai \
  --tag docker.io/vllm/vllm-openai:cu13 \
  -f docker/Dockerfile
```

**4. Test locally (with GPU):**

```bash
docker run --rm -it --gpus all \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -p 8000:8000 \
  -e HF_TOKEN="${HF_TOKEN}" \
  docker.io/vllm/vllm-openai:cu13 \
  --model Qwen/Qwen3-0.6B --reasoning-parser qwen3
```

If the server starts and `/health` returns 200, the image is compatible with your driver.

---

## Use the image in Kubernetes

**Option A – Load on a node (e.g. kind/k3s single node)**

If your cluster runs on the same machine that built the image:

```bash
# For kind: kind load docker-image docker.io/vllm/vllm-openai:cu13
# For k3s: k3s ctr images import (after docker save)
docker save docker.io/vllm/vllm-openai:cu13 | sudo k3s ctr images import -
```

Then deploy `vllm-server` using that image (see below).

**Option B – Push to a registry**

Use a fully qualified image name (FQN): `registry.example.com/namespace/repository:tag`.

```bash
docker tag docker.io/vllm/vllm-openai:cu13 registry.example.com/your-namespace/vllm-openai:cu13
docker push registry.example.com/your-namespace/vllm-openai:cu13
```

**Update the deployment**

Use the deploy script image override (no YAML edit needed):

```bash
make deploy-service SERVICE=vllm-server SKIP_BUILD=1 \
  VLLM_SERVER_IMAGE=registry.example.com/your-namespace/vllm-openai:cu13

kubectl rollout status deployment/vllm-server -n swe-ai-fleet --timeout=120s
kubectl logs -n swe-ai-fleet -l app=vllm-server --tail=50
```

If you still get `Error 803`, set `LD_LIBRARY_PATH=/usr/lib` in the deployment so the container uses host `libcuda` instead of CUDA compatibility stubs:

```bash
kubectl -n swe-ai-fleet set env deployment/vllm-server LD_LIBRARY_PATH=/usr/lib
kubectl rollout status deployment/vllm-server -n swe-ai-fleet --timeout=120s
```

You can still edit `deploy/k8s/30-microservices/vllm-server.yaml` directly if preferred.

---

## Alternative: Downgrade host driver

If you prefer not to build an image, you can **downgrade the NVIDIA driver** on the GPU node(s) to a version compatible with CUDA 12 (e.g. 535.x or 550.x, avoiding 590+). Then the official `docker.io/vllm/vllm-openai:latest` may work. Reboot after changing the driver. See [K8S_TROUBLESHOOTING.md](../K8S_TROUBLESHOOTING.md#-vllm-server-error-803-driver--cuda-mismatch).

---

## Official sources (read in order)

vLLM provides **pre-built wheels for CUDA 12.8, 12.9, and 13.0** (see GPU installation doc). Use `CUDA_VERSION=130` for the cu13.0 wheel.

| Tema | Enlace |
|------|--------|
| **vLLM – GPU installation (wheels cu128/cu129/cu130)** | https://docs.vllm.ai/en/stable/getting_started/installation/gpu.html |
| **vLLM – Docker (build from source, CUDA 13)** | https://docs.vllm.ai/en/stable/deployment/docker.html |
| **vLLM – Dockerfile en GitHub** | https://github.com/vllm-project/vllm/blob/main/docker/Dockerfile |
| **vLLM – Build para otra versión CUDA (foro)** | https://discuss.vllm.ai/t/how-to-build-vllm-docker-image-for-different-cuda-version/1552 |
| **NVIDIA – Compatibilidad CUDA** | https://docs.nvidia.com/deploy/cuda-compatibility |
| **NVIDIA – CUDA Toolkit release notes** | https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/ |
| **Docker Hub – vllm-openai tags** | https://hub.docker.com/r/vllm/vllm-openai/tags |
