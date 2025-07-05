import os
import numpy as np
import matplotlib.pyplot as plt
import glob

# Configuration types
config_types = ["none", "cpu", "l1d", "l1i", "l2", "llc", "membw"]
num_runs = 3  # Number of runs per configuration

# Directory where log files are stored
log_dir = "./logs"


# Function to parse a benchmark file
def parse_benchmark_file(file_path):
    data = []
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("read"):
                    parts = line.split()
                    p95_latency = float(parts[12])  # p95 column
                    actual_qps = float(parts[-2])  # QPS column (second to last)
                    data.append((actual_qps, p95_latency))
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return data


# Dictionary to store all results
all_results = {}

# Process each configuration type
for config in config_types:
    # Find all files for this configuration
    files = glob.glob(f"{log_dir}/benchmark_results_{config}_*.txt")

    # Group data by file index (run number)
    all_runs_data = []
    for i in range(num_runs):
        file_pattern = f"{log_dir}/benchmark_results_{config}_{i}.txt"
        if os.path.exists(file_pattern):
            run_data = parse_benchmark_file(file_pattern)
            all_runs_data.append(run_data)
        else:
            print(f"Warning: {file_pattern} not found")

    # Skip if no data found
    if not all_runs_data:
        print(f"No data found for {config} configuration")
        continue

    # Process the data for this configuration
    qps_by_target = {}
    p95_by_target = {}

    # Group by target QPS (assuming same number of targets in each run)
    for run_idx, run_data in enumerate(all_runs_data):
        for idx, (qps, p95) in enumerate(run_data):
            if idx not in qps_by_target:
                qps_by_target[idx] = []
                p95_by_target[idx] = []
            qps_by_target[idx].append(qps)
            p95_by_target[idx].append(p95)

    # Calculate mean and std for this configuration
    qps_means = []
    qps_stds = []
    p95_means = []
    p95_stds = []

    for idx in sorted(qps_by_target.keys()):
        qps_values = qps_by_target[idx]
        p95_values = p95_by_target[idx]

        qps_means.append(np.mean(qps_values))
        qps_stds.append(np.std(qps_values))
        p95_means.append(np.mean(p95_values))
        p95_stds.append(np.std(p95_values))

    all_results[config] = {
        "qps_means": qps_means,
        "qps_stds": qps_stds,
        "p95_means": p95_means,
        "p95_stds": p95_stds,
    }

# Create the plot
plt.figure(figsize=(12, 8))

# Colors and markers for better visibility
colors = ["blue", "red", "green", "orange", "purple", "brown", "black"]
markers = ["o", "s", "^", "D", "*", "x", "+"]

# Plot each configuration
for i, config in enumerate(config_types):
    if config not in all_results:
        continue

    data = all_results[config]

    # Cap the latency at 6ms for visualization as specified
    capped_p95 = [min(x, 6.0) for x in data["p95_means"]]

    plt.errorbar(
        data["qps_means"],
        capped_p95,
        xerr=data["qps_stds"],
        yerr=data["p95_stds"],
        fmt=f"{markers[i]}-",
        color=colors[i],
        label=config.upper(),
        capsize=5,
        markersize=8,
    )

# Set plot limits and labels
plt.xlim(0, 80000)
plt.ylim(0, 6)
plt.xlabel("Queries Per Second (QPS)", fontsize=14)
plt.ylabel("95th Percentile Latency (ms)", fontsize=14)
plt.title("Memcached Performance under Different Interference Types", fontsize=16)
plt.grid(True, linestyle="--", alpha=0.7)
plt.legend(loc="best", fontsize=12)

# Add a note about number of runs
plt.figtext(
    0.5,
    0.01,
    f"Note: Each data point represents the average of {num_runs} runs with standard deviation error bars.",
    ha="center",
    fontsize=10,
)

# Save the plot
plt.tight_layout(pad=2.0)
plt.savefig("memcached_benchmark_results.png", dpi=300, bbox_inches="tight")
plt.show()

print("Plot saved as 'memcached_benchmark_results.png'")
