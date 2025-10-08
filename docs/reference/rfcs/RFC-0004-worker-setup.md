# 🖥️ Worker Node Setup (GPU + CRI-O + Ray)

This document describes how we configured an Arch Linux worker node with NVIDIA GPUs, **CRI-O**, and **Ray** to participate in the [SWE AI Fleet](https://github.com/underpass-ai/swe-ai-fleet).  

The node was validated with GPU stress tests, Ray job submission, and automated metrics collection/reporting.

---

## 1. System Overview

- **OS**: Arch Linux  
- **User**: `ia`  
- **Hardware**: 2 × NVIDIA RTX 3090  
  - GPU0: PCIe Gen3 x4  
  - GPU1: PCIe Gen4 x16  

---

## 2. Install CRI-O with NVIDIA Runtime

```bash
yay -S cri-o nvidia-container-toolkit
sudo systemctl enable --now crio
```

Configure runtime:

```bash
sudo nvidia-ctk runtime configure --runtime=crio
sudo systemctl restart crio
```

Check `crio.conf`:

```toml
[crio.runtime.runtimes.nvidia]
runtime_path = "/usr/bin/nvidia-container-runtime"
```

---

## 3. Enable CDI (Container Device Interface)

```bash
sudo mkdir -p /etc/cdi
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
```

This allows Ray (and Kubernetes in the future) to allocate GPUs in a portable way.

---

## 4. Verify GPU Access via CRI-O

Pull CUDA image:

```bash
sudo crictl pull docker.io/nvidia/cuda:12.4.1-runtime-ubuntu22.04
```

Minimal specs:

```jsonc
// pod.json
{
  "metadata": { "name": "gpu-pod", "namespace": "default", "uid": "uidgpu", "attempt": 1 },
  "log_directory": "/tmp"
}

// ctr.json
{
  "metadata": { "name": "gpu-container" },
  "image": { "image": "docker.io/nvidia/cuda:12.4.1-runtime-ubuntu22.04" },
  "command": ["nvidia-smi"],
  "envs": [
    { "name": "NVIDIA_VISIBLE_DEVICES", "value": "all" },
    { "name": "NVIDIA_DRIVER_CAPABILITIES", "value": "all" }
  ]
}
```

Run and check logs:

```bash
POD=$(sudo crictl runp --runtime nvidia pod.json)
CTR=$(sudo crictl create "$POD" ctr.json pod.json)
sudo crictl start "$CTR"
sudo crictl logs "$CTR"
```

✔️ Should output `nvidia-smi` with both GPUs.

---

## 5. Install Ray + PyTorch

```bash
pip install 'ray[default]' torch
```

---

## 6. Ray GPU Tests

### GPU Smoke Test
```python
import ray, torch, os
ray.init()

@ray.remote(num_gpus=2)
def torch_probe():
    return {
        "visible": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "cuda_is_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count(),
        "name": torch.cuda.get_device_name(0),
    }

print(ray.get(torch_probe.remote()))
ray.shutdown()
```

---

## 7. GEMM and Stress Benchmarks

### GEMM benchmark
~57 TFLOPs per GPU (FP16).

### Stress test
```bash
python ray_gpu_stress_fn.py --seconds 120 --dtype fp16 --allow-tf32
```

✔️ Both GPUs fully loaded (≈350W each, ≤68 °C).

---

## 8. Ray Job Submission

Start Ray head node:

```bash
ray start --head --dashboard-host=0.0.0.0 --port=6379
```

- Cluster address: `ray-gpu-head-svc.ray.svc.cluster.local:10001`
- Jobs API: `http://127.0.0.1:8265`

Submit jobs:

```bash
ray job submit   --address http://127.0.0.1:8265   --runtime-env-json '{"working_dir":"./jobs"}'   -- python hello.py
```

✔️ Output: `Hello from Ray!`

---

## 9. GPU Stress + Metrics Job

We extended the stress job to collect per-second GPU metrics (via `nvidia-smi`):

- utilization.gpu  
- memory.used  
- temperature  
- power.draw  
- clocks.sm  
- clocks.mem  
- fan.speed  

Each worker writes a CSV file:

```text
./results/gpu_metrics_W0_<timestamp>.csv
./results/gpu_metrics_W1_<timestamp>.csv
```

Summary:

```
[W0] GPU=RTX 3090 CUDA_VISIBLE_DEVICES=0 time=181s ips=19.4/s est_TFLOP/s=71.9
[W1] GPU=RTX 3090 CUDA_VISIBLE_DEVICES=1 time=180s ips=19.3/s est_TFLOP/s=71.5
```

---

## 10. Plotting & Reporting

Script: `plot_gpu_metrics_report.py`

- Reads CSVs from `--results-dir`
- Generates per-metric PNG plots
- Creates multipage PDF report with all charts

Usage:

```bash
python plot_gpu_metrics_report.py   --results-dir ./results   --out-dir ./results/plots   --report-name metrics_report.pdf   --write-summary
```

Output:  
- PNG charts for each metric  
- `metrics_report.pdf`  

---

## 11. Automated Runner

Script: `run_stress_and_report.py`

- Submits GPU stress job via Ray Jobs API
- Waits for results
- Runs plotting/report generation

Usage:

```bash
python run_stress_and_report.py   --address http://127.0.0.1:8265   --working-dir ./jobs   --results-dir ./results   --out-dir ./results/plots   --seconds 180 --dtype fp16 --allow-tf32 --write-summary
```

✔️ Produces CSVs, PNGs, and a PDF report.

---

## ✅ Final Status

- Worker node runs **CRI-O with NVIDIA runtime**.  
- Ray head node up with Jobs API (8265).  
- GPUs validated with stress tests.  
- Automated metrics + reporting pipeline ready.  

This node is ready to join the **SWE AI Fleet** as a GPU worker.