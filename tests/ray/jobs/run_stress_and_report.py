#!/usr/bin/env python3
"""
End-to-end runner:
1) Submit gpu_stress_metrics_job.py to Ray Jobs.
2) On success, generate PNGs + multi-page PDF with plot_gpu_metrics_report.py.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunConfig:
    ray_bin: str
    address: str
    working_dir: Path
    results_dir: Path
    seconds: float
    m: int
    n: int
    k: int
    dtype: str
    allow_tf32: bool
    sample_period: float
    out_dir: Path
    report_name: str
    write_summary: bool


def _build_ray_job_cmd(cfg: RunConfig) -> list[str]:
    runtime_env = (
        f'{{"working_dir":"{str(cfg.working_dir)}",'
        f'"env_vars":{{"OMP_NUM_THREADS":"1","MKL_NUM_THREADS":"1"}}}}'
    )
    job_args = [
        "job",
        "submit",
        "--address", cfg.address,
        "--runtime-env-json", runtime_env,
        "--",
        "python", "gpu_stress_metrics_job.py",
        "--seconds", str(cfg.seconds),
        "--m", str(cfg.m),
        "--n", str(cfg.n),
        "--k", str(cfg.k),
        "--dtype", cfg.dtype,
        "--sample-period", str(cfg.sample_period),
        "--results-dir", str(cfg.results_dir),
    ]
    if cfg.allow_tf32:
        job_args.insert(len(job_args) - 2, "--allow-tf32")  # before script args end
    return [cfg.ray_bin] + job_args


def _build_plot_cmd(cfg: RunConfig) -> list[str]:
    return [
        sys.executable,
        str(cfg.working_dir / "plot_gpu_metrics_report.py"),
        "--results-dir", str(cfg.results_dir),
        "--out-dir", str(cfg.out_dir),
        "--report-name", cfg.report_name,
    ] + (["--write-summary"] if cfg.write_summary else [])


def _run_process(cmd: list[str]) -> int:
    # Stream output directly; fail fast on non-zero exit.
    try:
        completed = subprocess.run(cmd, check=False)
        return completed.returncode
    except FileNotFoundError as e:
        print(f"[ERROR] Command not found: {e}", file=sys.stderr)
        return 127


def parse_args() -> RunConfig:
    p = argparse.ArgumentParser(description="Run Ray GPU stress job and generate a metrics report.")
    # Ray / environment
    p.add_argument("--ray-bin", type=str, default="ray", help="Ray CLI binary path")
    p.add_argument("--address", type=str, default="http://127.0.0.1:8265", help="Ray Jobs API address")
    p.add_argument(
        "--working-dir",
        type=Path,
        default=Path("/home/ia/ia-ray/jobs"),
        help="Ray runtime working_dir",
    )
    # Job parameters
    p.add_argument(
        "--results-dir",
        type=Path,
        default=Path("/home/ia/ia-ray/results"),
        help="Directory for CSVs",
    )
    p.add_argument("--seconds", type=float, default=180.0)
    p.add_argument("--m", type=int, default=12288)
    p.add_argument("--n", type=int, default=12288)
    p.add_argument("--k", type=int, default=12288)
    p.add_argument("--dtype", type=str, choices=["fp16", "bf16", "fp32"], default="fp16")
    p.add_argument("--allow-tf32", action="store_true")
    p.add_argument("--sample-period", type=float, default=1.0)
    # Report parameters
    p.add_argument("--out-dir", type=Path, default=Path("/home/ia/ia-ray/results/plots"))
    p.add_argument("--report-name", type=str, default="metrics_report.pdf")
    p.add_argument("--write-summary", action="store_true")

    args = p.parse_args()

    results_dir = args.results_dir.expanduser().resolve()
    out_dir = args.out_dir.expanduser().resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    return RunConfig(
        ray_bin=args.ray_bin,
        address=args.address,
        working_dir=args.working_dir.expanduser().resolve(),
        results_dir=results_dir,
        seconds=args.seconds,
        m=args.m,
        n=args.n,
        k=args.k,
        dtype=args.dtype,
        allow_tf32=args.allow_tf32,
        sample_period=args.sample_period,
        out_dir=out_dir,
        report_name=args.report_name,
        write_summary=bool(args.write_summary),
    )


def main() -> None:
    cfg = parse_args()

    print(f"[INFO] Submitting Ray job to {cfg.address}")
    print(f"[INFO] Working dir: {cfg.working_dir}")
    print(f"[INFO] Results dir:  {cfg.results_dir}")
    job_cmd = _build_ray_job_cmd(cfg)
    rc = _run_process(job_cmd)
    if rc != 0:
        print(f"[ERROR] Ray job failed with exit code {rc}", file=sys.stderr)
        sys.exit(rc)

    print("[INFO] Generating plots and PDF report…")
    plot_cmd = _build_plot_cmd(cfg)
    rc = _run_process(plot_cmd)
    if rc != 0:
        print(f"[ERROR] Plot/report generation failed with exit code {rc}", file=sys.stderr)
        sys.exit(rc)

    print(f"[OK] Report ready: {cfg.out_dir / cfg.report_name}")
    print(f"[OK] PNGs in:      {cfg.out_dir}")


if __name__ == "__main__":
    main()

