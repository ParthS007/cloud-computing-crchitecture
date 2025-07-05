#!/usr/bin/env python3
"""
PARSEC Interference Runner

This script automates running PARSEC benchmarks with different interference types
and collects execution times.
"""

import os
import time
import subprocess
import pandas as pd
from datetime import datetime
from pathlib import Path
import argparse

# Configuration
WORKLOADS = ["blackscholes", "canneal", "dedup", "ferret", "freqmine", "radix", "vips"]
INTERFERENCE_TYPES = ["none", "cpu", "l1d", "l1i", "l2", "llc", "membw"]
REPETITIONS = 3
STABILIZATION_WAIT = 120  # Wait time for interference to stabilize
COOLDOWN_WAIT = 60  # Wait time between runs

# Fixed output directory (no timestamp)
OUTPUT_DIR = Path("part2/parsec_results")
RESULTS_CSV = OUTPUT_DIR / "all_results.csv"

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Utility functions
def run_cmd(cmd):
    """Run a shell command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed: {cmd}")
        print(f"Error: {result.stderr}")
    return result.stdout.strip()


def wait_for_pod_ready(pod_name, timeout=300):
    """Wait until pod is in Ready state with timeout."""
    print(f"Waiting for pod {pod_name} to be ready...")
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        status = run_cmd(f"kubectl get pod {pod_name} -o jsonpath='{{.status.phase}}'")
        if status == "Running":
            ready = run_cmd(
                f"kubectl get pod {pod_name} -o jsonpath='{{..status.conditions[?(@.type==\"Ready\")].status}}'"
            )
            if ready == "True":
                print(f"Pod {pod_name} is ready!")
                return True
        print(
            f"Pod status: {status}, waiting 5s... (timeout in {int(timeout - (time.time() - start_time))}s)"
        )
        time.sleep(5)
    print(f"ERROR: Pod {pod_name} not ready after {timeout}s")
    return False


def wait_for_job_completion(job_name, timeout=1800):
    """Wait until job has completed with timeout."""
    print(f"Waiting for job {job_name} to complete...")
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        status = run_cmd(
            f"kubectl get job {job_name} -o jsonpath='{{.status.succeeded}}'"
        )
        if status == "1":
            print(f"Job {job_name} completed successfully!")
            return True

        # Check if the job failed
        failed = run_cmd(f"kubectl get job {job_name} -o jsonpath='{{.status.failed}}'")
        if failed and int(failed) > 0:
            print(f"Job {job_name} failed!")
            return False

        print(
            f"Job still running, waiting 5s... (timeout in {int(timeout - (time.time() - start_time))}s)"
        )
        time.sleep(5)

    print(f"ERROR: Job {job_name} did not complete after {timeout}s")
    return False


def extract_execution_time(log_content):
    """Extract execution time from PARSEC log output."""
    for line in log_content.split("\n"):
        if line.strip().startswith("real"):
            parts = line.split()
            if len(parts) >= 2:
                time_str = parts[1]  # Format like "0m6.713s"
                try:
                    if "m" in time_str and "s" in time_str:
                        # Parse "0m6.713s" format
                        minutes, rest = time_str.split("m")
                        seconds = rest.replace("s", "")
                        total_seconds = (float(minutes) * 60) + float(seconds)
                        return total_seconds
                    else:
                        # Just in case we have a simpler format
                        return float(time_str.replace("s", ""))
                except ValueError:
                    pass
        # Alternative format - ROI timing
        if "ROI time:" in line:
            parts = line.split(":")
            if len(parts) >= 2:
                try:
                    return float(parts[1].strip())
                except ValueError:
                    pass
    # If we couldn't find the execution time
    print("Warning: Could not extract execution time from log")
    return None


def apply_interference(interference_type):
    """Apply interference and verify it's running."""
    print(f"Applying {interference_type} interference...")

    # First check if YAML file exists
    yaml_path = f"interference/ibench-{interference_type}.yaml"
    if not os.path.exists(yaml_path):
        print(f"ERROR: Interference file {yaml_path} not found")
        return None

    # Apply the interference
    result = run_cmd(f"kubectl create -f {yaml_path}")
    print(f"kubectl create result: {result}")

    # Wait for pod to be created (may take a moment)
    print("Waiting for pod to be created...")
    for attempt in range(1, 13):  # Try for up to 60 seconds
        time.sleep(5)
        # List all pods to debug
        all_pods = run_cmd("kubectl get pods")
        print(f"Current pods:\n{all_pods}")

        # Look for the pod by name instead of label
        pod_name = f"ibench-{interference_type}"
        pod_exists = run_cmd(f"kubectl get pod {pod_name}")

        if pod_exists and "not found" not in pod_exists:
            print(f"Found interference pod: {pod_name}")
            return pod_name

        print(f"Attempt {attempt}/12: Pod not found yet, waiting...")

    print(f"ERROR: Interference pod for {interference_type} not found after 60 seconds")
    return None


def append_result_to_csv(result_dict):
    """Append a single result to the results CSV file."""
    df = pd.DataFrame([result_dict])

    # If file exists, append without header, otherwise write with header
    if os.path.exists(RESULTS_CSV):
        df.to_csv(RESULTS_CSV, mode="a", header=False, index=False)
    else:
        df.to_csv(RESULTS_CSV, mode="w", header=True, index=False)

    print(f"Result appended to {RESULTS_CSV}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run PARSEC interference experiments")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a single test case only",
    )
    parser.add_argument(
        "--workload",
        choices=WORKLOADS,
        default="blackscholes",
        help="Specific workload to test (used with --test)",
    )
    parser.add_argument(
        "--interference",
        choices=INTERFERENCE_TYPES,
        default="none",
        help="Specific interference to test (used with --test)",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=3,
        help="Number of repetitions for test mode (default: 1)",
    )
    return parser.parse_args()


def main():
    """Main execution flow."""
    args = parse_arguments()
    print(
        f"Starting PARSEC interference experiments at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(f"Logs will be saved to {OUTPUT_DIR}")
    print(f"Results will be appended to {RESULTS_CSV}")

    # Check if parsec node is labeled
    parsec_nodes = run_cmd("kubectl get nodes -l cca-project-nodetype=parsec")
    if not parsec_nodes:
        print("Error: No nodes labeled with cca-project-nodetype=parsec")
        print(
            "Please label a node with: kubectl label nodes <node-name> cca-project-nodetype=parsec"
        )
        return

    # For test mode, override workloads and interference types
    if args.test:
        print(
            f"TEST MODE: Running only {args.workload} with {args.interference} interference for {args.repetitions} repetition(s)"
        )
        test_workloads = [args.workload]
        test_interference = [args.interference]
        test_reps = args.repetitions
    else:
        test_workloads = WORKLOADS
        test_interference = INTERFERENCE_TYPES
        test_reps = REPETITIONS

    # Calculate total experiments
    total_experiments = len(test_workloads) * len(test_interference) * test_reps
    current_experiment = 0

    # Run experiments
    for workload in test_workloads:
        for interference in test_interference:
            for rep in range(1, test_reps + 1):
                current_experiment += 1
                progress_pct = (current_experiment / total_experiments) * 100

                print(f"\n{'='*80}")
                print(
                    f"Progress: {progress_pct:.1f}% - Run {current_experiment}/{total_experiments}"
                )
                print(
                    f"Running {workload} with {interference} interference (repetition {rep})"
                )
                print(f"{'='*80}")

                # Timestamp for this run
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                log_file = (
                    OUTPUT_DIR / f"{workload}_{interference}_rep{rep}_{timestamp}.log"
                )

                # Apply interference if not 'none'
                ibench_pod_name = None
                if interference != "none":
                    ibench_pod_name = apply_interference(interference)
                    if ibench_pod_name:
                        # Wait for interference pod to be ready
                        if wait_for_pod_ready(ibench_pod_name):
                            # Wait for interference to stabilize
                            print(
                                f"Waiting {STABILIZATION_WAIT}s for interference to stabilize..."
                            )
                            time.sleep(STABILIZATION_WAIT)
                        else:
                            print(
                                "WARNING: Interference pod never became ready, continuing anyway..."
                            )
                    else:
                        print("ERROR: Could not apply interference, skipping this run")
                        continue

                # Launch PARSEC workload
                print(f"Launching {workload} workload...")
                run_cmd(
                    f"kubectl create -f parsec-benchmarks/part2a/parsec-{workload}.yaml"
                )

                # Wait for job to complete
                if not wait_for_job_completion(f"parsec-{workload}"):
                    print(
                        f"ERROR: Job parsec-{workload} failed or timed out, skipping log collection"
                    )
                    continue

                # Get pod name to collect logs
                workload_pod = run_cmd(
                    f"kubectl get pods -l job-name=parsec-{workload} -o jsonpath='{{.items[0].metadata.name}}'"
                )
                if not workload_pod:
                    print(f"ERROR: Could not find pod for job parsec-{workload}")
                    continue

                # Collect logs
                print(f"Collecting logs from {workload_pod}...")
                logs = run_cmd(f"kubectl logs {workload_pod}")

                # Save logs to file
                with open(log_file, "w") as f:
                    f.write(logs)

                # Extract execution time and append to results CSV
                exec_time = extract_execution_time(logs)
                if exec_time is not None:
                    result = {
                        "workload": workload,
                        "interference": interference,
                        "repetition": rep,
                        "execution_time": exec_time,
                        "timestamp": timestamp,
                    }
                    append_result_to_csv(result)
                else:
                    print(f"WARNING: Could not extract execution time from logs")

                # Cleanup
                print("Cleaning up...")
                run_cmd(f"kubectl delete job parsec-{workload}")
                if ibench_pod_name:
                    run_cmd(f"kubectl delete pod {ibench_pod_name}")

                # Cooldown period
                print(f"Cooldown period: waiting {COOLDOWN_WAIT}s...")
                time.sleep(COOLDOWN_WAIT)

    print("\nAll experiments completed!")
    print(f"Results saved to {RESULTS_CSV}")


if __name__ == "__main__":
    main()
