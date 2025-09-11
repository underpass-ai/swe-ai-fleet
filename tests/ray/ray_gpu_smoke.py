#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

import ray


@dataclass(frozen=True)
class GpuProbeResult:
    node: str
    pid: int
    cuda_visible_devices: str
    nvidia_smi: str


@ray.remote(num_gpus=1)
def gpu_probe() -> GpuProbeResult:
    """Run inside a Ray worker that reserves 1 GPU."""
    node = os.uname().nodename
    pid = os.getpid()
    # replace inside gpu_probe() in ray_gpu_smoke.py
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    cmd = ["nvidia-smi", "--query-gpu=index,name,uuid,memory.total", "--format=csv,noheader"]
    if visible:  # make nvidia-smi display only the scoped GPU(s)
        # CUDA_VISIBLE_DEVICES may be e.g. "0" or "0,1"
        cmd = [
            "nvidia-smi",
            "-i",
            visible,
            "--query-gpu=index,name,uuid,memory.total",
            "--format=csv,noheader",
        ]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=10)
    except Exception as e:
        out = f"nvidia-smi failed: {e}"
    return GpuProbeResult(node=node, pid=pid, cuda_visible_devices=visible, nvidia_smi=out.strip())


def main() -> None:
    # Local Ray; if a Ray cluster is already running, this will connect to it.
    ray.init(ignore_reinit_error=True)
    result: GpuProbeResult = ray.get(gpu_probe.remote())
    print("=== Ray GPU Smoke Test ===")
    print(f"Node: {result.node}")
    print(f"PID: {result.pid}")
    print(f"CUDA_VISIBLE_DEVICES: {result.cuda_visible_devices}")
    print("--- nvidia-smi (scoped) ---")
    print(result.nvidia_smi)
    ray.shutdown()


if __name__ == "__main__":
    main()

