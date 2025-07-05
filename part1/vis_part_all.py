import os
import glob
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Configuration types
config_types = ["none", "cpu", "l1d", "l1i", "l2", "llc", "membw"]
num_runs = 3  # Number of runs per configuration
log_dir = "./logs"

# Colors for better visibility
colors = ["blue", "red", "green", "orange", "purple", "brown", "black"]
markers = ["o", "s", "^", "D", "*", "x", "+"]


# Function to parse a benchmark file
def parse_benchmark_file(file_path):
    data = []
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
            # Skip the header line
            for line in lines[1:]:
                if line.startswith("read"):
                    parts = line.split()
                    if len(parts) >= 17:  # Make sure we have enough columns
                        row = {
                            "type": parts[0],
                            "avg": float(parts[1]),
                            "std": float(parts[2]),
                            "min": float(parts[3]),
                            "p5": float(parts[4]),
                            "p10": float(parts[5]),
                            "p50": float(parts[6]),
                            "p67": float(parts[7]),
                            "p75": float(parts[8]),
                            "p80": float(parts[9]),
                            "p85": float(parts[10]),
                            "p90": float(parts[11]),
                            "p95": float(parts[12]),
                            "p99": float(parts[13]),
                            "p999": float(parts[14]),
                            "p9999": float(parts[15]),
                            "actual_qps": float(parts[16]),
                            "target_qps": float(parts[17]),
                            "config": os.path.basename(file_path).split("_")[
                                2
                            ],  # Extract config from filename
                            "run": int(
                                os.path.basename(file_path).split("_")[3].split(".")[0]
                            ),  # Extract run number
                        }
                        data.append(row)
                # Stop processing at the warning line
                if line.startswith("Warning"):
                    break
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return data


# Parse all benchmark data
all_data = []
for config in config_types:
    for i in range(num_runs):
        file_pattern = f"{log_dir}/benchmark_results_{config}_{i}.txt"
        if os.path.exists(file_pattern):
            data = parse_benchmark_file(file_pattern)
            all_data.extend(data)
        else:
            print(f"Warning: {file_pattern} not found")

# Convert to DataFrame
if not all_data:
    print("No data found. Check your log directory and file patterns.")
    exit(1)

df = pd.DataFrame(all_data)

# Calculate average values across runs for each config and target QPS
avg_df = (
    df.groupby(["config", "target_qps"])
    .agg(
        {
            "actual_qps": ["mean", "std"],
            "p50": ["mean", "std"],
            "p95": ["mean", "std"],
            "p99": ["mean", "std"],
            "avg": ["mean", "std"],
        }
    )
    .reset_index()
)

# Flatten the column hierarchy
avg_df.columns = ["_".join(col).strip("_") for col in avg_df.columns.values]

# 1. Create combined P95 vs QPS plot
plt.figure(figsize=(12, 8))
for i, config in enumerate(config_types):
    config_data = avg_df[avg_df["config"] == config].sort_values("actual_qps_mean")
    if not config_data.empty:
        plt.errorbar(
            config_data["actual_qps_mean"],
            config_data["p95_mean"],
            xerr=config_data["actual_qps_std"],
            yerr=config_data["p95_std"],
            fmt=f"{markers[i]}-",
            color=colors[i],
            label=config.upper(),
            capsize=5,
            markersize=8,
        )

plt.xlabel("Actual QPS", fontsize=14)
plt.ylabel("P95 Latency (μs)", fontsize=14)
plt.title("P95 Latency vs Actual QPS Across Configurations", fontsize=16)
plt.grid(True, linestyle="--", alpha=0.7)
plt.legend(fontsize=12)
plt.xlim(0, 80000)
plt.tight_layout()
plt.savefig("combined_p95_qps.png", dpi=300, bbox_inches="tight")

# 2. Create multi-panel plot with all visualizations
plt.figure(figsize=(18, 12))

# Plot 1: P95 vs QPS for all configs
plt.subplot(2, 2, 1)
for i, config in enumerate(config_types):
    config_data = avg_df[avg_df["config"] == config].sort_values("actual_qps_mean")
    if not config_data.empty:
        plt.plot(
            config_data["actual_qps_mean"],
            config_data["p95_mean"],
            f"{markers[i]}-",
            color=colors[i],
            label=config.upper(),
            linewidth=2,
            markersize=6,
        )

plt.xlabel("Actual QPS", fontsize=12)
plt.ylabel("P95 Latency (μs)", fontsize=12)
plt.title("P95 Latency vs QPS by Configuration", fontsize=14)
plt.grid(True, linestyle="--", alpha=0.7)
plt.legend(fontsize=10)
plt.xlim(0, 80000)

# Plot 2: P50, P95, P99 for "none" config (baseline)
plt.subplot(2, 2, 2)
none_data = avg_df[avg_df["config"] == "none"].sort_values("actual_qps_mean")
if not none_data.empty:
    plt.plot(
        none_data["actual_qps_mean"],
        none_data["p50_mean"],
        "o-",
        label="P50",
        linewidth=2,
    )
    plt.plot(
        none_data["actual_qps_mean"],
        none_data["p95_mean"],
        "s-",
        label="P95",
        linewidth=2,
    )
    plt.plot(
        none_data["actual_qps_mean"],
        none_data["p99_mean"],
        "^-",
        label="P99",
        linewidth=2,
    )

plt.xlabel("Actual QPS", fontsize=12)
plt.ylabel("Latency (μs)", fontsize=12)
plt.title("Baseline Percentile Latencies vs QPS", fontsize=14)
plt.legend(fontsize=10)
plt.grid(True, linestyle="--", alpha=0.7)
plt.xlim(0, 80000)

# Plot 3: Log scale latency for all configs
plt.subplot(2, 2, 3)
for i, config in enumerate(config_types):
    config_data = avg_df[avg_df["config"] == config].sort_values("actual_qps_mean")
    if not config_data.empty:
        plt.semilogy(
            config_data["actual_qps_mean"],
            config_data["p95_mean"],
            f"{markers[i]}-",
            color=colors[i],
            label=config.upper(),
            linewidth=2,
            markersize=6,
        )

plt.xlabel("Actual QPS", fontsize=12)
plt.ylabel("P95 Latency (μs, log scale)", fontsize=12)
plt.title("Log Scale P95 Latency vs QPS", fontsize=14)
plt.grid(True, which="both", linestyle="--", alpha=0.7)
plt.legend(fontsize=10)
plt.xlim(0, 80000)

# Plot 4: QPS Achieved vs Target QPS for each config
plt.subplot(2, 2, 4)
for i, config in enumerate(config_types):
    config_data = avg_df[avg_df["config"] == config].sort_values("target_qps")
    if not config_data.empty:
        plt.plot(
            config_data["target_qps"],
            config_data["actual_qps_mean"],
            f"{markers[i]}-",
            color=colors[i],
            label=config.upper(),
            linewidth=2,
            markersize=6,
        )

# Add diagonal line (achieved = target)
max_qps = avg_df["target_qps"].max()
plt.plot([0, max_qps], [0, max_qps], "k--", alpha=0.5, label="Perfect Scaling")

plt.xlabel("Target QPS", fontsize=12)
plt.ylabel("Achieved QPS", fontsize=12)
plt.title("Target vs Achieved QPS by Configuration", fontsize=14)
plt.grid(True, linestyle="--", alpha=0.7)
plt.legend(fontsize=10)

# Add a suptitle with benchmark information
plt.suptitle("Memcached Performance Across Different Interference Types", fontsize=16)
plt.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust for suptitle

# Add a note about number of runs
plt.figtext(
    0.5,
    0.01,
    f"Note: Each data point represents the average of {num_runs} runs with standard deviation error bars.",
    ha="center",
    fontsize=10,
)

# Save the plots
plt.savefig("memcached_benchmark_combined.png", dpi=300, bbox_inches="tight")

# Create additional plot with P95 on log scale
plt.figure(figsize=(12, 8))
for i, config in enumerate(config_types):
    config_data = avg_df[avg_df["config"] == config].sort_values("actual_qps_mean")
    if not config_data.empty:
        plt.errorbar(
            config_data["actual_qps_mean"],
            config_data["p95_mean"],
            xerr=config_data["actual_qps_std"],
            yerr=config_data["p95_std"],
            fmt=f"{markers[i]}-",
            color=colors[i],
            label=config.upper(),
            capsize=5,
            markersize=8,
        )

plt.xlabel("Actual QPS", fontsize=14)
plt.ylabel("P95 Latency (μs, log scale)", fontsize=14)
plt.title("P95 Latency vs Actual QPS (Log Scale)", fontsize=16)
plt.grid(True, which="both", linestyle="--", alpha=0.7)
plt.legend(fontsize=12)
plt.xlim(0, 80000)
plt.figtext(
    0.5,
    0.01,
    f"Note: Each data point represents the average of {num_runs} runs with standard deviation error bars.",
    ha="center",
    fontsize=10,
)
plt.tight_layout(pad=2.0)
plt.savefig("memcached_benchmark_combined_log.png", dpi=300, bbox_inches="tight")

print("Plots saved as:")
print("- combined_p95_qps.png")
print("- memcached_benchmark_combined.png")
print("- memcached_benchmark_combined_log.png")

plt.show()
