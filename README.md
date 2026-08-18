# Xenomai Hard Real-Time 1ms Latency Benchmark

This package provides a standalone benchmark tool to measure the wake-up latency, scheduling jitter, cycle period consistency, and overrun detection for Xenomai real-time threads running at 1ms (1000 µs / 1 kHz).

---

## Files

- **`latency_test.c`**: Real-time C program using the Xenomai Alchemy API. Records high-resolution timestamps in pre-allocated RAM to avoid mode switches, and exports cycle-by-cycle metrics to CSV.
- **`Makefile`**: Compilation rules using `xeno-config`.
- **`plot_latency.py`**: Python script to compute statistical distributions (min, max, avg, 99th percentile, standard deviation) and plot the latency graph.

---

## 1. How to Build

Compile the benchmark binary:
```bash
cd /home/erl/Documents/Ekalaivan/xenomai_test
make
```

---

## 2. How to Run the Latency Test

Run with root permissions (required by `mlockall` and Xenomai RT priority):
```bash
sudo ./latency_test
```

### Optional Command-Line Arguments:
```bash
sudo ./latency_test [TOTAL_CYCLES] [PERIOD_IN_MICROSECONDS]
```

Examples:
* Run for **10,000 cycles** (10 seconds) at **1 ms (1000 µs)** (Default):
  ```bash
  sudo ./latency_test 10000 1000
  ```
* Run for **60,000 cycles** (1 minute) at **1 ms (1000 µs)**:
  ```bash
  sudo ./latency_test 60000 1000
  ```
* Run at **500 µs (2 kHz)** for 20,000 cycles:
  ```bash
  sudo ./latency_test 20000 500
  ```

> **Note**: You can press `Ctrl + C` at any point to stop the test early. The program will catch the signal, compute statistics on the samples collected so far, and save them to `latency_data.csv`.

---

## 3. How to View and Plot the Data

Run the Python visualizer:
```bash
python3 plot_latency.py
```

This will:
1. Print a full statistical summary table in the terminal.
2. Generate an interactive 3-panel plot:
   - **Wake-up Jitter vs Cycles** (shows worst-case spikes).
   - **Jitter Probability Distribution Histogram**.
   - **Cycle Period Stability** (vs nominal 1.000 ms line).
3. Save the image to `latency_plot.png`.
