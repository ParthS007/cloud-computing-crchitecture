import matplotlib.pyplot as plt
import mcPerfLogs
import os
import numpy as np
import csv
from collections import defaultdict
import sys


COLORS = ["tab:blue", "tab:orange"]


def read_cpu_usage(file_path: str, cores: list[int]):
    """Read CPU usage data from CSV file and return as a list of (timestamp, cpu_percentages) tuples."""
    cpu_data = []
    with open(file_path, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:  # Skip empty lines
                continue
            try:
                timestamp = int(row[0])
                # Parse the CPU percentages from individual columns
                cpu_percentages = []
                for val in row[1:-1]:  # Skip timestamp and last column
                    # Remove any spaces and convert to float
                    cleaned_val = val.strip(" []")
                    if cleaned_val:  # Only add non-empty values
                        cpu_percentages.append(float(cleaned_val))
                percentages_to_sum = [cpu_percentages[core] for core in cores]
                total_cpu = sum(percentages_to_sum)
                cpu_data.append((timestamp, total_cpu))
            except (ValueError, IndexError):
                continue
    return cpu_data


def calculate_avg_cpu_usage(cpu_data, start_time, end_time):
    """Calculate average CPU usage between start_time and end_time."""
    # Get lengths of timestamps
    start_len = len(str(start_time))
    end_len = len(str(end_time))

    # Find the shortest length to normalize to
    relevant_data = []
    for ts, cpu in cpu_data:
        ts_len = len(str(ts))
        min_len = min(start_len, end_len, ts_len)

        # Normalize all timestamps by removing extra digits
        normalized_ts = int(str(ts)[:min_len])
        normalized_start = int(str(start_time)[:min_len])
        normalized_end = int(str(end_time)[:min_len])

        if normalized_start <= normalized_ts < normalized_end:
            relevant_data.append(cpu)

    if not relevant_data:
        return 0
    return sum(relevant_data) / len(relevant_data)


def aggregate_qps_data(qps_data, latency_data, cpu_data, window_size):
    """Aggregate data points where QPS values are within a specified window size."""
    # Sort all data by QPS
    combined_data = list(zip(qps_data, latency_data, cpu_data))
    combined_data.sort(key=lambda x: x[0])

    aggregated_qps = []
    aggregated_latency = []
    aggregated_cpu = []

    current_window = []
    current_qps = None

    for qps, latency, cpu in combined_data:
        if current_qps is None or abs(qps - current_qps) <= window_size:
            current_window.append((qps, latency, cpu))
            current_qps = qps
        else:
            # Calculate averages for the current window
            avg_qps = np.mean([x[0] for x in current_window])
            avg_latency = np.mean([x[1] for x in current_window])
            avg_cpu = np.mean([x[2] for x in current_window])

            aggregated_qps.append(avg_qps)
            aggregated_latency.append(avg_latency)
            aggregated_cpu.append(avg_cpu)

            # Start new window
            current_window = [(qps, latency, cpu)]
            current_qps = qps

    # Process the last window
    if current_window:
        avg_qps = np.mean([x[0] for x in current_window])
        avg_latency = np.mean([x[1] for x in current_window])
        avg_cpu = np.mean([x[2] for x in current_window])

        aggregated_qps.append(avg_qps)
        aggregated_latency.append(avg_latency)
        aggregated_cpu.append(avg_cpu)

    return aggregated_qps, aggregated_latency, aggregated_cpu


def main(window_size: int):
    # Define the configurations
    configs = {
        "experiment1Core2Threads": {"T": 2, "C": 1, "label": "2 Threads, 1 Core"},
        "experiment2Cores2Threads": {"T": 2, "C": 2, "label": "2 Threads, 2 Cores"},
    }

    # Create a figure with two subplots
    fig, axs = plt.subplots(1, 2, figsize=(16, 8))

    # Colors for each configuration
    colors = ["blue", "red"]

    # Process each configuration
    for i, (exp_name, config) in enumerate(configs.items()):
        # Dictionary to store data points for each target QPS
        qps_data = defaultdict(list)
        latency_data = defaultdict(list)
        cpu_data = defaultdict(list)

        # Process each run
        for run in range(3):
            # Read mcperf logs
            log_file = os.path.join(
                os.path.dirname(__file__), f"4_1_d_logs", f"{exp_name}_run{run}.txt"
            )
            mcperf_log = mcPerfLogs.McPerfLogs(log_file)
            data = mcperf_log.parse_log_file()

            # Read CPU usage data
            cpu_file = os.path.join(
                os.path.dirname(__file__),
                f"4_1_d_logs",
                f"cpuUsage{exp_name.replace('experiment', '')}_run{run}.csv",
            )
            cores = [0] if config["C"] == 1 else [0, 1]
            cpu_usage_data = read_cpu_usage(cpu_file, cores)

            # Sort data by target QPS to maintain order
            data.sort(key=lambda x: x["target"])

            # Extract QPS, p95 latency, and CPU usage for each data point
            for point in data:
                qps = point["qps"]
                p95_latency = point["p95"]
                target = point["target"]
                ts_start = point.get("ts_start", 0)
                ts_end = point.get("ts_end", 0)

                # Calculate average CPU usage for this test period
                avg_cpu = calculate_avg_cpu_usage(cpu_usage_data, ts_start, ts_end)

                qps_data[target].append(qps)
                latency_data[target].append(p95_latency)
                cpu_data[target].append(avg_cpu)

        # Calculate average QPS, latency, and CPU usage for each target QPS
        avg_qps = []
        avg_latency = []
        std_latency = []
        avg_cpu_usage = []
        std_cpu_usage = []

        for target in sorted(qps_data.keys()):
            avg_qps.append(np.mean(qps_data[target]))
            avg_latency.append(np.mean(latency_data[target]))
            avg_cpu_usage.append(np.mean(cpu_data[target]))

        # Aggregate data points within 5k QPS windows
        avg_qps, avg_latency, avg_cpu_usage = aggregate_qps_data(
            avg_qps, avg_latency, avg_cpu_usage, window_size
        )

        # Create the primary y-axis for latency
        ax1 = axs[i]

        # Create the secondary y-axis for CPU usage
        ax2 = ax1.twinx()

        # Create bar plot for CPU usage first (behind)
        ax2.errorbar(
            avg_qps,
            avg_cpu_usage,
            label="CPU Usage",
            color=COLORS[1],
            linestyle="-",
            linewidth=2,
            solid_capstyle="round",
            capsize=3,
            capthick=1,
            elinewidth=1,
            zorder=1,
        )

        # Create the latency plot on top
        ax1.errorbar(
            avg_qps,
            avg_latency,
            label="Latency",
            color=COLORS[0],
            marker="o",
            linestyle="-",
            linewidth=2,
            markersize=5,
            capsize=3,
            capthick=1,
            elinewidth=1,
            zorder=2,
        )

        # Set labels and title for each subplot
        ax1.set_xlabel("Achieved QPS", fontsize=12)
        ax1.set_ylabel("95th Percentile Latency (μs)", fontsize=12, color=COLORS[0])
        ax2.set_ylabel("Average CPU Usage (%)", fontsize=12, color=COLORS[1])
        axs[i].set_title(f'Memcached Performance: {config["label"]}', fontsize=14)

        # Set x-axis limits from 0 to 230000
        ax1.set_xlim(0, 230000)

        # Add horizontal line at 800ms
        ax1.axhline(y=800, color="gray", linestyle="--", alpha=0.5, label="0.8ms SLO")

        # Add grid with appropriate alpha for log scale
        ax1.grid(True, linestyle="--", alpha=0.4, which="both")

        # Add legends
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=10, loc="upper left")

        # Add some padding to the axes
        ax1.margins(x=0.02)

    # Add note about number of runs
    fig.text(
        0.5,
        0.01,
        "Note: Data averaged across 3 runs with error bars showing standard deviation",
        ha="center",
        fontsize=10,
        style="italic",
    )

    # Adjust layout
    plt.tight_layout(rect=[0, 0.03, 1, 1])

    # Save the figure with high DPI
    plt.savefig("memcached_performance_with_cpu.png", dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    # check if w is in the args and take next arg as window size
    args = sys.argv[1:]
    window_size = 1
    if "-w" in args:
        window_size = int(args[args.index("-w") + 1])

    print(f"Window size: {window_size}")
    main(window_size)
