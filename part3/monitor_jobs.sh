#!/bin/bash

run_number=$1
results_dir="part3/logs/run_${run_number}"
job_log_file="${results_dir}/job_timestamps_${run_number}.txt"

# Initialize log file
echo "======================" >>$job_log_file
echo "Format: job_name, status, timestamp" >>$job_log_file

# List of all parsec jobs to monitor
jobs=("parsec-blackscholes" "parsec-canneal" "parsec-dedup" "parsec-ferret" "parsec-freqmine" "parsec-radix" "parsec-vips")

# Initialize tracking variables
for job in "${jobs[@]}"; do
    var_name=$(echo "$job" | tr '-' '_')
    eval "${var_name}_started=0"
    eval "${var_name}_completed=0"
done

# Function to log timestamp for a job event
log_job_event() {
    local job_name=$1
    local status=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "${job_name}, ${status}, ${timestamp}" >>$job_log_file
}

# Monitor loop - keep checking for job status changes
while true; do
    for job in "${jobs[@]}"; do
        var_name=$(echo "$job" | tr '-' '_')

        # Check if job exists
        if kubectl get job $job &>/dev/null; then
            # Check if job has started (active condition)
            started_var="${var_name}_started"
            if [[ "$(eval echo \$$started_var)" == "0" ]]; then
                active=$(kubectl get job $job -o jsonpath='{.status.active}')
                if [[ "$active" != "" && "$active" != "0" ]]; then
                    log_job_event $job "STARTED"
                    eval "${var_name}_started=1"
                fi
            fi

            # Check if job has completed
            completed_var="${var_name}_completed"
            if [[ "$(eval echo \$$completed_var)" == "0" ]]; then
                complete=$(kubectl get job $job -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}')
                if [[ "$complete" == "True" ]]; then
                    log_job_event $job "COMPLETED"
                    eval "${var_name}_completed=1"
                fi
            fi
        fi
    done

    # Check if all jobs have completed
    all_completed=true
    for job in "${jobs[@]}"; do
        var_name=$(echo "$job" | tr '-' '_')
        completed_var="${var_name}_completed"
        if [[ "$(eval echo \$$completed_var)" == "0" ]]; then
            all_completed=false
            break
        fi
    done

    # Exit if all jobs have completed
    if $all_completed; then
        echo "All jobs have completed. Monitoring finished." >>$job_log_file
        break
    fi

    # Sleep to avoid excessive polling
    sleep 5
done
