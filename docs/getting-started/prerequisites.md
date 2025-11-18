# Prerequisites

Before deploying SWE AI Fleet, ensure your environment meets the following requirements.

## 🖥️ Hardware Requirements

### Minimum (Testing/PoC)
-   **CPU**: 8+ Cores
-   **RAM**: 32 GB+
-   **GPU**: NVIDIA GPU with 16GB+ VRAM (e.g., RTX 3090, RTX 4090, A10G)
-   **Storage**: 100GB SSD

### Recommended (Production)
-   **CPU**: 32+ Cores (AMD Threadripper / EPYC preferred)
-   **RAM**: 128 GB+
-   **GPU**: Multiple NVIDIA GPUs (e.g., 2x RTX 3090 or 1x A100 80GB)
-   **Storage**: 1TB NVMe SSD

> **Note**: The "Precision Context" architecture allows us to use smaller consumer GPUs (RTX 3090/4090) instead of massive A100 clusters.

---

## 🛠️ Software Requirements

### Operating System
-   **Linux** (Arch, Ubuntu, Debian preferred).
-   Windows WSL2 and macOS are theoretically supported but not officially tested.

### Tools
-   **[Podman](https://podman.io/)** (or Docker): Container runtime.
-   **[Kubernetes](https://kubernetes.io/)** (v1.28+): We use standard K8s manifests.
-   **[kubectl](https://kubernetes.io/docs/tasks/tools/)**: CLI for Kubernetes.
-   **[Python](https://www.python.org/)** (3.13+): For local development and scripts.
-   **[Make](https://www.gnu.org/software/make/)**: For build automation.

### Kubernetes Add-ons
The following will be installed by our setup scripts if missing, or you should have them ready:
-   **NVIDIA GPU Operator**: For GPU support.
-   **Cert-Manager**: For TLS certificates.
-   **Ingress-Nginx**: For routing traffic.
-   **KubeRay Operator**: For managing the Ray cluster.

