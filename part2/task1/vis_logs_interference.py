#!/usr/bin/env python3
"""
PARSEC Interference Visualizer

This script analyzes PARSEC benchmark results and creates visualizations
of the impact of interference on performance.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import argparse
import os
import sys

# Default configuration (can be overridden with command line args)
WORKLOADS = ["blackscholes", "canneal", "dedup", "ferret", "freqmine", "radix", "vips"]
INTERFERENCE_TYPES = ["none", "cpu", "l1d", "l1i", "l2", "llc", "membw"]


def analyze_results(df, workloads=None, interference_types=None):
    """Analyze results and create normalized execution time table."""
    # Use provided lists or defaults
    workloads = workloads or WORKLOADS
    interference_types = interference_types or INTERFERENCE_TYPES

    # Calculate median execution time for each workload with no interference
    baseline = (
        df[df["interference"] == "none"].groupby("workload")["execution_time"].median()
    )

    print(f"Baseline execution times (no interference):")
    for workload, time in baseline.items():
        print(f"  {workload}: {time:.2f}s")

    # Calculate normalized execution time
    normalized_df = df.copy()
    normalized_df["normalized_time"] = normalized_df.apply(
        lambda row: (
            row["execution_time"] / baseline[row["workload"]]
            if row["workload"] in baseline.index
            else np.nan
        ),
        axis=1,
    )

    # Group by workload and interference, and calculate median of normalized times
    result_df = (
        normalized_df.groupby(["workload", "interference"])["normalized_time"]
        .median()
        .reset_index()
    )

    # Pivot to get the required table format
    pivot_df = result_df.pivot(
        index="workload", columns="interference", values="normalized_time"
    )

    # Ensure all workloads and interferences are present
    for w in workloads:
        if w not in pivot_df.index:
            pivot_df.loc[w] = np.nan

    for i in interference_types:
        if i not in pivot_df.columns:
            pivot_df[i] = np.nan

    # Round to 2 decimal places
    pivot_df = pivot_df.round(2)

    return pivot_df


def visualize_results(df, output_dir):
    """Create a color-coded visualization of the results."""
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define color mapping function for cell backgrounds
    def color_mapping(val):
        if pd.isna(val):
            return "background-color: white"
        elif val <= 1.3:
            return "background-color: lightgreen"
        elif val <= 2.0:
            return "background-color: orange"
        else:
            return "background-color: red"

    # Apply color mapping for HTML
    styled_df = df.style.map(color_mapping)
    styled_df.set_caption(
        "Normalized Execution Time Under Different Interference Types"
    )

    # Save to CSV
    df.to_csv(output_dir / "normalized_times.csv")

    # Save to HTML with styling
    styled_df.to_html(output_dir / "normalized_times_colored.html")

    # Create heatmap
    plt.figure(figsize=(12, 8))

    # Create a custom colormap for our specific thresholds
    cmap = plt.cm.RdYlGn_r  # Red-Yellow-Green reversed

    # Create heatmap
    sns.heatmap(
        df.sort_index(),
        annot=True,
        cmap=cmap,
        vmin=1.0,
        vmax=3.0,
        linewidths=0.5,
        fmt=".2f",
    )
    plt.title(
        "Normalized Execution Time Under Different Interference Types", fontsize=16
    )
    plt.tight_layout()
    plt.savefig(output_dir / "interference_heatmap.png", dpi=300)

    # Create bar chart comparison
    plt.figure(figsize=(14, 10))

    # Reshape data for plotting
    df_melted = df.reset_index().melt(
        id_vars=["workload"],
        value_vars=[c for c in df.columns if c != "none"],
        var_name="interference",
        value_name="normalized_time",
    )

    # Plot grouped bar chart
    g = sns.catplot(
        data=df_melted,
        x="workload",
        y="normalized_time",
        hue="interference",
        kind="bar",
        height=6,
        aspect=2,
    )
    g.set_xticklabels(rotation=45)
    g.set_ylabels("Normalized Execution Time (ratio to baseline)")
    plt.title(
        "Impact of Different Interference Types on PARSEC Benchmarks", fontsize=16
    )
    plt.axhline(y=1.0, color="black", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_dir / "interference_bars.png", dpi=300)

    print(f"Visualizations saved to {output_dir}")
    return styled_df


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Visualize PARSEC interference results"
    )
    parser.add_argument(
        "results_csv", type=str, help="Path to results CSV file with execution times"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="visualizations",
        help="Directory to save visualizations (default: visualizations)",
    )
    return parser.parse_args()


def main():
    """Main execution flow."""
    args = parse_arguments()

    # Check if results file exists
    if not os.path.exists(args.results_csv):
        print(f"ERROR: Results file not found: {args.results_csv}")
        sys.exit(1)

    print(f"Loading results from {args.results_csv}")
    df = pd.read_csv(args.results_csv)

    # Basic validation
    required_columns = ["workload", "interference", "execution_time"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print(
            f"ERROR: Results CSV missing required columns: {', '.join(missing_columns)}"
        )
        sys.exit(1)

    # Print basic statistics
    print(f"\nLoaded {len(df)} experiment results")
    print(f"Workloads: {df['workload'].unique()}")
    print(f"Interference types: {df['interference'].unique()}")
    print(f"Repetitions: {df['repetition'].max()}")

    # Analyze results
    print("\nAnalyzing results...")
    normalized_df = analyze_results(df)

    # Visualize results
    print("\nCreating visualizations...")
    styled_df = visualize_results(normalized_df, args.output_dir)

    # Print normalized times table
    print("\nNormalized execution times:")
    print(normalized_df)

    print(f"\nAll visualizations saved to {args.output_dir}/")


if __name__ == "__main__":
    main()
