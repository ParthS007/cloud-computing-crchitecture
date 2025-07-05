#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import json
import pandas as pd
from datetime import datetime
import os
from matplotlib.ticker import FuncFormatter

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


def parse_mcperf_data(file_path):
    """Parse mcperf data into a pandas DataFrame."""
    data = []
    # Correction for the 2-hour time difference (2 hours = 7,200,000 milliseconds)
    TIME_CORRECTION_MS = 7200000

    with open(file_path, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split()
            if parts[0] == "read" and len(parts) >= 16:
                # Get raw Unix epoch timestamps in milliseconds and apply time correction
                ts_start_ms = int(parts[-2]) - TIME_CORRECTION_MS
                ts_end_ms = int(parts[-1]) - TIME_CORRECTION_MS
                ts_mid_ms = (ts_start_ms + ts_end_ms) / 2

                # Extract performance metrics
                p95 = float(parts[12])
                qps = float(parts[16])  # QPS is typically the 2nd value

                data.append(
                    {
                        "timestamp_ms": ts_mid_ms,
                        "ts_start_ms": ts_start_ms,
                        "ts_end_ms": ts_end_ms,
                        "p95_us": p95,  # Store original microseconds
                        "p95_ms": p95 / 1000,  # Convert to milliseconds
                        "qps": qps,
                    }
                )

    # Convert to DataFrame for easier manipulation
    return pd.DataFrame(data)


def parse_datetime(dt_str):
    """Parse Kubernetes datetime string to Python datetime object."""
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")


def process_pods_file(file_path):
    """Process a pods JSON file and extract job events with timestamps."""
    with open(file_path, "r") as f:
        data = json.load(f)

    job_events = []
    earliest_start_ms = None

    # Process each pod
    for pod in data.get("items", []):
        metadata = pod.get("metadata", {})
        labels = metadata.get("labels", {})

        job_name = labels.get("job-name") or labels.get("batch.kubernetes.io/job-name")

        if job_name and any(workload in job_name for workload in WORKLOADS):
            # Get the workload name without the "parsec-" prefix
            workload_name = job_name.replace("parsec-", "")

            status = pod.get("status", {})
            spec = pod.get("spec", {})

            # Get start time
            start_time = status.get("startTime")
            if not start_time:
                for container in status.get("containerStatuses", []):
                    if "state" in container and "terminated" in container["state"]:
                        if "startedAt" in container["state"]["terminated"]:
                            start_time = container["state"]["terminated"]["startedAt"]
                            break

            # Get end time
            completion_time = None
            for container in status.get("containerStatuses", []):
                if "state" in container and "terminated" in container["state"]:
                    if "finishedAt" in container["state"]["terminated"]:
                        completion_time = container["state"]["terminated"]["finishedAt"]
                        break

            if start_time and completion_time:
                start_dt = parse_datetime(start_time)
                completion_dt = parse_datetime(completion_time)

                start_ms = int(start_dt.timestamp() * 1000)
                end_ms = int(completion_dt.timestamp() * 1000)

                # Get node information
                node_name = spec.get("nodeName", "unknown")

                # Update earliest start time
                if earliest_start_ms is None or start_ms < earliest_start_ms:
                    earliest_start_ms = start_ms

                # Record start event
                job_events.append(
                    {
                        "timestamp_ms": start_ms,
                        "process_name": workload_name,
                        "event": "START",
                        "node": node_name,
                    }
                )

                # Record end event
                job_events.append(
                    {
                        "timestamp_ms": end_ms,
                        "process_name": workload_name,
                        "event": "FINISH",
                        "node": node_name,
                    }
                )

    # Convert to DataFrame
    events_df = pd.DataFrame(job_events)
    return events_df, earliest_start_ms


def create_plots(run_number):
    mcperf_file = os.path.abspath(f"part3/part_3_results_group_020/mcperf_{run_number}.txt")
    pods_file = os.path.abspath(f"part3/part_3_results_group_020/pods_{run_number}.json")
    

    if not os.path.exists(mcperf_file) or not os.path.exists(pods_file):
        print(f"Missing files for run {run_number}. Skipping.")
        return

    # Parse data into DataFrames
    mcperf_df = parse_mcperf_data(mcperf_file)
    events_df, earliest_start_ms = process_pods_file(pods_file)

    if mcperf_df.empty or events_df.empty:
        print(f"No data found for run {run_number}. Skipping.")
        return

    # Print some debug info
    print(
        f"Run {run_number}: Found {len(mcperf_df)} mcperf data points and {len(events_df) // 2} jobs"
    )

    # Convert timestamps to seconds relative to first job start
    mcperf_df["timestamp"] = (mcperf_df["ts_start_ms"] - earliest_start_ms) / 1000
    events_df["timestamp"] = (events_df["timestamp_ms"] - earliest_start_ms) / 1000

    # Filter to include only data after the first job start (with a margin for visibility)
    mcperf_df = mcperf_df[
        mcperf_df["timestamp"] >= 0
    ]  # Only include data from job start

    # Get list of unique workloads for the events plot
    workloads = events_df["process_name"].unique()

    # Calculate experiment duration
    if not events_df.empty:
        duration = max(events_df["timestamp"]) + 20
    else:
        duration = max(mcperf_df["timestamp"]) + 20

    # Create the figure with two subplots
    fig = plt.figure(figsize=(10, 6))
    # Create subplots with specific height ratios
    axA_95p, ax_events = fig.subplots(2, 1, gridspec_kw={"height_ratios": [3, 1.5]})

    # Upper subplot: P95 latency and QPS
    axA_95p.set_title(f"Run {run_number} Visualization")
    axA_95p.set_xlim([0, duration])
    axA_95p.set_xlabel("Time [s]")
    axA_95p.set_xticks(np.arange(0, duration + 1, 50))
    axA_95p.grid(True, alpha=0.3)
    axA_95p.set_ylabel("95th Percentile Latency [ms]")
    axA_95p.tick_params(axis="y", labelcolor="tab:blue")

    # Set y-axis limits and ticks for latency
    max_latency = max(1.2, mcperf_df["p95_ms"].max() * 0.1)
    axA_95p.set_ylim([0, max_latency])
    axA_95p.set_yticks(np.arange(0, max_latency + 0.1, 0.4))

    min_start_ms = min(mcperf_df["ts_start_ms"])

    # Plot P95 latency as vertical bars spanning from ts_start to ts_end
    artistA_95p = axA_95p.bar(
        (mcperf_df["ts_start_ms"] - min_start_ms) / 1000,  # left edge (start time in seconds)
        mcperf_df["p95_ms"],  # height (latency value)
        width=(mcperf_df["ts_end_ms"] - mcperf_df["ts_start_ms"]) / 1000,  # width (duration in seconds)
        bottom=0,  # start from y=0
        color="tab:blue",
        alpha=0.7,
        align="edge",
        label="95 percentile latency",
    )

    # Add SLO threshold line (1ms)
    slo_line = axA_95p.axhline(y=1.0, color="red", linestyle="-", linewidth=1.5)

    # Add QPS on secondary y-axis
    axA_QPS = axA_95p.twinx()
    axA_QPS.set_ylabel("Queries per second")

    # Scale QPS axis appropriately
    # max_qps = max(40000, mcperf_df["qps"].max() * 1.1)
    axA_QPS.set_ylim([29000, 31000])
    axA_QPS.set_yticks(np.arange(29000, 31001, 1000))
    axA_QPS.yaxis.set_major_formatter(
        FuncFormatter(lambda x_val, tick_pos: "{:.0f}k".format(x_val / 1000))
    )
    axA_QPS.tick_params(axis="y", labelcolor="tab:orange")
    axA_QPS.grid(False)

    # Plot QPS points
    artistA_QPS = axA_QPS.plot(
        (mcperf_df["ts_start_ms"] - min_start_ms) / 1000, mcperf_df["qps"], color="tab:orange", label="QPS"
    )

    # Add legend with SLO line included
    axA_QPS.legend(
        [artistA_QPS[0], artistA_95p, slo_line],
        ["QPS", "95 percentile latency", "SLO (1ms)"],
        loc="upper right",
    )

    # Lower subplot: Job timeline
    ax_events.set_xlim([0, duration])
    ax_events.set_xticks(np.arange(0, duration + 1, 50))
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
        end_events = job_events[job_events["event"] == "FINISH"].sort_values(
            "timestamp"
        )

        # Plot horizontal bars for each job instance
        for i in range(min(len(start_events), len(end_events))):
            start_time = start_events.iloc[i]["timestamp"]
            end_time = end_events.iloc[i]["timestamp"]
            duration = end_time - start_time

            # Get node information
            node_name = start_events.iloc[i]["node"]
            # Clean up node name for display (remove common prefixes)
            display_node = node_name
            if node_name.startswith("node-"):
                display_node = node_name.replace("node-", "")

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

            # Add node name inside the bar if there's enough space

            if duration > 15:  # Long enough for text inside
                text_x = start_time + duration / 2
                ax_events.text(
                    text_x,
                    idx,
                    display_node,
                    ha="center",
                    va="center",
                    fontsize=7,
                    fontweight="bold",
                    color="black",
                    bbox=dict(boxstyle="round,pad=0.1", fc=color, ec="none", alpha=0.8),
                )
            else:  # Short bar - place text after with constraint
                # Extend plot width to fit labels
                plot_end = max(ax_events.get_xlim()[1], end_time + 40)
                ax_events.set_xlim([0, plot_end])

                # Limited-width text label
                text_x = end_time + 2
                ax_events.text(
                    text_x,
                    idx,
                    display_node,  # Limit text length
                    ha="left",
                    va="center",
                    fontsize=7,
                    fontweight="bold",
                    color="black",
                    bbox=dict(
                        boxstyle="round,pad=0.1",
                        fc="white",
                        ec=color,
                        linewidth=1,
                        alpha=0.9,
                    ),
                )

            # Add markers for start and end
            ax_events.scatter(
                [start_time],
                [idx],
                c="white",
                edgecolor=color,
                marker="o",
                s=30,
                zorder=10,
            )
            ax_events.scatter(
                [end_time],
                [idx],
                c="white",
                edgecolor=color,
                marker="x",
                s=30,
                zorder=10,
            )
    # Add vertical line at time 0 (first job start)
    axA_95p.axvline(x=0, color="black", linestyle=":", linewidth=1.0)
    ax_events.axvline(x=0, color="black", linestyle=":", linewidth=1.0)

    # Add label for first job start
    ax_events.text(
        0,
        len(displayed_workloads),  # Position above the top workload
        "First Job Start",
        ha="center",
        va="bottom",  # Changed to bottom alignment
        fontsize=8,
        bbox=dict(
            facecolor="white", alpha=0.8, edgecolor="black", boxstyle="round,pad=0.3"
        ),
    )

    # Adjust layout
    plt.subplots_adjust(hspace=0.3)
    plt.tight_layout()

    # Save figure
    output_path = f"memcached_latency_run_{run_number}.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Created visualization for run {run_number} -> {output_path}")

    # Print summary statistics
    if not mcperf_df.empty:
        slo_violations = sum(mcperf_df["p95_ms"] > 1.0)

        print(f"  Total measurements: {len(mcperf_df)}")
        print(
            f"  SLO violations (>1ms): {slo_violations} ({slo_violations/len(mcperf_df)*100:.1f}%)"
        )
        print(
            f"  Min/Avg/Max p95 latency: {mcperf_df['p95_ms'].min():.2f}/{mcperf_df['p95_ms'].mean():.2f}/{mcperf_df['p95_ms'].max():.2f} ms"
        )


# Run the visualization for all three runs
for run in [1,2,3]:
    print(f"\nProcessing run {run}...")
    create_plots(run)

print("\nAll plots created successfully!")
