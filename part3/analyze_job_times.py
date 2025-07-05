import json
import numpy as np
from datetime import datetime
import os


def parse_datetime(dt_str):
    """Parse Kubernetes datetime string to Python datetime object."""
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")


def calculate_execution_time(start_time, completion_time):
    """Calculate execution time in seconds."""
    start = parse_datetime(start_time)
    completion = parse_datetime(completion_time)
    return (completion - start).total_seconds()


def process_pods_file(file_path):
    """Process a pods JSON file and extract job information."""
    with open(file_path, "r") as f:
        data = json.load(f)

    job_pods = {}  # Dictionary to store pods by job name
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
                exec_time = calculate_execution_time(start_time, completion_time)

                if job_name not in job_pods:
                    job_pods[job_name] = []

                job_pods[job_name].append(
                    {
                        "name": metadata.get("name"),
                        "exec_time": exec_time,
                        "start": parse_datetime(start_time),
                        "completion": parse_datetime(completion_time),
                    }
                )

                # Update makespan tracking
                start_dt = parse_datetime(start_time)
                completion_dt = parse_datetime(completion_time)

                if earliest_start is None or start_dt < earliest_start:
                    earliest_start = start_dt
                if latest_completion is None or completion_dt > latest_completion:
                    latest_completion = completion_dt

    # Calculate average execution time for each job
    jobs = {}
    for job_name, pods in job_pods.items():
        if pods:
            jobs[job_name] = np.mean([pod["exec_time"] for pod in pods])

    # Calculate makespan (total time from earliest start to latest completion)
    makespan = None
    if earliest_start and latest_completion:
        makespan = (latest_completion - earliest_start).total_seconds()

    return jobs, makespan


def main():
    directory = "part_3_results_group_020"
    pod_files = [os.path.join(directory, f"pods_{i}.json") for i in range(1, 4)]

    all_jobs = {}
    makespans = []

    for i, file_path in enumerate(pod_files, 1):
        print(f"Processing run {i}: {file_path}")

        try:
            jobs, makespan = process_pods_file(file_path)

            # Store job execution times
            for job_name, exec_time in jobs.items():
                if job_name not in all_jobs:
                    all_jobs[job_name] = [None, None, None]  # Initialize with 3 slots
                all_jobs[job_name][i - 1] = exec_time

            # Store makespan
            makespans.append(makespan)

        except Exception as e:
            print(f"Error processing file {file_path}: {e}")

    # Print results with statistics
    print("\n## Job Execution Times (seconds)")
    print(
        f"| {'Job Name':<20} | {'Run 1':<10} | {'Run 2':<10} | {'Run 3':<10} | {'Mean':<10} | {'Std Dev':<10} |"
    )
    print(f"| {'-'*20} | {'-'*10} | {'-'*10} | {'-'*10} | {'-'*10} | {'-'*10} |")

    for job_name, times in sorted(all_jobs.items()):
        # Calculate statistics for available times
        valid_times = [t for t in times if t is not None]
        if valid_times:
            mean = np.mean(valid_times)
            std_dev = np.std(valid_times, ddof=1) if len(valid_times) > 1 else 0
        else:
            mean = std_dev = None

        # Format for display
        times_str = [f"{t:.2f}" if t is not None else "N/A" for t in times]
        mean_str = f"{mean:.2f}" if mean is not None else "N/A"
        std_dev_str = f"{std_dev:.2f}" if std_dev is not None else "N/A"

        print(
            f"| {job_name:<20} | {times_str[0]:<10} | {times_str[1]:<10} | {times_str[2]:<10} | {mean_str:<10} | {std_dev_str:<10} |"
        )

    # Print makespan statistics
    print("\n## Makespan (seconds)")
    print(
        f"| {'Run 1':<10} | {'Run 2':<10} | {'Run 3':<10} | {'Mean':<10} | {'Std Dev':<10} |"
    )
    print(f"| {'-'*10} | {'-'*10} | {'-'*10} | {'-'*10} | {'-'*10} |")

    # Calculate statistics for makespan
    valid_makespans = [m for m in makespans if m is not None]
    if valid_makespans:
        mean_makespan = np.mean(valid_makespans)
        std_dev_makespan = (
            np.std(valid_makespans, ddof=1) if len(valid_makespans) > 1 else 0
        )
    else:
        mean_makespan = std_dev_makespan = None

    # Format for display
    makespans_str = [f"{m:.2f}" if m is not None else "N/A" for m in makespans]
    mean_str = f"{mean_makespan:.2f}" if mean_makespan is not None else "N/A"
    std_dev_str = f"{std_dev_makespan:.2f}" if std_dev_makespan is not None else "N/A"

    print(
        f"| {makespans_str[0]:<10} | {makespans_str[1]:<10} | {makespans_str[2]:<10} | {mean_str:<10} | {std_dev_str:<10} |"
    )


if __name__ == "__main__":
    main()
