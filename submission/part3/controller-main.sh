#!/bin/bash

echo "Starting all node controllers in parallel..."
# Start all node controllers in background
./part3/controller-node-a.sh &
./part3/controller-node-b.sh &
./part3/controller-node-c.sh &
./part3/controller-node-d.sh &

# Wait for all background processes to complete
wait

echo "All jobs completed."
