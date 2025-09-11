#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import ray


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


def _results_dir(preferred: str = "./results") -> str:
    try:
        os.makedirs(preferred, exist_ok=True)
        # Try writing a tiny file to confirm writability.
        test_path = os.path.join(preferred, ".write_test")
        with open(test_path, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(test_path)
        return preferred
    except Exception:
        fallback = "/tmp/gpu-stress-results"
        os.makedirs(fallback, exist_ok=True)
        return fallback


def _sample_nvidia_smi_csv(gpu_id: str) -> dict[str, str]:
    """Query a fixed set of metrics from nvidia-smi for one GPU id."""
    import subprocess

    fields = [
        "timestamp",
        "power.draw",
        "temperature.gpu",
        "utilization.gpu",
        "utilization.memory",
        "fan.speed",
        "clocks.sm",
        "clocks.mem",
        "memory.total",
        "memory.used",
        "pcie.link.gen.current",
        "pcie.link.width.current",
    ]
    # NOTE: 'timestamp' is synthesized here with host time for monotonic sampling.
    query = ",".join(fields[1:])
    cmd = [
        "nvidia-smi",
        "-i",
        gpu_id or "0",
        "--query-gpu=" + query,
        "--format=csv,noheader,nounits",
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
        vals = [v.strip() for v in out.split(",")]
        now = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00","Z")
        data = dict(zip(fields[1:], vals, strict=False))
        data["timestamp"] = now
        return data
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "power.draw": "NA",
            "temperature.gpu": "NA",
            "utilization.gpu": "NA",
            "utilization.memory": "NA",
            "clocks.sm": "NA",
            "clocks.mem": "NA",
            "memory.total": "NA",
            "memory.used": "NA",
            "pcie.link.gen.current": "NA",
            "pcie.link.width.current": "NA",
            "_error": str(e),
        }


@ray.remote(num_gpus=1)
def gpu_stress_with_metrics(worker_id: int,
                            seconds: float,
                            m: int,
                            n: int,
                            k: int,
                            dtype_str: str,
                            allow_tf32: bool,
                            sample_period: float,
                            out_dir: str) -> dict[str, object]:
    import torch

    torch.backends.cuda.matmul.allow_tf32 = bool(allow_tf32)
    torch.backends.cudnn.benchmark = True
    torch.set_num_threads(1)

    device = torch.device("cuda:0")
    dtype = _dtype_from_str(dtype_str)
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    gpu_id = (visible.split(",")[0] if visible else "0").strip()

    # Allocate big operands (compute-bound)
    A = torch.randn(m, k, device=device, dtype=dtype)
    B = torch.randn(k, n, device=device, dtype=dtype)
    v = torch.randn(n, device=device, dtype=dtype)
    torch.cuda.synchronize()
    gpu_name = torch.cuda.get_device_name(device)

    # Prepare CSV writer
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    csv_path = os.path.join(out_dir, f"gpu_metrics_W{worker_id}_{ts}.csv")
    header = [
        "timestamp",
        "power.draw.W",
        "temperature.gpu.C",
        "utilization.gpu.%",
        "utilization.memory.%",
        "fan.speed.%",
        "clocks.sm.MHz",
        "clocks.mem.MHz",
        "memory.total.MiB",
        "memory.used.MiB",
        "pcie.link.gen",
        "pcie.link.width",
    ]
    # Warmup
    for _ in range(5):
        C = A @ B
        C = C + v
    torch.cuda.synchronize()

    start = time.perf_counter()
    next_sample = start
    end_t = start + seconds
    iters = 0

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["worker_id", "gpu_name", "CUDA_VISIBLE_DEVICES", "gpu_id"])
        w.writerow([worker_id, gpu_name, visible, gpu_id])
        w.writerow(header)
        # Main loop
        while True:
            now = time.perf_counter()
            if now >= end_t:
                break

            # Compute chunk
            C = A @ B
            C = torch.nn.functional.silu(C)
            C = C.add_(0.1).mul_(0.9)
            iters += 1

            # Sample at fixed rate
            if now >= next_sample:
                sample = _sample_nvidia_smi_csv(gpu_id)
                # Normalize order and names to header
                row = [
                    sample.get("timestamp", ""),
                    sample.get("power.draw", ""),
                    sample.get("temperature.gpu", ""),
                    sample.get("utilization.gpu", ""),
                    sample.get("utilization.memory", ""),
                    sample.get("fan.speed", ""),
                    sample.get("clocks.sm", ""),
                    sample.get("clocks.mem", ""),
                    sample.get("memory.total", ""),
                    sample.get("memory.used", ""),
                    sample.get("pcie.link.gen.current", ""),
                    sample.get("pcie.link.width.current", ""),
                ]
                w.writerow(row)
                next_sample += sample_period

            # Bound device queue
            if (iters & 0x1F) == 0:
                torch.cuda.synchronize()

        torch.cuda.synchronize()

    secs = time.perf_counter() - start
    return {
        "worker_id": worker_id,
        "gpu_name": gpu_name,
        "visible": visible,
        "gpu_id": gpu_id,
        "dtype": str(dtype).split(".")[-1],
        "seconds": round(secs, 2),
        "shape": (m, n, k),
        "iterations": iters,
        "iters_per_sec": round(iters / max(secs, 1e-6), 2),
        "est_TFLOP_s": round(_tflops(m, n, k, iters, secs), 2),
        "metrics_csv": csv_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ray GPU stress + per-second CSV metrics.")
    parser.add_argument("--seconds", type=float, default=180.0)
    parser.add_argument("--m", type=int, default=12288)
    parser.add_argument("--n", type=int, default=12288)
    parser.add_argument("--k", type=int, default=12288)
    parser.add_argument("--dtype", type=str, default="fp16", choices=["fp16", "bf16", "fp32"])
    parser.add_argument("--workers", type=int, default=0, help="0 = one per detected GPU")
    parser.add_argument("--allow-tf32", action="store_true")
    parser.add_argument(
        "--sample-period",
        type=float,
        default=1.0,
        help="Seconds between nvidia-smi samples.",
    )
    parser.add_argument("--results-dir", type=str, default="./results", help="Directory to save CSV metrics")

    args = parser.parse_args()

    # Normalize and ensure the results directory exists
    results_dir = Path(args.results_dir).expanduser().resolve()
    results_dir.mkdir(parents=True, exist_ok=True)

    ray.init(ignore_reinit_error=True)

    # Determine number of workers
    available = int(ray.available_resources().get("GPU", 0))
    num_workers = args.workers or available
    if num_workers < 1:
        raise RuntimeError("No GPUs reported by Ray.")
    num_workers = min(num_workers, available)

    print(f"Results directory: {results_dir}")
    print(
        f"Launching {num_workers} GPU task(s) for {args.seconds:.1f}s | "
        f"shape=({args.m},{args.n},{args.k}) dtype={args.dtype} TF32={args.allow_tf32} "
        f"sample={args.sample_period:.1f}s"
    )

    futures = [
        gpu_stress_with_metrics.remote(
            i,
            args.seconds,
            args.m,
            args.n,
            args.k,
            args.dtype,
            args.allow_tf32,
            args.sample_period,
            str(results_dir),  # pass as str to the worker
        )
        for i in range(num_workers)
    ]

    results: list[dict[str, object]] = ray.get(futures)
    ray.shutdown()

    print("\n=== Ray GPU Stress + Metrics Summary ===")
    for r in results:
        m, n, k = r["shape"]
        print(
            f"[W{r['worker_id']}] GPU={r['gpu_name']} id={r['gpu_id']} "
            f"CUDA_VISIBLE_DEVICES={r['visible']} dtype={r['dtype']} "
            f"time={r['seconds']}s iters={r['iterations']} ips={r['iters_per_sec']}/s "
            f"est_TFLOP/s={r['est_TFLOP_s']} (shape {m}x{n}x{k})"
        )
        print(f"  metrics_csv: {r['metrics_csv']}")


if __name__ == "__main__":
    main()

