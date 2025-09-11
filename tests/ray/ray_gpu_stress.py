#!/usr/bin/env python3
from __future__ import annotations
import argparse
import os
import time
from dataclasses import dataclass
from typing import List, Tuple

import ray
import torch


@dataclass(frozen=True)
class StressStats:
    worker_id: int
    visible: str
    device_name: str
    dtype: str
    seconds: float
    matmul_shape: Tuple[int, int, int]
    iterations: int
    iters_per_sec: float
    est_tflops: float


def _dtype_from_str(s: str) -> torch.dtype:
    s = s.lower()
    if s in ("fp16", "float16", "half"):
        return torch.float16
    if s in ("bf16", "bfloat16"):
        return torch.bfloat16
    if s in ("fp32", "float32"):
        return torch.float32
    raise ValueError(f"Unsupported dtype: {s}")


def _tflops(m: int, n: int, k: int, iters: int, secs: float) -> float:
    # GEMM FLOPs ~ 2*m*n*k per iteration
    if secs <= 0:
        return 0.0
    return (2.0 * m * n * k * iters) / secs / 1e12


@ray.remote(num_gpus=1)
class GpuStresser:
    def __init__(self, worker_id: int, m: int, n: int, k: int, dtype_str: str, allow_tf32: bool):
        self.worker_id = worker_id
        self.visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
        self.device = torch.device("cuda:0")  # mapped inside Ray's namespace
        self.dtype = _dtype_from_str(dtype_str)

        torch.backends.cuda.matmul.allow_tf32 = bool(allow_tf32)
        torch.backends.cudnn.benchmark = True
        torch.set_num_threads(1)

        # Allocate large operands once to avoid HtoD churn
        self.A = torch.randn(m, k, device=self.device, dtype=self.dtype)
        self.B = torch.randn(k, n, device=self.device, dtype=self.dtype)
        # Add a vector for elementwise ops to keep ALUs busy between GEMMs
        self.v = torch.randn(n, device=self.device, dtype=self.dtype)

        torch.cuda.synchronize()
        self.m, self.n, self.k = m, n, k
        self.name = torch.cuda.get_device_name(self.device)

    def run(self, seconds: float) -> StressStats:
        end_t = time.perf_counter() + seconds
        iters = 0

        # Warmup
        for _ in range(5):
            C = self.A @ self.B
            C = C + self.v  # fuse a trivial elementwise op
        torch.cuda.synchronize()

        start = time.perf_counter()
        while time.perf_counter() < end_t:
            # Matmul dominates; elementwise to avoid sitting in matmul cache too predictably
            C = self.A @ self.B
            C = torch.nn.functional.silu(C)
            # Optional extra op to increase register pressure
            C = C.add_(0.1).mul_(0.9)
            iters += 1

            # Avoid host sync every iter; periodically sync to keep the device queue bounded
            if (iters & 0x1F) == 0:  # every 32 iterations
                torch.cuda.synchronize()

        torch.cuda.synchronize()
        secs = time.perf_counter() - start
        ips = iters / max(secs, 1e-6)
        tflops = _tflops(self.m, self.n, self.k, iters, secs)

        return StressStats(
            worker_id=self.worker_id,
            visible=self.visible,
            device_name=self.name,
            dtype=str(self.dtype).split(".")[-1],
            seconds=secs,
            matmul_shape=(self.m, self.n, self.k),
            iterations=iters,
            iters_per_sec=ips,
            est_tflops=tflops,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ray multi-GPU stress test (sustained high utilization).")
    parser.add_argument("--seconds", type=float, default=120.0, help="Stress duration per worker (seconds).")
    parser.add_argument("--m", type=int, default=12288, help="GEMM M dimension.")
    parser.add_argument("--n", type=int, default=12288, help="GEMM N dimension.")
    parser.add_argument("--k", type=int, default=12288, help="GEMM K dimension.")
    parser.add_argument("--dtype", type=str, default="fp16", choices=["fp16", "bf16", "fp32"], help="Compute dtype.")
    parser.add_argument("--workers", type=int, default=0, help="Number of GPU workers (0 = one per detected GPU).")
    parser.add_argument("--allow-tf32", action="store_true", help="Allow TF32 (on Ampere+) to boost FP32 throughput.")
    args = parser.parse_args()

    assert torch.cuda.is_available(), "CUDA not available on host."

    ray.init(ignore_reinit_error=True)
    # Determine how many workers to launch
    available = int(ray.available_resources().get("GPU", 0))
    num_workers = args.workers or available
    if num_workers < 1:
        raise RuntimeError("No GPUs reported by Ray. Check drivers and Ray init.")

    # Cap by available GPUs
    num_workers = min(num_workers, available)

    print(f"Launching {num_workers} GPU worker(s) for {args.seconds:.1f}s | "
          f"shape=({args.m},{args.n},{args.k}) dtype={args.dtype} TF32={args.allow_tf32}")

    workers = [
        GpuStresser.remote(i, args.m, args.n, args.k, args.dtype, args.allow_tf32)
        for i in range(num_workers)
    ]
    results: List[StressStats] = ray.get([w.run.remote(args.seconds) for w in workers])
    ray.shutdown()

    print("\n=== Ray GPU Stress Summary ===")
    for r in results:
        shape = "x".join(map(str, r.matmul_shape))
        print(f"[W{r.worker_id}] GPU={r.device_name} "
              f"CUDA_VISIBLE_DEVICES={r.visible} dtype={r.dtype} "
              f"time={r.seconds:.1f}s iters={r.iterations} ips={r.iters_per_sec:.2f}/s "
              f"est_TFLOP/s={r.est_tflops:.2f}")


if __name__ == "__main__":
    main()

