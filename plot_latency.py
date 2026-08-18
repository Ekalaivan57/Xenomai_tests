#!/usr/bin/env python3
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

CSV_FILE = "latency_data.csv"
OUTPUT_IMG = "latency_plot.png"

def load_data(filepath):
    if not os.path.exists(filepath):
        print(f"[-] Error: '{filepath}' not found.")
        print("[-] Please run './latency_test' first to generate benchmark data.")
        sys.exit(1)
    
    df = pd.read_csv(filepath)
    if df.empty:
        print(f"[-] Error: '{filepath}' is empty.")
        sys.exit(1)
    return df

def print_stats(df):
    jitter = df['jitter_us']
    period = df['period_us']
    exec_time = df['exec_us']
    overruns = df['overruns'].sum()

    print("\n" + "="*65)
    print("           XENOMAI REAL-TIME LATENCY ANALYSIS REPORT")
    print("="*65)
    print(f" Total Samples Analyzed   : {len(df):,} cycles")
    print(f" Total Overruns Detected  : {overruns}")
    print("-"*65)
    print(" WAKE-UP JITTER (us):")
    print(f"   Min Jitter             : {jitter.min():10.3f} us")
    print(f"   Avg Jitter             : {jitter.mean():10.3f} us")
    print(f"   Median (50th %ile)     : {jitter.median():10.3f} us")
    print(f"   95th Percentile        : {jitter.quantile(0.95):10.3f} us")
    print(f"   99th Percentile        : {jitter.quantile(0.99):10.3f} us")
    print(f"   99.9th Percentile      : {jitter.quantile(0.999):10.3f} us")
    print(f"   Max Jitter (Worst-case): {jitter.max():10.3f} us")
    print(f"   Standard Deviation     : {jitter.std():10.3f} us")
    print("-"*65)
    print(" MEASURED CYCLE PERIOD (us):")
    print(f"   Min Period             : {period.min():10.3f} us")
    print(f"   Avg Period             : {period.mean():10.3f} us")
    print(f"   Max Period             : {period.max():10.3f} us")
    print(f"   Period Std Deviation   : {period.std():10.3f} us")
    print("-"*65)
    print(" EXECUTION DURATION (us):")
    print(f"   Avg Execution Time     : {exec_time.mean():10.3f} us")
    print(f"   Max Execution Time     : {exec_time.max():10.3f} us")
    print("="*65 + "\n")

def plot_data(df):
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=False)
    fig.suptitle('Xenomai Hard Real-Time Latency & Jitter Benchmark', fontsize=15, fontweight='bold')

    jitter = df['jitter_us']
    period = df['period_us']
    samples = df['sample_idx']

    # 1. Wake-up Jitter vs Time
    ax1 = axes[0]
    ax1.plot(samples, jitter, color='#1f77b4', linewidth=0.8, alpha=0.85, label='Jitter')
    ax1.axhline(jitter.mean(), color='red', linestyle='--', linewidth=1.5, label=f'Avg Jitter ({jitter.mean():.2f} us)')
    ax1.axhline(jitter.max(), color='purple', linestyle=':', linewidth=1.5, label=f'Max Jitter ({jitter.max():.2f} us)')
    ax1.set_ylabel('Wake-up Jitter (µs)', fontsize=11, fontweight='semibold')
    ax1.set_title('Wake-up Scheduling Jitter over Cycles', fontsize=12)
    ax1.legend(loc='upper right', frameon=True)
    ax1.grid(True, linestyle='--', alpha=0.6)

    # 2. Jitter Distribution Histogram
    ax2 = axes[1]
    n, bins, patches = ax2.hist(jitter, bins=80, color='#2ca02c', edgecolor='black', alpha=0.75, density=True)
    ax2.axvline(jitter.mean(), color='red', linestyle='--', linewidth=1.5, label=f'Mean: {jitter.mean():.2f} us')
    ax2.axvline(jitter.quantile(0.99), color='orange', linestyle='--', linewidth=1.5, label=f'99th %: {jitter.quantile(0.99):.2f} us')
    ax2.axvline(jitter.max(), color='purple', linestyle=':', linewidth=1.5, label=f'Max: {jitter.max():.2f} us')
    ax2.set_xlabel('Jitter (µs)', fontsize=11, fontweight='semibold')
    ax2.set_ylabel('Probability Density', fontsize=11, fontweight='semibold')
    ax2.set_title('Jitter Probability Distribution (Histogram)', fontsize=12)
    ax2.legend(loc='upper right', frameon=True)
    ax2.grid(True, linestyle='--', alpha=0.6)

    # 3. Measured Period vs Expected
    ax3 = axes[2]
    expected_period = period.median()
    ax3.plot(samples, period, color='#ff7f0e', linewidth=0.8, alpha=0.85, label='Measured Period')
    ax3.axhline(expected_period, color='black', linestyle='--', linewidth=1.5, label=f'Nominal Period ({expected_period:.1f} us)')
    ax3.set_xlabel('Cycle Index (Sample #)', fontsize=11, fontweight='semibold')
    ax3.set_ylabel('Period (µs)', fontsize=11, fontweight='semibold')
    ax3.set_title('Loop Cycle Period Stability', fontsize=12)
    ax3.legend(loc='upper right', frameon=True)
    ax3.grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()
    plt.savefig(OUTPUT_IMG, dpi=200)
    print(f"[+] Saved visualization plot to '{OUTPUT_IMG}'")

    # If in interactive GUI environment, display window
    if os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
        try:
            plt.show()
        except Exception:
            pass

if __name__ == '__main__':
    csv_path = sys.argv[1] if len(sys.argv) > 1 else CSV_FILE
    df = load_data(csv_path)
    print_stats(df)
    plot_data(df)
