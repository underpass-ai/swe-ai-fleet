#!/usr/bin/env python3
import argparse
import glob
import os

import matplotlib.pyplot as plt
import pandas as pd


def parse_args():
    ap = argparse.ArgumentParser(
        description="Plot GPU metrics CSVs produced by gpu_stress_metrics_job.py"
    )
    ap.add_argument(
        "--results-dir",
        type=str,
        default="./results",
        help="Directory with gpu_metrics_*.csv files",
    )
    ap.add_argument("--show", action="store_true", help="Show on screen instead of saving PNGs")
    ap.add_argument("--out-dir", type=str, default="./results/plots", help="Output directory for figures")
    return ap.parse_args()


def load_csvs(results_dir: str):
    paths = sorted(glob.glob(os.path.join(results_dir, "gpu_metrics_*.csv")))
    if not paths:
        raise FileNotFoundError(f"No CSV files found in {results_dir} (pattern gpu_metrics_*.csv).")
    frames = []
    for p in paths:
        # First two lines are metadata rows; header is on the third line
        df = pd.read_csv(p, skiprows=2)
        # Inject worker_id from filename
        base = os.path.basename(p)
        # expected: gpu_metrics_W<id>_YYYYMMDDThhmmssZ.csv
        try:
            w = int(base.split("_")[2][1:])  # 'W0' -> 0
        except Exception:
            w = -1
        df["worker_id"] = w
        df["__file"] = base
        # Parse timestamp
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        frames.append(df)
    return pd.concat(frames, ignore_index=True).sort_values(["worker_id", "timestamp"])


def plot_timeseries(df: pd.DataFrame, ycol: str, ylabel: str, args, filename: str):
    fig = plt.figure(figsize=(10, 5))
    for w, sdf in df.groupby("worker_id"):
        plt.plot(sdf["timestamp"], pd.to_numeric(sdf[ycol], errors="coerce"), label=f"W{w}")
    plt.xlabel("Time (UTC)")
    plt.ylabel(ylabel)
    plt.title(f"{ylabel} over time")
    plt.legend()
    plt.tight_layout()
    if args.show:
        plt.show()
    else:
        os.makedirs(args.out_dir, exist_ok=True)
        out = os.path.join(args.out_dir, filename)
        plt.savefig(out, dpi=150)
        print(f"Saved {out}")
    plt.close(fig)


def main():
    args = parse_args()
    df = load_csvs(args.results_dir)

    # Columns (strings) expected from the job CSVs:
    # timestamp, power.draw.W, temperature.gpu.C, utilization.gpu.%,
    # utilization.memory.%, fan.speed.%, clocks.sm.MHz, clocks.mem.MHz,
    # memory.total.MiB, memory.used.MiB, pcie.link.gen, pcie.link.width

    # GPU utilization
    plot_timeseries(df, "utilization.gpu.%", "GPU Utilization (%)", args, "util_gpu.png")
    # Power
    plot_timeseries(df, "power.draw.W", "Power Draw (W)", args, "power.png")
    # Temperature
    plot_timeseries(df, "temperature.gpu.C", "Temperature (°C)", args, "temperature.png")
    # Fan
    plot_timeseries(df, "fan.speed.%", "Fan Speed (%)", args, "fan_speed.png")
    # SM clocks
    plot_timeseries(df, "clocks.sm.MHz", "SM Clock (MHz)", args, "clock_sm.png")
    # Memory clocks
    plot_timeseries(df, "clocks.mem.MHz", "Memory Clock (MHz)", args, "clock_mem.png")

    # Bonus: memory used
    plot_timeseries(df, "memory.used.MiB", "Memory Used (MiB)", args, "mem_used.png")


if __name__ == "__main__":
    main()

