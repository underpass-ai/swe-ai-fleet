#!/usr/bin/env python3
"""
Headless plotting for GPU stress CSVs:
- Saves PNGs per metric
- Builds a multi-page PDF report
- Emits a summary CSV (min/avg/max) per worker and metric
"""
from __future__ import annotations
import argparse
import glob
import os
from pathlib import Path
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd


METRIC_COLUMNS = {
    "utilization.gpu.%":     ("GPU Utilization (%)", "GPU Utilization (%) over time", "util_gpu"),
    "power.draw.W":          ("Power Draw (W)",      "Power Draw (W) over time",      "power"),
    "temperature.gpu.C":     ("Temperature (°C)",    "Temperature (°C) over time",    "temperature"),
    "fan.speed.%":           ("Fan Speed (%)",       "Fan Speed (%) over time",       "fan_speed"),
    "clocks.sm.MHz":         ("SM Clock (MHz)",      "SM Clock (MHz) over time",      "clock_sm"),
    "clocks.mem.MHz":        ("Memory Clock (MHz)",  "Memory Clock (MHz) over time",  "clock_mem"),
    "memory.used.MiB":       ("Memory Used (MiB)",   "Memory Used (MiB) over time",   "mem_used"),
}

def _load_csvs(results_dir: Path) -> pd.DataFrame:
    paths = sorted(glob.glob(str(results_dir / "gpu_metrics_*.csv")))
    if not paths:
        raise FileNotFoundError(f"No CSV files found in {results_dir} (pattern gpu_metrics_*.csv)")
    frames: List[pd.DataFrame] = []
    for p in paths:
        df = pd.read_csv(p, skiprows=2)  # first 2 lines are metadata
        base = os.path.basename(p)
        try:
            worker_id = int(base.split("_")[2][1:])  # gpu_metrics_W0_*.csv -> 0
        except Exception:
            worker_id = -1
        df["worker_id"] = worker_id
        df["__file"] = base
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        frames.append(df)
    return pd.concat(frames, ignore_index=True).sort_values(["worker_id", "timestamp"])

def _plot_timeseries(df: pd.DataFrame, ycol: str, ylabel: str, title: str):
    fig = plt.figure(figsize=(10, 5))
    for w, sdf in df.groupby("worker_id"):
        y = pd.to_numeric(sdf[ycol], errors="coerce")
        plt.plot(sdf["timestamp"], y, label=f"W{w}")
    plt.xlabel("Time (UTC)")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    return fig

def _summarize(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = [c for c in df.columns if any(c.startswith(k.split(".")[0]) for k in METRIC_COLUMNS.keys())]
    # Keep only metrics we care about and are numeric
    keep = [c for c in METRIC_COLUMNS.keys() if c in df.columns]
    df_num = df[["worker_id"] + keep].apply(pd.to_numeric, errors="coerce")
    agg = df_num.groupby("worker_id").agg(["min", "mean", "max"])
    agg.columns = [f"{m}__{stat}" for m, stat in agg.columns]
    return agg.reset_index()

def main():
    ap = argparse.ArgumentParser(description="Generate PNGs and a multi-page PDF from GPU metrics CSVs.")
    ap.add_argument("--results-dir", type=str, default="./results", help="Directory containing gpu_metrics_*.csv")
    ap.add_argument("--out-dir", type=str, default="./results/plots", help="Output directory for figures/report")
    ap.add_argument("--report-name", type=str, default="metrics_report.pdf", help="PDF report filename")
    ap.add_argument("--write-summary", action="store_true", help="Also write summary CSV (min/avg/max)")
    args = ap.parse_args()

    results_dir = Path(args.results_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    df = _load_csvs(results_dir)

    pdf_path = out_dir / args.report_name
    with PdfPages(pdf_path) as pdf:
        # Title page
        title_fig = plt.figure(figsize=(10, 5))
        title_fig.text(0.5, 0.7, "GPU Metrics Report", ha="center", va="center", fontsize=20)
        time_range = f"{df['timestamp'].min()} → {df['timestamp'].max()}"
        title_fig.text(0.5, 0.5, f"Files: {len(df['__file'].unique())} | Workers: {len(df['worker_id'].unique())}", ha="center")
        title_fig.text(0.5, 0.4, f"Time window: {time_range}", ha="center")
        title_fig.tight_layout()
        pdf.savefig(title_fig)
        plt.close(title_fig)

        for col, (ylabel, title, base) in METRIC_COLUMNS.items():
            if col not in df.columns:
                continue
            fig = _plot_timeseries(df, col, ylabel, title)
            # Save PNG
            png_path = out_dir / f"{base}.png"
            fig.savefig(png_path, dpi=150)
            # Append to PDF
            pdf.savefig(fig)
            plt.close(fig)

        # Optional summary page
        if args.write_summary:
            summary = _summarize(df)
            csv_path = out_dir / "summary_stats.csv"
            summary.to_csv(csv_path, index=False)

            fig = plt.figure(figsize=(11.7, 8.3))  # A4 landscape
            plt.axis("off")
            plt.title("Summary (min / mean / max) per worker", pad=20)
            tbl = plt.table(cellText=summary.round(2).values,
                            colLabels=summary.columns,
                            loc="center")
            tbl.auto_set_font_size(False)
            tbl.set_fontsize(8)
            tbl.scale(1.0, 1.3)
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

    print(f"Saved report: {pdf_path}")
    print(f"PNGs in: {out_dir}")
    if args.write_summary:
        print(f"Summary CSV: {out_dir / 'summary_stats.csv'}")

if __name__ == "__main__":
    main()

