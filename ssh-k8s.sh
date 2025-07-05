#!/bin/bash

# Get all nodes and store them in an array
nodes=($(kubectl get nodes -o wide | grep -v NAME | awk '{print $1}'))

# Check if there are any nodes
if [ ${#nodes[@]} -eq 0 ]; then
    echo "No nodes found!"
    exit 1
fi

# Display available nodes with numbers
echo "Available nodes:"
for i in "${!nodes[@]}"; do
    echo "$((i+1)). ${nodes[$i]}"
done

# Prompt for selection
echo -n "Select a node number to connect to: "
read selection

# Validate input
if ! [[ "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 1 ] || [ "$selection" -gt ${#nodes[@]} ]; then
    echo "Invalid selection!"
    exit 1
fi

# Get the selected node name
selected_node=${nodes[$((selection-1))]}

# Connect to the selected node
echo "Connecting to $selected_node..."
gcloud compute ssh --ssh-key-file ~/.ssh/cloud-computing ubuntu@$selected_node --zone europe-west1-b 