# Part 3: Co-scheduling Latency-Critical and Batch Applications

This part combines the latency-critical **memcached** application from Part 1 and the seven batch applications from Part 2 in a heterogeneous cluster environment. Our scheduling policy optimizes resource usage while minimizing interference.

## Cluster Configuration

- 1 VM for the Kubernetes master
- 3 VMs for mcperf clients (2 agents and 1 measure machine)
- 4 heterogeneous worker VMs:
  - **node-a-2core**: `e2-highmem-2` (2 cores, high memory)
  - **node-b-2core**: `n2-highcpu-2` (2 cores, high CPU)
  - **node-c-4core**: `c3-highcpu-4` (4 cores, high CPU)
  - **node-d-4core**: `n2-standard-4` (4 cores, balanced)

## Scheduling Policy

Our scheduling strategy balances workload characteristics with node capabilities:

- **node-a-2core**: Runs *canneal* (memory-intensive benchmark)
  - Placed on `e2-highmem-2` to leverage higher memory capacity for this memory-intensive workload.

- **node-b-2core**: Runs *blackscholes* and *dedup* sequentially
  - `n2-highcpu-2` provides good CPU performance for computation-heavy *blackscholes*.
  - Followed by *dedup* for efficient memory-to-CPU utilization.

- **node-c-4core**: Runs *freqmine*, *radix*, and *vips* sequentially
  - `c3-highcpu-4` with SSD storage provides optimal compute and I/O performance.
  - Sequential execution ensures maximum resource availability for each application.
  - Running three varied workloads utilizes the 4-core capacity efficiently.

- **node-d-4core**: Runs *memcached* and *ferret* in parallel
  - *memcached* is pinned to dedicated cores to ensure consistent latency performance.
  - *ferret* runs alongside, leveraging the `n2-standard-4`'s balanced resources.
  - The balanced configuration of this node provides suitable isolation for the latency-critical service.

## Implementation Details

- Node/pod affinity rules enforce VM-specific placement.
- CPU pinning using `taskset` isolates workloads on specific cores.
- A controller script orchestrates the sequential execution of batch applications.
- Resource requests/limits enforce proper resource allocation for each application.

## Usage

1. Set up the Kubernetes cluster with the specified VMs from the project instructions.

2. Install the mcperf client on the measure machine:
  
```bash
./install_mcperf.sh
```

3. Run the experiment:
  
```bash
./part3_experiment.sh 1
```

4. The logs and results will be saved in the `logs` directory. We have logs folder with all different runs of the experiments and `part_3_results_group_020` folder with the final results of the experiments.

5. Analyze the logs and print some statistics:
  - Job completion times - `python3 analyze_job_times.py`
  - SLO violations - `python3 analyze_slo.py`

6. After the satisfactory statistics, we can plot the results.
  - `python3 vis_plots.py`
