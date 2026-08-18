#!/usr/bin/env python3
"""
Plot Xenomai `latency` tool output (RTD lines) as a detailed time-series graph.

Usage:
    python3 xenomai_latency_plot.py xenomai_latency_log.txt

Requires:
    pip install matplotlib numpy
"""

import re
import sys
import matplotlib.pyplot as plt
import numpy as np

if len(sys.argv) != 2:
    print("Usage: python3 xenomai_latency_plot.py <xenomai_latency_log_file>")
    sys.exit(1)

path = sys.argv[1]

with open(path, "r") as f:
    lines = f.readlines()

# Parse RTD lines:
# RTD|   lat_min|   lat_avg|   lat_max| overrun| msw|  best|  worst
rtd_pattern = re.compile(
    r"^RTD\|\s*([\d.]+)\|\s*([\d.]+)\|\s*([\d.]+)\|\s*(\d+)\|\s*(\d+)\|\s*([\d.]+)\|\s*([\d.]+)"
)

samples = []
for line in lines:
    m = rtd_pattern.match(line)
    if m:
        lat_min, lat_avg, lat_max, overrun, msw, best, worst = m.groups()
        samples.append({
            "min": float(lat_min),
            "avg": float(lat_avg),
            "max": float(lat_max),
            "overrun": int(overrun),
            "msw": int(msw),
            "best": float(best),
            "worst": float(worst),
        })

# Parse final RTS summary line
rts_pattern = re.compile(
    r"^RTS\|\s*([\d.]+)\|\s*([\d.]+)\|\s*([\d.]+)\|\s*(\d+)\|\s*(\d+)\|\s*([\d:/]+)"
)
final_summary = None
for line in lines:
    m = rts_pattern.match(line)
    if m:
        final_summary = m.groups()

if not samples:
    print("No RTD samples found. Check the log file format.")
    sys.exit(1)

n = len(samples)
time_idx = np.arange(n)  # each RTD line is one sample interval (~1s apart typically)

lat_min = np.array([s["min"] for s in samples])
lat_avg = np.array([s["avg"] for s in samples])
lat_max = np.array([s["max"] for s in samples])
overruns = np.array([s["overrun"] for s in samples])
running_worst = np.array([s["worst"] for s in samples])

print(f"Total samples: {n}")
print(f"Overall min latency: {lat_min.min():.3f} us")
print(f"Overall avg latency: {lat_avg.mean():.3f} us")
print(f"Overall max latency: {lat_max.max():.3f} us")
print(f"Total overruns: {overruns.sum()}")
if final_summary:
    print(f"Final RTS summary -> min:{final_summary[0]} avg:{final_summary[1]} "
          f"max:{final_summary[2]} overrun:{final_summary[3]} msw:{final_summary[4]} "
          f"runtime:{final_summary[5]}")

# --- Single combined detailed plot ---
fig, ax1 = plt.subplots(figsize=(13, 6.5))

ax1.plot(time_idx, lat_max, color="#e53e3e", linewidth=1.2, label="Max latency (per interval)")
ax1.plot(time_idx, lat_avg, color="#2b6cb0", linewidth=1.5, label="Avg latency (per interval)")
ax1.plot(time_idx, lat_min, color="#48bb78", linewidth=1.0, label="Min latency (per interval)")
ax1.plot(time_idx, running_worst, color="black", linewidth=1.2, linestyle="--",
          label="Running worst-case (cumulative)")

ax1.fill_between(time_idx, lat_min, lat_max, color="#2b6cb0", alpha=0.08)

ax1.set_xlabel("Sample interval (~1s each)")
ax1.set_ylabel("Latency (microseconds)")
ax1.set_title("Xenomai Cobalt RT Latency Over Time (min / avg / max / worst-case)")
ax1.grid(True, alpha=0.3)
ax1.legend(loc="upper left")

# Mark overrun points if any occurred
overrun_idx = np.where(overruns > 0)[0]
if len(overrun_idx) > 0:
    ax1.scatter(overrun_idx, lat_max[overrun_idx], color="purple", marker="x",
                s=80, label="Overrun occurred", zorder=5)
    ax1.legend(loc="upper left")

# Annotate final worst-case value
ax1.axhline(lat_max.max(), color="gray", linestyle=":", linewidth=1)
ax1.text(n * 0.98, lat_max.max(), f" worst={lat_max.max():.1f}us",
          va="bottom", ha="right", fontsize=9, color="gray")

plt.tight_layout()
plt.show()
