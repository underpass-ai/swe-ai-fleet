#!/usr/bin/env python3
from __future__ import annotations

import os
import time
from dataclasses import dataclass

import ray
import torch


@dataclass(frozen=True)
class GpuBenchResult:
    worker_id: int
    visible: str
    device_count: int
    tflops: float
    secs: float

@ray.remote(num_gpus=1)
class GpuWorker:
    def __init__(self, worker_id: int, m: int = 8192, n: int = 8192, k: int = 8192, iters: int = 10) -> None:
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.set_num_threads(1)
        self.worker_id = worker_id
        self.visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
        self.device = torch.device("cuda:0")  # always index 0 inside the mapped namespace
        self.m, self.n, self.k, self.iters = m, n, k, iters
        self.A = torch.randn(self.m, self.k, device=self.device, dtype=torch.float16)
        self.B = torch.randn(self.k, self.n, device=self.device, dtype=torch.float16)
        torch.cuda.synchronize()

    def run(self) -> GpuBenchResult:
        start = time.perf_counter()
        for _ in range(self.iters):
            _ = self.A @ self.B
        torch.cuda.synchronize()
        secs = time.perf_counter() - start
        # FLOPs per GEMM ~ 2*m*n*k; iters times; convert to TFLOP/s
        tflops = (2 * self.m * self.n * self.k * self.iters) / secs / 1e12
        return GpuBenchResult(
            worker_id=self.worker_id,
            visible=self.visible,
            device_count=torch.cuda.device_count(),
            tflops=tflops,
            secs=secs,
        )

def main() -> None:
    ray.init(ignore_reinit_error=True)
    num_workers = min(2, int(os.environ.get("RAY_NUM_WORKERS", "2")))  # adjust if you want
    workers = [GpuWorker.remote(i) for i in range(num_workers)]
    results: list[GpuBenchResult] = ray.get([w.run.remote() for w in workers])
    ray.shutdown()

    print("\n=== Ray GPU GEMM Benchmark ===")
    for r in results:
        print(f"[W{r.worker_id}] CUDA_VISIBLE_DEVICES={r.visible} "
              f"device_count={r.device_count} "
              f"TFLOP/s={r.tflops:.2f} time={r.secs:.2f}s")

if __name__ == "__main__":
    assert torch.cuda.is_available(), "CUDA not available"
    main()

