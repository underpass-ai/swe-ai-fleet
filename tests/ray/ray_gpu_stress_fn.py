#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass

import ray


@dataclass(frozen=True)
class StressStats:
    worker_id: int
    visible: str
    device_name: str
    dtype: str
    seconds: float
    matmul_shape: tuple[int, int, int]
    iterations: int
    iters_per_sec: float
    est_tflops: float

def _tflops(m: int, n: int, k: int, iters: int, secs: float) -> float:
    if secs <= 0:
        return 0.0
    return (2.0 * m * n * k * iters) / secs / 1e12

def _dtype_from_str(s: str):
    s = s.lower()
    if s in ("fp16", "float16", "half"):
        import torch
        return torch.float16
    if s in ("bf16", "bfloat16"):
        import torch
        return torch.bfloat16
    if s in ("fp32", "float32"):
        import torch
        return torch.float32
    raise ValueError(f"Unsupported dtype: {s}")

@ray.remote(num_gpus=1)
def gpu_stress_fn(worker_id: int, seconds: float, m: int, n: int, k: int,
                  dtype_str: str, allow_tf32: bool) -> StressStats:
    # Import inside the worker to avoid pickling big module state
    import torch

    torch.backends.cuda.matmul.allow_tf32 = bool(allow_tf32)
    torch.backends.cudnn.benchmark = True
    torch.set_num_threads(1)

    device = torch.device("cuda:0")  # GPU mapeada por Ray
    dtype = _dtype_from_str(dtype_str)
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")

    # Tensores grandes para saturar ALUs y memoria
    A = torch.randn(m, k, device=device, dtype=dtype)
    B = torch.randn(k, n, device=device, dtype=dtype)
    v = torch.randn(n, device=device, dtype=dtype)

    torch.cuda.synchronize()
    name = torch.cuda.get_device_name(device)

    # Warmup corto
    for _ in range(5):
        C = A @ B
        C = C + v
    torch.cuda.synchronize()

    end_t = time.perf_counter() + seconds
    iters = 0
    start = time.perf_counter()
    while time.perf_counter() < end_t:
        C = A @ B
        # mezclar elementwise para presión sostenida
        C = torch.nn.functional.silu(C)
        C = C.add_(0.1).mul_(0.9)
        iters += 1
        if (iters & 0x1F) == 0:
            torch.cuda.synchronize()

    torch.cuda.synchronize()
    secs = time.perf_counter() - start
    ips = iters / max(secs, 1e-6)
    tflops = _tflops(m, n, k, iters, secs)

    return StressStats(
        worker_id=worker_id,
        visible=visible,
        device_name=name,
        dtype=str(dtype).split(".")[-1],
        seconds=secs,
        matmul_shape=(m, n, k),
        iterations=iters,
        iters_per_sec=ips,
        est_tflops=tflops,
    )

def main() -> None:
    parser = argparse.ArgumentParser(description="Ray multi-GPU stress test without actors.")
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--m", type=int, default=12288)
    parser.add_argument("--n", type=int, default=12288)
    parser.add_argument("--k", type=int, default=12288)
    parser.add_argument("--dtype", type=str, default="fp16", choices=["fp16", "bf16", "fp32"])
    parser.add_argument("--workers", type=int, default=0, help="0 = one per detected GPU")
    parser.add_argument("--allow-tf32", action="store_true")
    args = parser.parse_args()

    ray.init(ignore_reinit_error=True)
    available = int(ray.available_resources().get("GPU", 0))
    num_workers = args.workers or available
    if num_workers < 1:
        raise RuntimeError("No GPUs reported by Ray.")

    print(
        f"Launching {num_workers} GPU task(s) for {args.seconds:.1f}s | "
        f"shape=({args.m},{args.n},{args.k}) dtype={args.dtype} TF32={args.allow_tf32}"
    )

    futures = [
        gpu_stress_fn.remote(i, args.seconds, args.m, args.n, args.k, args.dtype, args.allow_tf32)
        for i in range(num_workers)
    ]
    results: list[StressStats] = ray.get(futures)
    ray.shutdown()

    print("\n=== Ray GPU Stress Summary ===")
    for r in results:
        print(
            f"[W{r.worker_id}] GPU={r.device_name} "
            f"CUDA_VISIBLE_DEVICES={r.visible} dtype={r.dtype} "
            f"time={r.seconds:.1f}s iters={r.iterations} ips={r.iters_per_sec:.2f}/s "
            f"est_TFLOP/s={r.est_tflops:.2f}"
        )

if __name__ == "__main__":
    main()

