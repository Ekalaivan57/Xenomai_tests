#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <sys/mman.h>
#include <math.h>

#include <alchemy/task.h>
#include <alchemy/timer.h>

/* ================= CONFIGURATION DEFAULTS ================= */
#define DEFAULT_SAMPLES     10000       /* 10,000 cycles = 10s at 1ms */
#define DEFAULT_PERIOD_US   1000        /* 1 ms = 1000 us */
#define MAX_SAMPLES         1000000     /* Max buffer allocation */
#define CSV_FILENAME        "latency_data.csv"

/* ================= DATA STRUCTURES ================= */
typedef struct {
    uint64_t expected_ns;   /* Expected wake-up timestamp (ns) */
    uint64_t actual_ns;     /* Actual wake-up timestamp (ns) */
    int64_t  jitter_ns;     /* Wake-up jitter (actual - expected) in ns */
    uint64_t period_ns;     /* Measured period between cycles in ns */
    uint64_t exec_ns;       /* Payload execution duration in ns */
    unsigned long overruns; /* Overrun count from rt_task_wait_period */
} LatencyRecord;

/* ================= GLOBAL STATE ================= */
static LatencyRecord *records = NULL;
static int total_samples = DEFAULT_SAMPLES;
static uint64_t period_ns = DEFAULT_PERIOD_US * 1000ULL;
static volatile sig_atomic_t keep_running = 1;
static int collected_samples = 0;

static RT_TASK benchmark_task;

/* ================= SIGNAL HANDLER ================= */
static void sig_handler(int sig)
{
    (void)sig;
    keep_running = 0;
}

/* ================= REAL-TIME BENCHMARK TASK ================= */
static void latency_rt_task(void *arg)
{
    (void)arg;

    /* Start the periodic timer 10ms from now to allow setup */
    RTIME start_time = rt_timer_read() + 10000000ULL;
    int err = rt_task_set_periodic(NULL, start_time, period_ns);
    if (err) {
        fprintf(stderr, "Error: rt_task_set_periodic failed: %d\n", err);
        return;
    }

    RTIME expected_time = start_time;
    RTIME prev_actual = start_time;

    for (int i = 0; i < total_samples && keep_running; i++) {
        unsigned long overruns = 0;

        /* Wait for next periodic cycle */
        err = rt_task_wait_period(&overruns);
        RTIME actual_time = rt_timer_read();

        /* If you have any dummy real-time work/computation, it runs here */
        volatile double dummy = sin(0.001 * i);
        (void)dummy;

        RTIME work_end = rt_timer_read();

        /* Calculate timing metrics (nanoseconds) */
        int64_t jitter = (int64_t)actual_time - (int64_t)expected_time;
        uint64_t cycle_period = (i == 0) ? period_ns : (actual_time - prev_actual);
        uint64_t exec_time = work_end - actual_time;

        /* Zero-overhead in-RAM logging (No printf, No file I/O during RT loop) */
        records[i].expected_ns = expected_time;
        records[i].actual_ns   = actual_time;
        records[i].jitter_ns   = jitter;
        records[i].period_ns   = cycle_period;
        records[i].exec_ns     = exec_time;
        records[i].overruns    = overruns;

        collected_samples++;
        prev_actual = actual_time;

        /* Advance expected target time; account for any missed overruns */
        expected_time += period_ns * (1 + overruns);
    }
}

/* ================= EXPORT CSV & PRINT SUMMARY ================= */
static void save_csv_and_print_summary(const char *filename)
{
    if (collected_samples == 0) {
        printf("No samples were collected.\n");
        return;
    }

    printf("\nSaving %d samples to %s ...\n", collected_samples, filename);

    FILE *f = fopen(filename, "w");
    if (!f) {
        perror("Failed to open output CSV file");
        return;
    }

    /* Write CSV Header */
    fprintf(f, "sample_idx,expected_ns,actual_ns,jitter_us,period_us,exec_us,overruns\n");

    double min_jitter = 1e9;
    double max_jitter = -1e9;
    double sum_jitter = 0.0;
    double sum_sq_jitter = 0.0;

    double min_period = 1e9;
    double max_period = -1e9;
    double sum_period = 0.0;

    unsigned long total_overruns = 0;

    for (int i = 0; i < collected_samples; i++) {
        double jitter_us = records[i].jitter_ns / 1000.0;
        double period_us = records[i].period_ns / 1000.0;
        double exec_us   = records[i].exec_ns   / 1000.0;

        fprintf(f, "%d,%lu,%lu,%.3f,%.3f,%.3f,%lu\n",
                i,
                (unsigned long)records[i].expected_ns,
                (unsigned long)records[i].actual_ns,
                jitter_us,
                period_us,
                exec_us,
                records[i].overruns);

        /* Statistics aggregation */
        if (jitter_us < min_jitter) min_jitter = jitter_us;
        if (jitter_us > max_jitter) max_jitter = jitter_us;
        sum_jitter += jitter_us;
        sum_sq_jitter += (jitter_us * jitter_us);

        if (period_us < min_period) min_period = period_us;
        if (period_us > max_period) max_period = period_us;
        sum_period += period_us;

        total_overruns += records[i].overruns;
    }

    fclose(f);
    printf("Successfully written to %s\n", filename);

    double avg_jitter = sum_jitter / collected_samples;
    double variance = (sum_sq_jitter / collected_samples) - (avg_jitter * avg_jitter);
    double stddev_jitter = (variance > 0.0) ? sqrt(variance) : 0.0;

    double avg_period = sum_period / collected_samples;

    /* Print Summary Report */
    printf("\n=================================================================\n");
    printf("                   XENOMAI LATENCY BENCHMARK REPORT              \n");
    printf("=================================================================\n");
    printf("  Configured Period       : %lu us (%.2f ms / %.1f Hz)\n",
           (unsigned long)(period_ns / 1000ULL),
           (double)(period_ns / 1000000.0),
           1e9 / (double)period_ns);
    printf("  Total Samples Recorded  : %d cycles\n", collected_samples);
    printf("  Total Overruns Detected : %lu\n", total_overruns);
    printf("-----------------------------------------------------------------\n");
    printf("  WAKE-UP JITTER (Latency):\n");
    printf("    Minimum Jitter        : %8.3f us\n", min_jitter);
    printf("    Average Jitter        : %8.3f us\n", avg_jitter);
    printf("    Maximum Jitter (Worst): %8.3f us\n", max_jitter);
    printf("    Std. Deviation        : %8.3f us\n", stddev_jitter);
    printf("-----------------------------------------------------------------\n");
    printf("  MEASURED CYCLE PERIOD:\n");
    printf("    Minimum Period        : %8.3f us\n", min_period);
    printf("    Average Period        : %8.3f us\n", avg_period);
    printf("    Maximum Period        : %8.3f us\n", max_period);
    printf("=================================================================\n\n");
}

/* ================= MAIN FUNCTION ================= */
int main(int argc, char *argv[])
{
    /* Parse command line arguments */
    if (argc >= 2) {
        total_samples = atoi(argv[1]);
        if (total_samples <= 0 || total_samples > MAX_SAMPLES) {
            fprintf(stderr, "Invalid sample count. Range: [1 - %d]\n", MAX_SAMPLES);
            return 1;
        }
    }
    if (argc >= 3) {
        int period_us = atoi(argv[2]);
        if (period_us <= 0) {
            fprintf(stderr, "Invalid period. Must be > 0 us\n");
            return 1;
        }
        period_ns = (uint64_t)period_us * 1000ULL;
    }

    printf("====================================================\n");
    printf(" Starting Xenomai Hard Real-Time Latency Benchmark  \n");
    printf(" Target Samples : %d cycles\n", total_samples);
    printf(" Target Period  : %lu us (%.2f ms)\n",
           (unsigned long)(period_ns / 1000ULL),
           (double)(period_ns / 1000000.0));
    printf(" Press Ctrl+C at any time to stop and export data.  \n");
    printf("====================================================\n");

    /* Register signal handlers */
    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);

    /* Lock all current and future memory to prevent paging / page faults */
    if (mlockall(MCL_CURRENT | MCL_FUTURE) != 0) {
        perror("mlockall failed (run with sudo/root permissions)");
        return 1;
    }

    /* Allocate in-RAM record buffer */
    records = (LatencyRecord *)calloc(total_samples, sizeof(LatencyRecord));
    if (!records) {
        fprintf(stderr, "Failed to allocate memory for %d records\n", total_samples);
        return 1;
    }

    /* Create Xenomai Real-Time task with priority 99 (highest RT priority) */
    int ret = rt_task_create(&benchmark_task, "latency_bench", 0, 99, 0);
    if (ret != 0) {
        fprintf(stderr, "Failed to create Xenomai task (error: %d: %s)\n",
                ret, strerror(-ret));
        free(records);
        return 1;
    }

    /* Start the RT benchmark task */
    ret = rt_task_start(&benchmark_task, &latency_rt_task, NULL);
    if (ret != 0) {
        fprintf(stderr, "Failed to start Xenomai task (error: %d: %s)\n",
                ret, strerror(-ret));
        rt_task_delete(&benchmark_task);
        free(records);
        return 1;
    }

    /* Wait for completion or interrupt */
    while (keep_running && (collected_samples < total_samples)) {
        usleep(50000); /* 50ms check interval */
    }

    /* Stop task */
    rt_task_delete(&benchmark_task);

    /* Save CSV and print comprehensive statistics */
    save_csv_and_print_summary(CSV_FILENAME);

    /* Clean up */
    free(records);
    return 0;
}
