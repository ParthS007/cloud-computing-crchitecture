# Cloud Computing Architecture Project

A comprehensive research project exploring resource interference, application profiling, and intelligent scheduling in cloud computing environments. This project investigates how latency-sensitive and batch applications can be efficiently co-scheduled in Kubernetes clusters while minimizing resource contention and maintaining performance guarantees.

## Project Overview

This repository contains a complete implementation and analysis of cloud computing architecture principles through four progressive parts:

1. **Part 1**: Resource Interference Analysis - Understanding how hardware resource contention affects latency-critical applications
2. **Part 2**: Batch Application Profiling - Characterizing resource requirements of diverse computational workloads  
3. **Part 3**: Static Co-scheduling - Developing scheduling policies for heterogeneous cluster environments
4. **Part 4**: Dynamic Scheduler Implementation - Creating adaptive schedulers that respond to runtime conditions

## Key Technologies

- **Kubernetes**: Container orchestration and cluster management
- **Google Cloud Platform**: Infrastructure and virtual machine provisioning
- **Memcached**: Latency-critical in-memory caching application
- **PARSEC Benchmark Suite**: Diverse batch computational workloads
- **mcperf**: Specialized memcached performance measurement tool
- **iBench**: Hardware resource interference generation
- **Ansible**: Infrastructure automation and deployment
- **Python**: Data analysis, visualization, and scheduler implementation

## Architecture

The project utilizes a distributed cloud infrastructure consisting of:

- **Master Node**: Kubernetes control plane
- **Worker Nodes**: Heterogeneous VM configurations (2-core/4-core, CPU/memory optimized)
- **Client VMs**: Load generation and performance measurement
- **Dynamic Scheduler**: Real-time resource allocation and job management

## Quick Start

### Prerequisites

- Google Cloud Platform account with billing enabled
- Kubernetes cluster access (`kubectl` configured)
- Python 3.11+ with virtual environment support
- Required Python packages (see `requirements.txt`)

### Environment Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd cloud-computing-architecture
   ```

2. **Set up Python environment**:
   ```bash
   python -m venv env
   source env/bin/activate  # On macOS/Linux
   pip install -r requirements.txt
   ```

3. **Configure Google Cloud**:
   ```bash
   gcloud config set account your-email@student.ethz.ch
   gcloud config set project your-project-id
   kubectl config set-context part1.k8s.local --cluster=part1.k8s.local
   kubectl config use-context part1.k8s.local
   ```

4. **SSH to K8s cluster** (convenience script):
   ```bash
   chmod +x ssh-k8s.sh
   ./ssh-k8s.sh
   ```

## Project Parts

### Part 1: Resource Interference Analysis

**Objective**: Investigate how hardware resource contention affects memcached performance.

**Key Components**:
- Memcached server deployment with CPU affinity controls
- mcperf load generator for realistic workload simulation
- iBench interference patterns (CPU, L1D, L1I, L2, LLC, MEMBW)
- Tail latency analysis across different QPS levels

**Files**:
- `part1/run_part_1.py` - Main experiment orchestration
- `part1/vis_part_1.py` - Performance visualization
- `memcache-t1-cpuset.yaml` - Memcached pod configuration
- `interference/` - Hardware interference workloads

**Running Part 1**:
```bash
cd part1
# Install mcperf and load data
python run_part_1.py install

# Start client agent
python run_part_1.py client

# Run benchmark suite (7 interference patterns × 3 iterations)
python run_part_1.py benchmark
```

**Expected Output**: Performance logs in `part1/logs/` showing latency impact of each interference type.

---

### Part 2: Batch Application Profiling

**Objective**: Characterize resource requirements and interference sensitivity of PARSEC benchmarks.

**Applications Studied**:
- `blackscholes` - Financial modeling (compute-intensive)
- `canneal` - Chip design optimization (memory-intensive) 
- `dedup` - Data deduplication (mixed workload)
- `ferret` - Content-based search (pipeline parallel)
- `freqmine` - Data mining (memory + compute)
- `radix` - Sorting algorithm (memory bandwidth)
- `vips` - Image processing (varied resources)

**Files**:
- `parsec-benchmarks/` - YAML configurations for each workload
- `part2/task1/` - Interference sensitivity analysis
- `part2/task2/` - Resource requirement profiling

**Running Part 2**:
```bash
# Generate test logs for single workload
python part2/gen_logs_interference.py --test --workload=canneal --interference=cpu --repetitions=1

# Generate complete dataset
python part2/gen_logs_interference.py

# Visualize results
python part2/vis_logs_interference.py part2/parsec_results/all_results.csv --output-dir=part2/visualizations
```

---

### Part 3: Static Co-scheduling

**Objective**: Develop scheduling policies for heterogeneous clusters running mixed workloads.

**Cluster Configuration**:
- **node-a-2core**: `e2-highmem-2` → Runs canneal (memory-intensive)
- **node-b-2core**: `n2-highcpu-2` → Runs blackscholes + dedup sequentially  
- **node-c-4core**: `c3-highcpu-4` → Runs freqmine + radix + vips sequentially
- **node-d-4core**: `n2-standard-4` → Runs ferret (balanced workload)

**Key Features**:
- Memcached co-location with batch jobs
- SLA maintenance through careful placement
- Resource utilization optimization

**Files**:
- `part3/part3_experiment.sh` - Main experiment runner
- `part3/controller-*.sh` - Per-node control scripts  
- `part3/analyze_slo.py` - SLA compliance analysis
- `part3/vis_plots.py` - Results visualization

**Running Part 3**:
```bash
cd part3
# Install dynamic mcperf
./install_mcperf.sh

# Run experiment (specify run number)
./part3_experiment.sh 1

# Analyze results
python analyze_results.py
```

---

### Part 4: Dynamic Scheduler Implementation

**Objective**: Create adaptive schedulers that respond to runtime conditions and resource demands.

**Scheduler Policies**:
1. **Core Scaling Policy** (2-core nodes): Dynamic core allocation based on CPU utilization
2. **Advanced Policy** (3-core nodes): Sophisticated resource management with job prioritization

**Key Features**:
- Real-time CPU monitoring and adjustment
- Job queuing and prioritization
- Automated core allocation (1-3 cores for memcached)
- Comprehensive logging and performance tracking

**Files**:
- `part4/scheduler/` - Complete scheduler implementation
  - `main.py` - Scheduler entry point and orchestration
  - `policy_1_2_cores.py` - Basic 2-core scheduling policy
  - `policy_2_3_cores.py` - Advanced 3-core scheduling policy
  - `job.py` - Job management and containerization
  - `scheduler_logger.py` - Performance logging and monitoring
- `part4/ansible/` - Infrastructure automation
  - `install_scheduler.yaml` - Scheduler deployment playbook
  - `inventory.yaml` - Cluster configuration
- `part4/part4_1_a_c.py` - Core scaling experiments
- `part4/part4_1_d.py` - Core count analysis
- `part4/part4_2&3.py` - Policy comparison experiments

**Running Part 4**:

1. **Deploy Scheduler** (using Ansible):
   ```bash
   ansible-playbook -i part4/ansible/inventory.yaml part4/ansible/install_scheduler.yaml
   ```

2. **Run Core Scaling Experiments**:
   ```bash
   cd part4
   python part4_1_a_c.py  # Basic core scaling
   python part4_1_d.py    # Core count analysis
   ```

3. **Run Policy Comparison**:
   ```bash
   python part4_2&3.py    # Compare scheduling policies
   ```

4. **Visualize Results**:
   ```bash
   python vis_part4_1.py     # Core scaling visualization
   python vis_part4_1_d.py   # Core analysis plots
   ```

**Scheduler Features**:
- **Automatic Core Adjustment**: Scales memcached cores (1-3) based on CPU usage thresholds
- **Job Queue Management**: Intelligent batching and prioritization of PARSEC jobs
- **Performance Monitoring**: Real-time logging of CPU usage, job completion times, and resource allocation decisions
- **SLA Protection**: Maintains memcached performance guarantees while maximizing cluster utilization

## Repository Structure

```
cloud-computing-architecture/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── scheduler_logger.py          # Shared logging utilities
├── ssh-k8s.sh                  # Cluster SSH convenience script
├── get_time.py                 # Time synchronization utility
│
├── docs/                       # Documentation
│   └── part1.md               # Part 1 detailed instructions
│
├── part1/                      # Resource Interference Analysis
│   ├── README.md              # Part 1 documentation
│   ├── run_part_1.py          # Main experiment runner
│   ├── vis_part_1.py          # Visualization tools
│   ├── install_mcperf.sh      # mcperf installation script
│   └── logs/                  # Experimental results
│
├── part2/                      # Batch Application Profiling
│   ├── README.md              # Part 2 documentation
│   ├── task1/                 # Interference sensitivity analysis
│   └── task2/                 # Resource requirement profiling
│
├── part3/                      # Static Co-scheduling
│   ├── README.md              # Part 3 documentation
│   ├── part3_experiment.sh    # Main experiment orchestration
│   ├── controller-*.sh        # Per-node control scripts
│   ├── analyze_slo.py         # SLA compliance analysis
│   ├── monitor_jobs.sh        # Job monitoring utilities
│   └── logs/                  # Experimental results
│
├── part4/                      # Dynamic Scheduler Implementation
│   ├── scheduler/             # Core scheduler implementation
│   │   ├── main.py           # Scheduler entry point
│   │   ├── policy_1_2_cores.py  # Basic scheduling policy
│   │   ├── policy_2_3_cores.py  # Advanced scheduling policy
│   │   ├── job.py            # Job management
│   │   └── scheduler_logger.py   # Performance logging
│   ├── ansible/              # Infrastructure automation
│   │   ├── install_scheduler.yaml # Deployment playbook
│   │   └── inventory.yaml    # Cluster configuration
│   ├── part4_1_a_c.py        # Core scaling experiments
│   ├── part4_1_d.py          # Core count analysis
│   ├── part4_2&3.py          # Policy comparison
│   └── vis_part4_*.py        # Result visualization
│
├── parsec-benchmarks/          # PARSEC workload configurations
│   ├── part2a/               # Baseline configurations
│   └── part2b/               # Modified configurations
│
├── interference/               # Hardware interference workloads
│   ├── ibench-cpu.yaml       # CPU interference
│   ├── ibench-l1d.yaml       # L1 data cache interference
│   ├── ibench-l1i.yaml       # L1 instruction cache interference
│   ├── ibench-l2.yaml        # L2 cache interference
│   ├── ibench-llc.yaml       # Last-level cache interference
│   └── ibench-membw.yaml     # Memory bandwidth interference
│
├── examples/                   # Sample outputs and logs
│   ├── mcperf-part3.txt      # Part 3 sample results
│   ├── mcperf-part4.txt      # Part 4 sample results
│   └── scheduler-part4.txt   # Scheduler sample logs
│
└── submission/                 # Final results and reports
    ├── README.md             # Submission documentation
    └── part_*_results_group_020/  # Experimental results
```

## Performance Analysis Tools

### Visualization Scripts
- `part1/vis_part_1.py` - QPS vs latency analysis with interference patterns
- `part1/vis_qps_latency.py` - Detailed latency distribution plots
- `part3/vis_plots.py` - Co-scheduling performance analysis
- `part4/vis_part4_1.py` - Core scaling effectiveness
- `part4/vis_part4_1_d.py` - Core count optimization analysis

### Data Analysis Scripts  
- `part3/analyze_job_times.py` - Batch job completion time analysis
- `part3/analyze_slo.py` - SLA compliance and violation tracking
- `part4/analyze_job_times.py` - Dynamic scheduling performance analysis
- `part4/extract_job_data.py` - Log parsing and data extraction utilities

### Monitoring and Logging
- `scheduler_logger.py` - Centralized logging framework for scheduler events
- `part4/mcPerfLogs.py` - mcperf performance log analysis
- `part4/ansible/cpuUsageMeasurer.py` - Real-time CPU monitoring

## Key Configuration Files

### Kubernetes Manifests
- `memcache-t1-cpuset.yaml` - Memcached deployment with CPU affinity
- `part*.yaml` - Per-part cluster configurations
- `parsec-benchmarks/*.yaml` - PARSEC workload specifications

### Infrastructure Automation
- `part4/ansible/install_scheduler.yaml` - Automated scheduler deployment
- `part4/ansible/inventory.yaml` - Cluster node configuration
- `part4/ansible/set_up_vms.yaml` - VM provisioning automation

## Research Insights

This project demonstrates several key cloud computing principles:

1. **Resource Interference Quantification**: Systematic measurement of how shared hardware resources impact application performance
2. **Workload Characterization**: Comprehensive profiling of diverse computational workloads and their resource requirements
3. **Intelligent Scheduling**: Development of policies that balance performance, resource utilization, and SLA compliance
4. **Dynamic Adaptation**: Implementation of schedulers that respond to runtime conditions and changing resource demands

## Troubleshooting

### Common Issues

1. **Kubernetes Context Issues**:
   ```bash
   kubectl config set-context part1.k8s.local --cluster=part1.k8s.local
   kubectl config use-context part1.k8s.local
   ```

2. **Google Cloud Authentication**:
   ```bash
   gcloud config set account your-email@student.ethz.ch
   gcloud config set project your-project-id
   ```

3. **Pod Scheduling Issues**: Check node capacity and resource requests in YAML files

4. **mcperf Connection Issues**: Verify memcached pod IP and update hardcoded IPs in scripts

### Getting Node Information
```bash
kubectl get nodes -o wide
kubectl get pods -o wide
kubectl describe pod <pod-name>
```

### Log Access
```bash
kubectl logs <pod-name>
kubectl exec -it <pod-name> -- /bin/bash
```

## Dependencies

### System Requirements
- Python 3.11+
- kubectl (Kubernetes CLI)
- gcloud (Google Cloud CLI)
- Ansible (for Part 4 automation)

### Python Packages
```
kubernetes==32.0.1
numpy==2.2.3
matplotlib==3.10.1
psutil
colorama
pyyaml
```

### Cloud Resources
- Google Cloud Platform project with billing enabled
- Kubernetes cluster with multiple node types
- VM instances for mcperf clients
- Load balancer for memcached service exposure

## Contributing

This project was developed as part of the Cloud Computing Architecture course at ETH Zurich. The implementation demonstrates practical applications of resource management, interference analysis, and intelligent scheduling in modern cloud environments.

## Timeline

- **Week 1-2**: Resource interference analysis (Part 1-2)
- **Week 3-4**: Static co-scheduling implementation (Part 3)  
- **Week 5-8**: Dynamic scheduler development (Part 4)
- **Week 9**: Results consolidation and final analysis

## License

This project is part of academic coursework at ETH Zurich. Please respect academic integrity policies when referencing or building upon this work.
