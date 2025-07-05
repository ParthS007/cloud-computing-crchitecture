#!/bin/bash

# Exit on errors, but allow us to clean up first
set -e

# Check for run number argument
if [ $# -ne 1 ]; then
    echo "Usage: $0 <run_number>"
    echo "Example: $0 2   # Run experiment #2"
    exit 1
fi

run_number=$1

# Constants
RESULTS_DIR="part3/logs/run_${run_number}"
LOG_FILE="$RESULTS_DIR/experiment_${run_number}_log.txt"
SSH_KEY_FILE="$HOME/.ssh/cloud-computing"
ZONE="europe-west1-b"


# Create results directory
mkdir -p $RESULTS_DIR

# Start logging
exec > >(tee -a $LOG_FILE) 2>&1
echo "=== Starting experiment run #${run_number} at $(date) ==="

# Function to check if mcperf is installed on a node
check_mcperf_installed() {
    local node_name=$1
    gcloud compute ssh --ssh-key-file $SSH_KEY_FILE ubuntu@$node_name --zone $ZONE -- \
        "[ -f ~/memcache-perf-dynamic/mcperf ] && echo 'mcperf found' || echo 'mcperf not found'" |
        grep -q "mcperf found"
    return $?
}

# Check mcperf installation before proceeding
verify_installations() {
    CLIENT_AGENT_A=$(get_node_name "client-agent-a")
    CLIENT_AGENT_B=$(get_node_name "client-agent-b")
    CLIENT_MEASURE=$(get_node_name "client-measure")

    echo "Verifying mcperf installations..."
    local all_installed=true

    if ! check_mcperf_installed $CLIENT_AGENT_A; then
        echo "WARNING: mcperf not found on $CLIENT_AGENT_A"
        all_installed=false
    fi

    if ! check_mcperf_installed $CLIENT_AGENT_B; then
        echo "WARNING: mcperf not found on $CLIENT_AGENT_B"
        all_installed=false
    fi

    if ! check_mcperf_installed $CLIENT_MEASURE; then
        echo "WARNING: mcperf not found on $CLIENT_MEASURE"
        all_installed=false
    fi

    if [ "$all_installed" = false ]; then
        echo "mcperf is not installed on all required nodes."
        echo "Please run ./part3/install_mcperf.sh before proceeding."
        return 1
    fi

    echo "mcperf is installed on all required nodes."
    return 0
}

# Cleanup function
cleanup() {
    echo "Cleaning up resources..."
    kill $(jobs -p) 2>/dev/null || true
    kubectl delete jobs --all --ignore-not-found
    kubectl delete pod memcached --ignore-not-found
    echo "Cleanup completed"
}

# Set trap for graceful exit
trap cleanup EXIT INT TERM

# Function to get node wildcard name (handles dynamic node names)
get_node_name() {
    local prefix=$1
    kubectl get nodes | grep "$prefix" | awk '{print $1}' | head -1
}

# Function to check if all parsec jobs are completed
check_jobs_completed() {
    local expected_jobs=("parsec-blackscholes" "parsec-canneal" "parsec-dedup" "parsec-ferret" "parsec-freqmine" "parsec-radix" "parsec-vips")

    for job in "${expected_jobs[@]}"; do
        if ! kubectl get job "$job" -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}' 2>/dev/null | grep -q "True"; then
            return 1
        fi
    done
    return 0
}

# Function to run a single experiment
run_experiment() {
    local run_number=$1
    echo "=========================================="
    echo "Starting Run #$run_number - $(date)"
    echo "=========================================="

    # 1. Deploy memcached
    echo "Starting memcached on node-d-4core..."
    kubectl apply -f memcache-t1-cpuset.yaml

    echo "Waiting for memcached to be ready..."
    kubectl wait --for=condition=ready pod/memcached --timeout=5m || {
        echo "ERROR: Memcached failed to start within timeout"
        return 1
    }

    # Get IP addresses
    MEMCACHED_IP=$(kubectl get pod memcached -o jsonpath='{.status.podIP}')
    if [[ -z "$MEMCACHED_IP" ]]; then
        echo "ERROR: Could not get memcached IP"
        return 1
    fi

    # Get node names
    CLIENT_AGENT_A=$(get_node_name "client-agent-a")
    CLIENT_AGENT_B=$(get_node_name "client-agent-b")
    CLIENT_MEASURE=$(get_node_name "client-measure")

    if [[ -z "$CLIENT_AGENT_A" || -z "$CLIENT_AGENT_B" || -z "$CLIENT_MEASURE" ]]; then
        echo "ERROR: Could not find all required nodes"
        echo "Found: Agent A: $CLIENT_AGENT_A, Agent B: $CLIENT_AGENT_B, Measure: $CLIENT_MEASURE"
        return 1
    fi

    # Get agent IPs using node names
    AGENT_A_IP=$(kubectl get node $CLIENT_AGENT_A -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}')
    AGENT_B_IP=$(kubectl get node $CLIENT_AGENT_B -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}')

    if [[ -z "$AGENT_A_IP" || -z "$AGENT_B_IP" ]]; then
        echo "ERROR: Could not get agent IP addresses"
        return 1
    fi

    echo "Memcached IP: $MEMCACHED_IP"
    echo "Agent A: $CLIENT_AGENT_A ($AGENT_A_IP)"
    echo "Agent B: $CLIENT_AGENT_B ($AGENT_B_IP)"
    echo "Measure node: $CLIENT_MEASURE"

    # 2. Start mcperf load generators on agents (in background)
    echo "Starting mcperf load generators..."
    echo "Starting job timestamp monitor..."
    chmod +x ./part3/monitor_jobs.sh
    ./part3/monitor_jobs.sh $run_number &
    JOB_MONITOR_PID=$!

    # Agent A load generator
    echo "Starting agent A load generator..."
    gcloud compute ssh --ssh-key-file $SSH_KEY_FILE ubuntu@$CLIENT_AGENT_A \
        --zone $ZONE -- "cd memcache-perf-dynamic && ./mcperf -T 2 -A" &
    AGENT_A_PID=$!

    # Agent B load generator
    echo "Starting agent B load generator..."
    gcloud compute ssh --ssh-key-file $SSH_KEY_FILE ubuntu@$CLIENT_AGENT_B \
        --zone $ZONE -- "cd memcache-perf-dynamic && ./mcperf -T 4 -A" &
    AGENT_B_PID=$!

    # Wait for load generators to start
    echo "Waiting for load generators to initialize (10s)..."
    sleep 10

    # 3. Start mcperf measurement (in foreground to capture output)
    echo "Starting mcperf measurement..."
    gcloud compute ssh --ssh-key-file $SSH_KEY_FILE ubuntu@$CLIENT_MEASURE \
        --zone $ZONE -- "cd memcache-perf-dynamic && \
        ./mcperf -s $MEMCACHED_IP --loadonly && \
        ./mcperf -s $MEMCACHED_IP -a $AGENT_A_IP -a $AGENT_B_IP \
        --noload -T 6 -C 4 -D 4 -Q 1000 -c 4 -t 10 \
        --scan 30000:30500:5" >$RESULTS_DIR/mcperf_${run_number}.txt &
    MCPERF_PID=$!

    # 4. Start controller scripts to run PARSEC jobs
    echo "Starting PARSEC jobs via controller scripts..."
    ./part3/controller-main.sh

    # Wait for mcperf to finish collecting data
    echo "Waiting for measurement to complete..."
    wait $MCPERF_PID || {
        echo "WARNING: mcperf measurement process exited with non-zero status"
    }

    # Wait for all jobs to complete (with timeout)
    echo "Waiting for all PARSEC jobs to complete..."
    local timeout=7200 # 2 hours
    local start_time=$(date +%s)
    local current_time

    while ! check_jobs_completed; do
        current_time=$(date +%s)
        if ((current_time - start_time > timeout)); then
            echo "WARNING: Not all jobs completed within timeout. Continuing anyway."
            break
        fi
        echo "Still waiting for jobs to complete... ($(((current_time - start_time) / 60)) minutes elapsed)"
        sleep 30
    done

    # 6. Collect pod data
    echo "Collecting pod data..."
    kubectl get pods -o json >$RESULTS_DIR/pods_${run_number}.json

    # 7. Process execution times (for verification)
    echo "Processing execution times..."
    python3 get_time.py $RESULTS_DIR/pods_${run_number}.json >$RESULTS_DIR/times_${run_number}.txt || {
        echo "WARNING: Error processing execution times. This might be expected if not all jobs completed."
    }

    # 8. Clean up
    echo "Cleaning up run #${run_number}..."
    # Kill background processes
    kill $AGENT_A_PID $AGENT_B_PID 2>/dev/null || true

    # Delete Kubernetes resources
    kubectl delete jobs --all
    kubectl delete pod memcached

    echo "Run #$run_number completed at $(date)"
    echo "Waiting 60 seconds before next run..."
    sleep 60
}

# Main execution
echo "Starting experiment run #${run_number}"

# Verify installations
verify_installations || {
    echo "ERROR: Required mcperf is not installed. Please run ./part3/install_mcperf.sh first."
    exit 1
}

# Ensure controller script exists and is executable
if [ ! -f "./part3/controller-main.sh" ]; then
    echo "ERROR: Controller script not found at ./part3/controller-main.sh"
    exit 1
fi

if [ ! -x "./part3/controller-main.sh" ]; then
    echo "Making controller script executable..."
    chmod +x ./part3/controller-main.sh
fi

# Run single experiment
run_experiment $run_number || {
    echo "ERROR: Run #$run_number failed."
    exit 1
}

echo "Experiment run #${run_number} completed!"
echo "Results are stored in the $RESULTS_DIR directory."

# Verify all required files exist
echo "Verifying results..."
exit_code=0
if [ ! -f "$RESULTS_DIR/pods_${run_number}.json" ]; then
    echo "WARNING: pods_${run_number}.json is missing"
    exit_code=1
fi

if [ ! -f "$RESULTS_DIR/mcperf_${run_number}.txt" ]; then
    echo "WARNING: mcperf_${run_number}.txt is missing"
    exit_code=1
fi

if [ $exit_code -eq 0 ]; then
    echo "All required files for run #${run_number} are present."
    echo ""
    echo "To run the next experiment:"
    echo "  ./part3_experiment.sh $((run_number + 1))"
    echo ""
else
    echo "Some files are missing. Please check the logs."
fi

echo "=== Experiment #${run_number} completed at $(date) ==="
exit $exit_code
