#!/bin/bash

set -e
SSH_KEY_FILE="$HOME/.ssh/cloud-computing"
ZONE="europe-west1-b"

# Function to get node wildcard name
get_node_name() {
    local prefix=$1
    kubectl get nodes | grep "$prefix" | awk '{print $1}' | head -1
}

# Function to install mcperf on a node
install_mcperf_on_node() {
    local node_name=$1
    local external_ip=$(kubectl get node $node_name -o jsonpath='{.status.addresses[?(@.type=="ExternalIP")].address}')

    if [[ -z "$external_ip" ]]; then
        echo "ERROR: Could not get external IP for node $node_name"
        return 1
    fi

    echo "Installing mcperf on $node_name ($external_ip)..."

    gcloud compute ssh --ssh-key-file $SSH_KEY_FILE ubuntu@$node_name --zone $ZONE -- "
        echo 'Installing mcperf dependencies...'
        sudo sed -i 's/^Types: deb\$/Types: deb deb-src/' /etc/apt/sources.list.d/ubuntu.sources
        sudo apt-get update
        sudo apt-get install libevent-dev libzmq3-dev git make g++ --yes
        sudo apt-get build-dep memcached --yes
        
        echo 'Cloning and building mcperf...'
        if [ -d 'memcache-perf-dynamic' ]; then
            echo 'Directory exists, updating...'
            cd memcache-perf-dynamic
            git pull
        else
            git clone https://github.com/eth-easl/memcache-perf-dynamic.git
            cd memcache-perf-dynamic
        fi
        
        make
        echo 'mcperf installation completed on $node_name'
    "

    return $?
}

echo "=== Installing mcperf on client nodes ==="

# Get node names
CLIENT_AGENT_A=$(get_node_name "client-agent-a")
CLIENT_AGENT_B=$(get_node_name "client-agent-b")
CLIENT_MEASURE=$(get_node_name "client-measure")

if [[ -z "$CLIENT_AGENT_A" || -z "$CLIENT_AGENT_B" || -z "$CLIENT_MEASURE" ]]; then
    echo "ERROR: Could not find all required nodes"
    echo "Found: Agent A: $CLIENT_AGENT_A, Agent B: $CLIENT_AGENT_B, Measure: $CLIENT_MEASURE"
    exit 1
fi

# Install mcperf on all three nodes
install_mcperf_on_node $CLIENT_AGENT_A || {
    echo "Failed to install on $CLIENT_AGENT_A"
    exit 1
}
install_mcperf_on_node $CLIENT_AGENT_B || {
    echo "Failed to install on $CLIENT_AGENT_B"
    exit 1
}
install_mcperf_on_node $CLIENT_MEASURE || {
    echo "Failed to install on $CLIENT_MEASURE"
    exit 1
}

echo "=== mcperf installation completed on all nodes ==="
