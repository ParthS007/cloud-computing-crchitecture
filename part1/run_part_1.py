"""Script for running Part 1 of the Cloud Computing Architecture project."""

import enum
import os
import subprocess
import argparse
import time
from kubernetes import client, config

MCPERF_CLIENT_CMD = "cd memcache-perf && ./mcperf -T 8 -A"
MCPERF_LOAD_DATA_CMD = "cd memcache-perf && ./mcperf -s {MEMCACHED_IP} --loadonly"
MCPERF_BENCHMARK_CMD_TEMPLATE = "cd memcache-perf && ./mcperf -s {MEMCACHED_IP} -a {INTERNAL_AGENT_IP} --noload -T 8 -C 8 -D 4 -Q 1000 -c 8 -t 5 -w 2 --scan 5000:80000:5000"


ZONE = "europe-west1-b"

# Get the absolute path to the install script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INSTALL_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "install_mcperf.sh")


class InterferencePattern(enum.Enum):
    """Enum for the different interference patterns."""

    NONE = "none"
    CPU = "cpu"
    L1D = "l1d"
    L1I = "l1i"
    L2 = "l2"
    LLC = "llc"
    MEMBW = "membw"


class Mode(enum.Enum):
    """Enum for the different modes of operation."""

    INSTALL = "install"
    CLIENT = "client"
    BENCHMARK = "benchmark"


# Initialize Kubernetes client
config.load_kube_config()
kubernetes_client = client.CoreV1Api()


def install_mcperf(node_name_prefix: str):
    """Install and configure mcperf with the given name prefix."""
    # Find the node with the given prefix
    found_node = None
    for node in kubernetes_client.list_node().items:
        if node.metadata.name.startswith(node_name_prefix):
            found_node = node
            break
    if not found_node:
        raise ValueError(f"Node with prefix {node_name_prefix} not found")

    if not os.path.exists(INSTALL_SCRIPT_PATH):
        raise FileNotFoundError(f"Install script not found at {INSTALL_SCRIPT_PATH}")

    print(f"Copying mcperf-install script to {found_node.metadata.name}")
    # Copy the install script to the VM
    process = subprocess.Popen(
        f"gcloud compute scp --ssh-key-file=~/.ssh/cloud-computing {INSTALL_SCRIPT_PATH} ubuntu@{found_node.metadata.name}:~/ --zone {ZONE}",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )
    for line in process.stdout:
        print(line, end="")
    process.wait()
    if process.returncode != 0:
        print(f"Error copying script: {process.stderr.read()}")

    # Make the script executable and run it
    print(f"Running mcperf-install script on {found_node.metadata.name}")
    process = subprocess.Popen(
        f"gcloud compute ssh --ssh-key-file=~/.ssh/cloud-computing ubuntu@{found_node.metadata.name} --zone {ZONE} --command 'chmod +x ~/install_mcperf.sh && ~/install_mcperf.sh'",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )
    for line in process.stdout:
        print(line, end="")
    process.wait()
    if process.returncode != 0:
        print(f"Error running script: {process.stderr.read()}")
    print(f"Finished running mcperf-install script on {found_node.metadata.name}")


def run_memcached_client(node_name_prefix: str):
    """Start the memcached client on the given node."""
    # get the node name
    found_node = None
    for node in kubernetes_client.list_node().items:
        if node.metadata.name.startswith(node_name_prefix):
            found_node = node
            break
    if not found_node:
        raise ValueError(f"Node with prefix {node_name_prefix} not found")

    print(f"Running memcached client on {found_node.metadata.name}")

    command = MCPERF_CLIENT_CMD
    process = subprocess.Popen(
        f"gcloud compute ssh --ssh-key-file=~/.ssh/cloud-computing ubuntu@{found_node.metadata.name} --zone {ZONE} --command '{command}'",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )
    for line in process.stdout:
        print(line, end="")
    process.wait()
    if process.returncode != 0:
        print(f"Error running script: {process.stderr.read()}")
    print(f"\n\nFinished running memcached client on {found_node.metadata.name}")


def load_memcached_data(node_name_prefix: str, memcached_ip: str):
    """Load the memcached data on the given node."""
    print(f"Loading memcached data on {node_name_prefix}")

    # get the node name
    found_node = kubernetes_client.list_node()
    for node in found_node.items:
        if node.metadata.name.startswith(node_name_prefix):
            found_node = node
            break
    if not found_node:
        raise ValueError(f"Node with prefix {node_name_prefix} not found")

    command = MCPERF_LOAD_DATA_CMD.format(MEMCACHED_IP=memcached_ip)

    process = subprocess.Popen(
        f"gcloud compute ssh --ssh-key-file=~/.ssh/cloud-computing ubuntu@{found_node.metadata.name} --zone {ZONE} --command '{command}'",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )
    for line in process.stdout:
        print(line, end="")
    process.wait()
    if process.returncode != 0:
        print(f"Error running script: {process.stderr.read()}")
    print(f"Finished loading memcached data on {found_node.metadata.name}")


def run_memcached_benchmark(
    node_name_prefix: str, memcached_ip: str, internal_agent_ip: str, log_file: str
):
    """Run the memcached benchmark on the given node."""
    # get the node name
    found_node = None
    for node in kubernetes_client.list_node().items:
        if node.metadata.name.startswith(node_name_prefix):
            found_node = node
            break
    if not found_node:
        raise ValueError(f"Node with prefix {node_name_prefix} not found")

    print(f"Running memcached benchmark on {found_node.metadata.name}")
    # create log file and directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    command = MCPERF_BENCHMARK_CMD_TEMPLATE.format(
        MEMCACHED_IP=memcached_ip, INTERNAL_AGENT_IP=internal_agent_ip
    )

    # Run the benchmark and capture output
    process = subprocess.Popen(
        f"gcloud compute ssh --ssh-key-file=~/.ssh/cloud-computing ubuntu@{found_node.metadata.name} --zone {ZONE} --command '{command}'",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    # Create output file
    output_file = log_file

    # Print output in real-time and save to file
    with open(output_file, "w") as f:
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line, end="")  # Print to console
                f.write(line)  # Save to file
                f.flush()  # Ensure it's written immediately

    # Wait for the process to complete
    process.wait()

    # Check for errors
    if process.returncode != 0:
        error_output = process.stderr.read()
        print(f"Error running script: {error_output}")
        with open(output_file, "a") as f:
            f.write(f"\nError output:\n{error_output}")

    print(f"\n\nFinished running memcached benchmark on {found_node.metadata.name}")
    print(f"Results have been saved to {output_file}")


def get_internal_agent_ip():
    """Get the internal agent IP address on the client-agent node."""
    nodes = kubernetes_client.list_node()
    for node in nodes.items:
        if node.metadata.name.startswith("client-agent"):
            return node.status.addresses[0].address
    raise ValueError("Client-agent node not found")


def start_interference(interference_pattern: InterferencePattern):
    """Start the interference on the given node."""
    if interference_pattern == InterferencePattern.NONE:
        return
    elif interference_pattern == InterferencePattern.CPU:
        subprocess.run(
            ["kubectl", "create", "-f", "../interference/ibench-cpu.yaml"], check=True
        )
    elif interference_pattern == InterferencePattern.L1D:
        subprocess.run(
            ["kubectl", "create", "-f", "../interference/ibench-l1d.yaml"], check=True
        )
    elif interference_pattern == InterferencePattern.L1I:
        subprocess.run(
            ["kubectl", "create", "-f", "../interference/ibench-l1i.yaml"], check=True
        )
    elif interference_pattern == InterferencePattern.L2:
        subprocess.run(
            ["kubectl", "create", "-f", "../interference/ibench-l2.yaml"], check=True
        )
    elif interference_pattern == InterferencePattern.LLC:
        subprocess.run(
            ["kubectl", "create", "-f", "../interference/ibench-llc.yaml"], check=True
        )
    elif interference_pattern == InterferencePattern.MEMBW:
        subprocess.run(
            ["kubectl", "create", "-f", "../interference/ibench-membw.yaml"], check=True
        )
    print(f"Waiting for pod to start")
    # spin while pod is starting
    while True:
        pods = subprocess.run(
            [
                "kubectl",
                "get",
                "pods",
                "-o",
                "jsonpath={.items[?(@.metadata.name=='ibench-"
                + interference_pattern.value
                + "')].status.phase}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        if pods.stdout == "Running":
            break
        print(f"Pod status: {pods.stdout}")
        time.sleep(1)
    print(f"Pod started with {interference_pattern} interference")
    time.sleep(10)
    print("Waiting for 10 seconds before starting benchmark")


def stop_interference(interference_pattern: InterferencePattern):
    """Stop the interference on the given node."""
    if interference_pattern == InterferencePattern.NONE:
        return
    elif interference_pattern == InterferencePattern.CPU:
        subprocess.run(
            ["kubectl", "delete", "-f", "../interference/ibench-cpu.yaml"], check=True
        )
    elif interference_pattern == InterferencePattern.L1D:
        subprocess.run(
            ["kubectl", "delete", "-f", "../interference/ibench-l1d.yaml"], check=True
        )
    elif interference_pattern == InterferencePattern.L1I:
        subprocess.run(
            ["kubectl", "delete", "-f", "../interference/ibench-l1i.yaml"], check=True
        )
    elif interference_pattern == InterferencePattern.L2:
        subprocess.run(
            ["kubectl", "delete", "-f", "../interference/ibench-l2.yaml"], check=True
        )
    elif interference_pattern == InterferencePattern.LLC:
        subprocess.run(
            ["kubectl", "delete", "-f", "../interference/ibench-llc.yaml"], check=True
        )
    elif interference_pattern == InterferencePattern.MEMBW:
        subprocess.run(
            ["kubectl", "delete", "-f", "../interference/ibench-membw.yaml"], check=True
        )
    print(f"Waiting for pod to stop")
    # spin while pod is stopping
    while True:
        pods = subprocess.run(
            [
                "kubectl",
                "get",
                "pods",
                "-o",
                "jsonpath={.items[?(@.metadata.name=='ibench-"
                + interference_pattern.value
                + "')].status.phase}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        if pods.stdout == "Terminating":
            print(f"Pod status: {pods.stdout}")
            time.sleep(1)
        else:
            break
    print(f"Pod stopped with {interference_pattern.value} interference")
    print(f"Waiting for 10 seconds before starting next benchmark")
    time.sleep(10)


def parse_mode(mode_str: str) -> Mode:
    """Parse the mode string into a Mode enum value."""
    mode_str = mode_str.lower()
    if mode_str in ["i", "install", "1"]:
        return Mode.INSTALL
    elif mode_str in ["c", "client", "2"]:
        return Mode.CLIENT
    elif mode_str in ["b", "benchmark", "3"]:
        return Mode.BENCHMARK
    else:
        raise ValueError(
            f"Invalid mode: {mode_str}. Must be one of: i/install/1, c/client/2, b/benchmark/3"
        )


def main():
    """Main entry point for running Part 1 of the project."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Run Part 1 of the Cloud Computing Architecture project"
    )
    parser.add_argument(
        "mode",
        type=str,
        help="Mode of operation: i/install/1, c/client/2, b/benchmark/3",
    )
    parser.add_argument(
        "--memcached-ip",
        type=str,
        help="IP address of memcached server",
        default="100.96.3.2",
    )
    args = parser.parse_args()

    try:
        mode = parse_mode(args.mode)
        memcached_ip = "100.96.2.4"  # Hardcoded for now

        internal_agent_ip = get_internal_agent_ip()

        if mode == Mode.INSTALL:
            print("Installing mcperf on client-agent...")
            install_mcperf("client-agent")
            print("Installing mcperf on client-measure...")
            install_mcperf("client-measure")
            print("Loading data into memcached...")
            load_memcached_data("client-measure", memcached_ip)

        elif mode == Mode.CLIENT:
            print("Starting memcached client...")
            run_memcached_client("client-agent")

        elif mode == Mode.BENCHMARK:
            for interference_pattern in InterferencePattern:
                start_interference(interference_pattern)
                for i in range(0, 3):
                    run_memcached_benchmark(
                        "client-measure",
                        memcached_ip,
                        internal_agent_ip,
                        f"logs/benchmark_results_{interference_pattern.value}_{i}.txt",
                    )
                    print("waiting 60 seconds before next benchmark")
                    time.sleep(60)
                stop_interference(interference_pattern)
            print(
                f"\nFinished memcached benchmark with {interference_pattern.value} interference\n\n"
            )

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    # Run the main function
    main()
