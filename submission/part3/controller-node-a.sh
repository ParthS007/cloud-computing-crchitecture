#!/bin/bash

echo "Starting controller for node-a-2core (canneal)..."

run_job() {
  local job_name=$1
  local yaml_file=$2
  local max_attempts=3
  local attempt=1

  while [ $attempt -le $max_attempts ]; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting $job_name (attempt $attempt)..."
    kubectl apply -f $yaml_file

    # Check if job completes successfully
    if kubectl wait --for=condition=complete job/$job_name --timeout=2h; then
      echo "$(date '+%Y-%m-%d %H:%M:%S') - $job_name completed successfully."
      return 0
    else
      echo "$(date '+%Y-%m-%d %H:%M:%S') - $job_name failed on attempt $attempt."
      kubectl delete job $job_name --ignore-not-found
      attempt=$((attempt + 1))
      sleep 10
    fi
  done

  echo "$(date '+%Y-%m-%d %H:%M:%S') - Failed to run $job_name after $max_attempts attempts."
  return 1
}

# Run canneal
run_job parsec-canneal part3/parsec-canneal.yaml
