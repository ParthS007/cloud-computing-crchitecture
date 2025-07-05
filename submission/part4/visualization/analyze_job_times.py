import os
import csv
import statistics
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd
import numpy as np

# Define colors for different workloads - using matplotlib's default color cycle for consistency
WORKLOADS = ["ferret", "dedup", "canneal", "freqmine", "blackscholes", "radix", "vips"]
# Define custom colors for each workload
WORKLOAD_COLORS = {
    "blackscholes": "#CCA000",  # Gold/amber
    "canneal": "#CCCCAA",  # Light beige
    "dedup": "#CCACCA",  # Light lavender
    "ferret": "#AACCCA",  # Light sage
    "freqmine": "#0CCA00",  # Bright green
    "radix": "#00CCA0",  # Teal
    "vips": "#CC0A00",  # Bright red
}

DURATION_MARGIN = 60

def ensure_directory_exists(directory_path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Created directory: {directory_path}")

def parse_mcperf_data(file_path):
    """Parse mcperf data into a pandas DataFrame."""
    data = []

    with open(file_path, mode='r') as file:
        # Get QPS and their timestamps
        file.readline()
        interval_line = file.readline().strip()
        interval_string = interval_line.split("=")[1].strip().split(" ", 1)
        
        number_of_intervals = int(interval_string[0])

        file.readline()
        timestamp_start_ms = int(file.readline().split(":")[1].strip())
        timestamp_end_ms = int(file.readline().split(":")[1].strip())
        timestamp_delta_ms = (timestamp_end_ms - timestamp_start_ms) / number_of_intervals

        file.readline()
        file.readline()
        for i in range(number_of_intervals):
            line = file.readline().strip().split()
            latency_95th = float(line[-6])
            qps = float(line[-2])

            data.append(
                {
                    "timestamp_ms": timestamp_start_ms + i * timestamp_delta_ms,
                    "p95_us": latency_95th, # Store original microseconds
                    "p95_ms": latency_95th / 1000, # Convert to milliseconds
                    "qps": qps,
                }
            )

        return pd.DataFrame(data)
    
def process_execution_intervals(file_path):
    # Are the jobs running or not
    blackscholes_is_running = False
    canneal_is_running = False
    dedup_is_running = False
    ferret_is_running = False
    freqmine_is_running = False
    radix_is_running = False
    vips_is_running = False

    job_events = []
    earliest_start_ms = None

    df = pd.read_csv(file_path)
    for index, row in df.iterrows():
        job_name = row["job_name"].strip()
        timestamp = int(row["timestamp"]) * 1000
        status = row["status"].strip()

        if earliest_start_ms is None or timestamp < earliest_start_ms:
            earliest_start_ms = timestamp

        if job_name == "blackscholes":
            if status == "RUNNING" and not blackscholes_is_running:
                blackscholes_is_running = True
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "blackscholes",
                        "event": "START",
                        "node": None,
                    }
                )
            elif (status == "PAUSED" or status == "COMPLETED") and blackscholes_is_running:
                blackscholes_is_running = False
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "blackscholes",
                        "event": "END",
                        "node": None,
                    }
                )
        elif job_name == "canneal":
            if status == "RUNNING" and not canneal_is_running:
                canneal_is_running = True
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "canneal",
                        "event": "START",
                        "node": None,
                    }
                )
            elif (status == "PAUSED" or status == "COMPLETED") and canneal_is_running:
                canneal_is_running = False
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "canneal",
                        "event": "END",
                        "node": None,
                    }
                )
        elif job_name == "dedup":
            if status == "RUNNING" and not dedup_is_running:
                dedup_is_running = True
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "dedup",
                        "event": "START",
                        "node": None,
                    }
                )
            elif (status == "PAUSED" or status == "COMPLETED") and dedup_is_running:
                dedup_is_running = False
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "dedup",
                        "event": "END",
                        "node": None,
                    }
                )
        elif job_name == "ferret":
            if status == "RUNNING" and not ferret_is_running:
                ferret_is_running = True
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "ferret",
                        "event": "START",
                        "node": None,
                    }
                )
            elif (status == "PAUSED" or status == "COMPLETED") and ferret_is_running:
                ferret_is_running = False
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "ferret",
                        "event": "END",
                        "node": None,
                    }
                )
        elif job_name == "freqmine":
            if status == "RUNNING" and not freqmine_is_running:
                freqmine_is_running = True
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "freqmine",
                        "event": "START",
                        "node": None,
                    }
                )
            elif (status == "PAUSED" or status == "COMPLETED") and freqmine_is_running:
                freqmine_is_running = False
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "freqmine",
                        "event": "END",
                        "node": None,
                    }
                )
        elif job_name == "radix":
            if status == "RUNNING" and not radix_is_running:
                radix_is_running = True
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "radix",
                        "event": "START",
                        "node": None,
                    }
                )
            elif (status == "PAUSED" or status == "COMPLETED") and radix_is_running:
                radix_is_running = False
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "radix",
                        "event": "END",
                        "node": None,
                    }
                )
        elif job_name == "vips":
            if status == "RUNNING" and not vips_is_running:
                vips_is_running = True
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "vips",
                        "event": "START",
                        "node": None,
                    }
                )
            elif (status == "PAUSED" or status == "COMPLETED") and vips_is_running:
                vips_is_running = False
                job_events.append(
                    {
                        "timestamp_ms": timestamp,
                        "process_name": "vips",
                        "event": "END",
                        "node": None,
                    }
                )

    events_df = pd.DataFrame(job_events)
    return events_df, earliest_start_ms

def process_cpu_usage_of_memcached(file_path):
    df = pd.read_csv(file_path)

    memcached_cpu_usage = []
    for index, row in df.iterrows():
        timestamp_ms = int(row["timestamp"]) * 1000
        cpu_usage = int(row["memcached_cores_usage"])
        memcached_cpu_usage.append(
            {
                "timestamp_ms": timestamp_ms,
                "memcached_cores_usage": cpu_usage,
            }
        )
    return pd.DataFrame(memcached_cpu_usage)

def create_plots_A(input_directory_path, policy_number, run_number, save_folder_path):
    mcperf_file = os.path.join(input_directory_path, f"mcperf_policy{policy_number}_run{run_number}.log")
    scheduler_file = os.path.join(input_directory_path, f"job_times/job_start_end_times/job_times_policy{policy_number}_run{run_number}.csv")
    
    if not os.path.exists(mcperf_file) or not os.path.exists(scheduler_file):
        print(f"Missing files for run {run_number}. Skipping.")
        return

    # Parse data into DataFrames
    mcperf_df = parse_mcperf_data(mcperf_file)
    events_df, earliest_start_ms = process_execution_intervals(scheduler_file)

    if mcperf_df.empty or events_df.empty:
        print(f"No data found for run {run_number}. Skipping.")
        return

    # Print some debug info
    print(
        f"Run {run_number}: Found {len(mcperf_df)} mcperf data points"
    )

    # Convert timestamps to seconds relative to first job start
    mcperf_df["timestamp"] = (mcperf_df["timestamp_ms"] - earliest_start_ms) / 1000
    events_df["timestamp"] = (events_df["timestamp_ms"] - earliest_start_ms) / 1000

    # Filter to include only data after the first job start (with a margin for visibility)
    mcperf_df = mcperf_df[
        mcperf_df["timestamp"] >= 0
    ]  # Only include data from job start

    # Get list of unique workloads for the events plot
    workloads = events_df["process_name"].unique()

    # Calculate experiment duration
    if not events_df.empty:
        duration = max(events_df["timestamp"]) + 20  # Add margin at end
    else:
        duration = max(mcperf_df["timestamp"]) + 20

    # Create the figure with two subplots
    fig = plt.figure(figsize=(10, 6))
    # Create subplots with specific height ratios
    axA_95p, ax_events = fig.subplots(2, 1, gridspec_kw={"height_ratios": [3, 1.5]})

    # Upper subplot: P95 latency and QPS
    axA_95p.set_title(f"{run_number}A")
    axA_95p.set_xlim([0, duration + DURATION_MARGIN])
    axA_95p.set_xlabel("Time [s]")
    axA_95p.set_xticks(np.arange(0, duration + DURATION_MARGIN, 50))
    axA_95p.grid(True, alpha=0.3)
    axA_95p.set_ylabel("95th Percentile Latency [ms]")
    axA_95p.tick_params(axis="y", labelcolor="tab:blue")

    # Set y-axis limits and ticks for latency
    max_latency = max(3.2, mcperf_df["p95_ms"].max() * 1.1)
    axA_95p.set_ylim([0, max_latency])
    axA_95p.set_yticks(np.arange(0, max_latency + 0.1, 0.4))

    # Plot P95 latency line
    (artistA_95p,) = axA_95p.plot(
        mcperf_df["timestamp"],
        mcperf_df["p95_ms"],
        color="tab:blue",
        label="95 percentile latency",
    )

    # Add SLO threshold line (0.8ms)
    slo_line = axA_95p.axhline(y=0.8, color="red", linestyle="-", linewidth=1.5, label="SLO (0.8ms)")

    # Add QPS on secondary y-axis
    axA_QPS = axA_95p.twinx()
    axA_QPS.set_ylabel("Queries per second")

    # Scale QPS axis appropriately
    max_qps = max(40000, mcperf_df["qps"].max() * 1.1)
    axA_QPS.set_ylim([0, max_qps])
    axA_QPS.set_yticks(np.arange(0, max_qps + 1, 10000))
    axA_QPS.yaxis.set_major_formatter(
        FuncFormatter(lambda x_val, tick_pos: "{:.0f}k".format(x_val / 1000))
    )
    axA_QPS.tick_params(axis="y", labelcolor="tab:orange")
    axA_QPS.grid(False)

    (artistA_QPS,) = axA_QPS.plot(
        mcperf_df["timestamp"], mcperf_df["qps"], color="tab:orange", label="QPS"
    )

    # Add legend with SLO line included
    axA_QPS.legend(
        [artistA_QPS, artistA_95p, slo_line],
        ["QPS", "95 percentile latency", "SLO (0.8ms)"],
        loc="upper right",
    )

    # Lower subplot: Job timeline
    ax_events.set_xlim([0, duration + DURATION_MARGIN])
    ax_events.set_xticks(np.arange(0, duration + DURATION_MARGIN, 50))
    ax_events.grid(True, alpha=0.3)

    # Prepare workloads list for y-axis
    displayed_workloads = sorted(list(workloads))
    ax_events.set_yticks(range(len(displayed_workloads)))
    ax_events.set_yticklabels(displayed_workloads)
    ax_events.set_ylim([-0.5, len(displayed_workloads) - 0.5])

    # Plot job timelines as bars
    for idx, name in enumerate(displayed_workloads):
        # Get all events for this workload
        job_events = events_df[events_df["process_name"] == name]

        # Use a consistent color from matplotlib's color cycle
        color = WORKLOAD_COLORS.get(name, f"C{idx % 10}")

        # Group events by pairs (start/finish)
        start_events = job_events[job_events["event"] == "START"].sort_values(
            "timestamp"
        )
        end_events = job_events[job_events["event"] == "END"].sort_values(
            "timestamp"
        )

        # Plot horizontal bars for each job instance
        for i in range(min(len(start_events), len(end_events))):
            start_time = start_events.iloc[i]["timestamp"]
            end_time = end_events.iloc[i]["timestamp"]
            duration = end_time - start_time

            # Draw the horizontal job bar
            ax_events.barh(
                idx,  # Y position
                duration,  # Width = duration
                height=0.6,  # Height of the bar
                left=start_time,  # X position = start time
                color=color,  # Bar color
                alpha=0.7,  # Transparency
                edgecolor=color,  # Border color
                linewidth=1.5,  # Border width
            )

    # Add vertical line at time 0 (first job start)
    axA_95p.axvline(x=0, color="black", linestyle=":", linewidth=1.0)
    ax_events.axvline(x=0, color="black", linestyle=":", linewidth=1.0)

    # Add label for first job start
    ax_events.text(
        0,
        -0.5,
        "First Job Start",
        ha="center",
        va="top",
        fontsize=8,
        bbox=dict(
            facecolor="white", alpha=0.8, edgecolor="black", boxstyle="round,pad=0.3"
        ),
    )

    # Adjust layout
    plt.subplots_adjust(hspace=0.3)
    plt.tight_layout()

    # Show the plot
    # plt.show()

    # Save figure
    output_path = os.path.join(save_folder_path, f"{run_number}A.png")
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Created visualization for run {run_number} -> {output_path}")

    # Print summary statistics
    if not mcperf_df.empty:
        slo_violations = sum(mcperf_df["p95_ms"] > 0.8)

        print(f"  Total measurements: {len(mcperf_df)}")
        print(
            f"  SLO violations (>0.8ms): {slo_violations} ({slo_violations/len(mcperf_df)*100:.1f}%)"
        )
        print(
            f"  Min/Avg/Max p95 latency: {mcperf_df['p95_ms'].min():.2f}/{mcperf_df['p95_ms'].mean():.2f}/{mcperf_df['p95_ms'].max():.2f} ms"
        )

def create_plots_B(input_directory_path, policy_number, run_number, save_folder_path):
    mcperf_file = os.path.join(input_directory_path, f"mcperf_policy{policy_number}_run{run_number}.log")
    scheduler_file = os.path.join(input_directory_path, f"job_times/job_start_end_times/job_times_policy{policy_number}_run{run_number}.csv")
    cpu_usage_file = os.path.join(input_directory_path, f"job_times/memcached_cpu_usage/memcached_cpu_usage_policy{policy_number}_run{run_number}.csv")

    if not os.path.exists(mcperf_file) or not os.path.exists(scheduler_file) or not os.path.exists(cpu_usage_file):
        print(f"Missing files for run {run_number}. Skipping.")
        return

    # Parse data into DataFrames
    mcperf_df = parse_mcperf_data(mcperf_file)
    events_df, earliest_start_ms = process_execution_intervals(scheduler_file)
    cpu_usage_df = process_cpu_usage_of_memcached(cpu_usage_file)

    if mcperf_df.empty or events_df.empty or cpu_usage_df.empty:
        print(f"No data found for run {run_number}. Skipping.")
        return

    # Print some debug info
    print(
        f"Run {run_number}: Found {len(mcperf_df)} mcperf data points"
    )

    # Convert timestamps to seconds relative to first job start
    mcperf_df["timestamp"] = (mcperf_df["timestamp_ms"] - earliest_start_ms) / 1000
    events_df["timestamp"] = (events_df["timestamp_ms"] - earliest_start_ms) / 1000
    cpu_usage_df["timestamp"] = (cpu_usage_df["timestamp_ms"] - earliest_start_ms) / 1000

    # Filter to include only data after the first job start (with a margin for visibility)
    mcperf_df = mcperf_df[
        mcperf_df["timestamp"] >= 0
    ]  # Only include data from job start

    cpu_usage_df = cpu_usage_df[
        cpu_usage_df["timestamp"] >= 0
    ]  # Only include data from job start

    # Get list of unique workloads for the events plot
    workloads = events_df["process_name"].unique()

    # Calculate experiment duration
    if not events_df.empty:
        duration = max(events_df["timestamp"]) + 20  # Add margin at end
    else:
        duration = max(mcperf_df["timestamp"]) + 20

    # Create the figure with two subplots
    fig = plt.figure(figsize=(10, 6))
    # Create subplots with specific height ratios
    ax_cpu, ax_events = fig.subplots(2, 1, gridspec_kw={"height_ratios": [3, 1.5]})

    # Upper subplot: P95 latency and QPS
    ax_cpu.set_title(f"{run_number}B")
    ax_cpu.set_xlim([0, duration + DURATION_MARGIN])
    ax_cpu.set_xlabel("Time [s]")
    ax_cpu.set_xticks(np.arange(0, duration + DURATION_MARGIN, 50))
    ax_cpu.grid(True, alpha=0.3)
    ax_cpu.set_ylabel("Number of CPU Cores in use by Memcached")
    ax_cpu.tick_params(axis="y", labelcolor="tab:blue")

    # Set y-axis limits and ticks for latency
    ax_cpu.set_ylim([1, 3])
    ax_cpu.set_yticks([1, 2, 3])

    # Plot P95 latency line
    (artistA_cpu,) = ax_cpu.plot(
        cpu_usage_df["timestamp"],
        cpu_usage_df["memcached_cores_usage"],
        color="tab:blue",
        label="Memcached CPU Cores Usage",
    )

    # Add QPS on secondary y-axis
    axA_QPS = ax_cpu.twinx()
    axA_QPS.set_ylabel("Queries per second")

    # Scale QPS axis appropriately
    max_qps = max(40000, mcperf_df["qps"].max() * 1.1)
    axA_QPS.set_ylim([0, max_qps])
    axA_QPS.set_yticks(np.arange(0, max_qps + 1, 10000))
    axA_QPS.yaxis.set_major_formatter(
        FuncFormatter(lambda x_val, tick_pos: "{:.0f}k".format(x_val / 1000))
    )
    axA_QPS.tick_params(axis="y", labelcolor="tab:orange")
    axA_QPS.grid(False)

    (artistA_QPS,) = axA_QPS.plot(
        mcperf_df["timestamp"], mcperf_df["qps"], color="tab:orange", label="QPS"
    )

    # Add legend with SLO line included
    axA_QPS.legend(
        [artistA_QPS, artistA_cpu],
        ["QPS", "Memcached CPU Cores Usage"],
        loc="upper right",
    )

    # Lower subplot: Job timeline
    ax_events.set_xlim([0, duration + DURATION_MARGIN])
    ax_events.set_xticks(np.arange(0, duration + DURATION_MARGIN, 50))
    ax_events.grid(True, alpha=0.3)

    # Prepare workloads list for y-axis
    displayed_workloads = sorted(list(workloads))
    ax_events.set_yticks(range(len(displayed_workloads)))
    ax_events.set_yticklabels(displayed_workloads)
    ax_events.set_ylim([-0.5, len(displayed_workloads) - 0.5])

    # Plot job timelines as bars
    for idx, name in enumerate(displayed_workloads):
        # Get all events for this workload
        job_events = events_df[events_df["process_name"] == name]

        # Use a consistent color from matplotlib's color cycle
        color = WORKLOAD_COLORS.get(name, f"C{idx % 10}")

        # Group events by pairs (start/finish)
        start_events = job_events[job_events["event"] == "START"].sort_values(
            "timestamp"
        )
        end_events = job_events[job_events["event"] == "END"].sort_values(
            "timestamp"
        )

        # Plot horizontal bars for each job instance
        for i in range(min(len(start_events), len(end_events))):
            start_time = start_events.iloc[i]["timestamp"]
            end_time = end_events.iloc[i]["timestamp"]
            duration = end_time - start_time

            # Draw the horizontal job bar
            ax_events.barh(
                idx,  # Y position
                duration,  # Width = duration
                height=0.6,  # Height of the bar
                left=start_time,  # X position = start time
                color=color,  # Bar color
                alpha=0.7,  # Transparency
                edgecolor=color,  # Border color
                linewidth=1.5,  # Border width
            )

    # Add vertical line at time 0 (first job start)
    ax_cpu.axvline(x=0, color="black", linestyle=":", linewidth=1.0)
    ax_events.axvline(x=0, color="black", linestyle=":", linewidth=1.0)

    # Add label for first job start
    ax_events.text(
        0,
        -0.5,
        "First Job Start",
        ha="center",
        va="top",
        fontsize=8,
        bbox=dict(
            facecolor="white", alpha=0.8, edgecolor="black", boxstyle="round,pad=0.3"
        ),
    )

    # Adjust layout
    plt.subplots_adjust(hspace=0.3)
    plt.tight_layout()

    # Show the plot
    # plt.show()

    # Save figure
    output_path = os.path.join(save_folder_path, f"{run_number}B.png")
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Created visualization for run {run_number} -> {output_path}")

    # Print summary statistics
    if not mcperf_df.empty:
        slo_violations = sum(mcperf_df["p95_ms"] > 0.8)

        print(f"  Total measurements: {len(mcperf_df)}")
        print(
            f"  SLO violations (>0.8ms): {slo_violations} ({slo_violations/len(mcperf_df)*100:.1f}%)"
        )
        print(
            f"  Min/Avg/Max p95 latency: {mcperf_df['p95_ms'].min():.2f}/{mcperf_df['p95_ms'].mean():.2f}/{mcperf_df['p95_ms'].max():.2f} ms"
        )

def main():
    # Run the visualization for all three runs
    # input_directory_path_4_3 = "part4/part4_3_logs"
    # output_directory_path_4_3 = "part4/plots/part_4_3"

    # input_directory_path_4_4_9s = "part4/part4_4_logs/9s_interval"
    # output_directory_path_4_4_9s = "part4/plots/part_4_4/9s_interval"
    # input_directory_path_4_4_5s = "part4/part4_4_logs/5s_interval"
    # output_directory_path_4_4_5s = "part4/plots/part_4_4/5s_interval"
    input_directory_path_4_4_7s = "part4/part4_4_logs/7s_interval"
    output_directory_path_4_4_7s = "part4/plots/part_4_4/7s_interval"

    # Create output directories
    # ensure_directory_exists(output_directory_path_4_4_9s)
    # ensure_directory_exists(output_directory_path_4_4_5s)

    for run in [1, 2, 3]:
        print(f"\nProcessing run {run}...")
        # create_plots_A(input_directory_path_4_3, 1, run, output_directory_path_4_3)
        # create_plots_B(input_directory_path_4_3, 1, run, output_directory_path_4_3)
        # create_plots_A(input_directory_path_4_4_9s, 1, run, output_directory_path_4_4_9s)
        # create_plots_B(input_directory_path_4_4_9s, 1, run, output_directory_path_4_4_9s)
        # create_plots_A(input_directory_path_4_4_5s, 1, run, output_directory_path_4_4_5s)
        # create_plots_B(input_directory_path_4_4_5s, 1, run, output_directory_path_4_4_5s)
        create_plots_A(input_directory_path_4_4_7s, 1, run, output_directory_path_4_4_7s)
        create_plots_B(input_directory_path_4_4_7s, 1, run, output_directory_path_4_4_7s)


if __name__ == "__main__":
    main()