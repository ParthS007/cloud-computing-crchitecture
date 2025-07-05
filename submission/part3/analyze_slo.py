import json
import re
from datetime import datetime
import os
import numpy as np


def parse_datetime(dt_str):
    """Parse Kubernetes datetime string to Python datetime object."""
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")


def get_batch_job_time_window(pods_file):
    """Extract start time of first batch job and end time of last batch job."""
    with open(pods_file, "r") as f:
        data = json.load(f)

    earliest_start = None
    latest_completion = None

    # Process each pod
    for pod in data.get("items", []):
        # Check if the pod is part of a job
        metadata = pod.get("metadata", {})
        labels = metadata.get("labels", {})

        # Find job name from labels
        job_name = labels.get("job-name") or labels.get("batch.kubernetes.io/job-name")

        if job_name and "parsec" in job_name:  # Only consider parsec jobs
            status = pod.get("status", {})

            start_time = status.get("startTime")
            if not start_time:
                continue

            # Find container completion time
            completion_time = None
            container_statuses = status.get("containerStatuses", [])
            for container in container_statuses:
                if "state" in container and "terminated" in container["state"]:
                    if "finishedAt" in container["state"]["terminated"]:
                        completion_time = container["state"]["terminated"]["finishedAt"]
                        break

            if start_time and completion_time:
                start_dt = parse_datetime(start_time)
                completion_dt = parse_datetime(completion_time)

                if earliest_start is None or start_dt < earliest_start:
                    earliest_start = start_dt
                if latest_completion is None or completion_dt > latest_completion:
                    latest_completion = completion_dt

    return earliest_start, latest_completion


def parse_mcperf_data(mcperf_file, start_time, end_time):
    """Parse mcperf data file and extract 95th percentile latency data points."""
    data_points = []
    slo_violations = 0
    total_checked = 0

    with open(mcperf_file, "r") as f:
        lines = f.readlines()

    # Skip header and comment lines
    for line_num, line in enumerate(lines):
        if line.startswith("#") or not line.strip():
            continue

        # Parse columns (space-separated)
        parts = line.strip().split()
        if len(parts) < 15:  # Need at least 15 columns for ts_start and ts_end
            continue

        try:
            # Extract p95 latency (microseconds) - column 13
            p95_latency_us = float(parts[12])

            # Extract timestamps (milliseconds since epoch)
            ts_start_ms = int(parts[-2])
            ts_end_ms = int(parts[-1])

            # Convert to datetime using UTC (important for timezone consistency)
            ts_start = datetime.utcfromtimestamp(ts_start_ms / 1000.0)
            ts_end = datetime.utcfromtimestamp(ts_end_ms / 1000.0)

            total_checked += 1

            # Check if measurement overlaps with batch job window
            if ts_end < start_time or ts_start > end_time:
                continue

            # Convert latency to milliseconds
            p95_latency_ms = p95_latency_us / 1000.0

            # Add to data points
            data_points.append(p95_latency_ms)

            # Check SLO violation (latency > 1ms)
            if p95_latency_ms > 1.0:
                slo_violations += 1

        except (ValueError, IndexError) as e:
            print(f"Error parsing line {line_num}: {line.strip()[:50]}... - {str(e)}")
            continue

    print(f"Total mcperf records checked: {total_checked}")
    print(f"Data points in batch window: {len(data_points)}")

    return data_points, slo_violations


def main():
    directory = "part_3_results_group_020"

    print("SLO Violation Analysis for Memcached")
    print("====================================")

    results = []

    for i in range(1, 4):
        pods_file = os.path.join(directory, f"pods_{i}.json")
        mcperf_file = os.path.join(directory, f"mcperf_{i}.txt")

        print(f"\nRun {i}:")
        print("-" * (len(f"Run {i}:") + 1))

        try:
            # Get time window when batch jobs were running
            start_time, end_time = get_batch_job_time_window(pods_file)

            if not start_time or not end_time:
                print(f"Could not determine batch job time window for run {i}")
                continue

            duration = (end_time - start_time).total_seconds()
            print(
                f"Batch job window: {start_time} to {end_time} (duration: {duration:.2f}s)"
            )

            # Parse mcperf data and calculate SLO violations
            data_points, slo_violations = parse_mcperf_data(
                mcperf_file, start_time, end_time
            )

            total_points = len(data_points)

            if total_points > 0:
                slo_violation_ratio = slo_violations / total_points
                results.append(slo_violation_ratio)

                print(f"Data points analyzed: {total_points}")
                print(f"SLO violations (latency > 1ms): {slo_violations}")
                print(
                    f"SLO violation ratio: {slo_violation_ratio:.4f} ({slo_violations}/{total_points})"
                )
            else:
                print(f"No data points found during batch job window.")

        except Exception as e:
            print(f"Error processing run {i}: {e}")

    # Print summary statistics
    if results:
        mean_ratio = np.mean(results)
        std_dev = np.std(results, ddof=1) if len(results) > 1 else 0

        print("\nSummary:")
        print("========")
        print(f"SLO violation ratios: {', '.join(f'{r:.4f}' for r in results)}")
        print(f"Mean SLO violation ratio: {mean_ratio:.4f}")
        print(f"Standard deviation: {std_dev:.4f}")

        # Print in table format for easy inclusion in reports
        print("\nTable Format:")
        print(f"| {'Run':<8} | {'SLO Violation Ratio':<20} |")
        print(f"| {'-'*8} | {'-'*20} |")
        for i, ratio in enumerate(results, 1):
            print(f"| {f'Run {i}':<8} | {ratio:.4f}{' '*15} |")
        print(f"| {'Mean':<8} | {mean_ratio:.4f}{' '*15} |")
        print(f"| {'Std Dev':<8} | {std_dev:.4f}{' '*15} |")
    else:
        print("\nNo valid results were obtained.")


if __name__ == "__main__":
    main()
