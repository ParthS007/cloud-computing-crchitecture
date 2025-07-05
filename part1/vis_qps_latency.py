import os
import glob
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# Define the configuration types we're analyzing
config_types = ["none", "cpu", "l1d", "l1i", "l2", "llc", "membw"]
num_runs = 3  # Number of runs per configuration
log_dir = "./logs"  # Directory containing the benchmark logs

# Visual styling elements - Distinct colors and markers for each configuration
colors = [
    "blue",
    "red",
    "green",
    "orange",
    "purple",
    "brown",
    "black",
]
markers = ["o", "s", "^", "D", "*", "x", "+"]


def parse_benchmark_file(file_path):
    """
    Parse a memcached benchmark file to extract relevant performance metrics.

    The file format has rows starting with 'read' containing latency percentiles and QPS data.
    Each row represents measurements for a particular target QPS level.

    Args:
        file_path: Path to the benchmark results file

    Returns:
        List of dictionaries, each containing parsed metrics for one QPS level
    """
    data = []
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
            for line in lines[1:]:
                if line.startswith("read"):
                    parts = line.split()
                    if len(parts) >= 17:
                        row = {
                            # 95th percentile latency - our key metric of interest
                            "p95": float(parts[12]) / 1000.0,  # Convert μs to ms
                            # Actual QPS achieved
                            "actual_qps": float(parts[16]),
                            # Target QPS that was requested
                            "target_qps": float(parts[17]),
                            # Extract configuration type from filename
                            "config": os.path.basename(file_path).split("_")[2],
                            # Extract run number from filename
                            "run": int(
                                os.path.basename(file_path).split("_")[3].split(".")[0]
                            ),
                        }
                        data.append(row)
                if line.startswith("Warning"):
                    break
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return data


# PHASE 1: DATA COLLECTION
# ------------------------
print("Phase 1: Collecting benchmark data...")
all_data = []  # Will hold all parsed data points

for config in config_types:
    for i in range(num_runs):
        file_pattern = f"{log_dir}/benchmark_results_{config}_{i}.txt"
        if os.path.exists(file_pattern):
            # Parse and collect data from this file
            data = parse_benchmark_file(file_pattern)
            all_data.extend(data)
        else:
            print(f"Warning: {file_pattern} not found")
if not all_data:
    print("No data found. Check your log directory and file patterns.")
    exit(1)

# PHASE 2: DATA PROCESSING
# ------------------------
print("Phase 2: Processing data...")

df = pd.DataFrame(all_data)

# Group by configuration and target QPS to calculate statistics across runs
# This computes mean and standard deviation for each metric across the runs
avg_df = (
    df.groupby(["config", "target_qps"])
    .agg(
        {
            "actual_qps": ["mean", "std"],
            "p95": ["mean", "std"],
        }
    )
    .reset_index()
)

# Flatten the column hierarchy created by the aggregation
avg_df.columns = ["_".join(col).strip("_") for col in avg_df.columns.values]

# PHASE 3: VISUALIZATION
# ---------------------
print("Phase 3: Creating visualization...")

# Create a new figure with appropriate size for report
plt.figure(figsize=(10, 6))

# Plot each configuration as a separate line
for i, config in enumerate(config_types):
    config_data = avg_df[avg_df["config"] == config].sort_values("actual_qps_mean")
    if not config_data.empty:
        # Plot line with error bars in both x and y dimensions
        plt.errorbar(
            config_data["actual_qps_mean"],  # X-axis: mean achieved QPS
            config_data["p95_mean"],  # Y-axis: mean P95 latency
            yerr=config_data["p95_std"],  # Y error bars: std dev of P95 latency
            xerr=config_data["actual_qps_std"],  # X error bars: std dev of QPS
            fmt=f"{markers[i]}-",  # Line style with marker
            color=colors[i],  # Line color
            label=config.upper(),  # Legend label
            linewidth=2,  # Thicker line for visibility
            markersize=8,  # Larger markers for clarity
            capsize=5,  # Add caps to the error bars
        )

plt.xlim(0, 80000)  # X-axis from 0 to 80K QPS as specified
plt.xlabel("Actual Queries Per Second (QPS)", fontsize=14)
plt.ylim(0, 6)  # Y-axis from 0 to 6 ms for P95 latency
plt.ylabel("95th Percentile Latency (ms)", fontsize=14)
plt.title(
    "Memcached P95 Latency vs QPS Under Different Interference Types", fontsize=16
)

# Add grid for easier reading
plt.grid(True, linestyle="--", alpha=0.7)

# Add legend to identify configurations
plt.legend(fontsize=12, loc="best")

plt.figtext(
    0.5,
    0.01,
    f"Note: Each data point represents the average of {num_runs} runs.",
    ha="center",
    fontsize=10,
)

# Save the visualization to a file
output_file = "memcached_p95_qps_plot.png"
plt.savefig(output_file, dpi=500, bbox_inches="tight")
print(f"Visualization saved to {output_file}")
