# Part 1 Explaination

Our main aim is to investigate how a latency-critical application (memcached) performs under various types of hardware resource interference. 

- We examine how different types of **contention for shared hardware resources** affect the tail latency of memcached at varying request rates. 

- This understanding is important where multiple applications frequently share the same physical infrastructure. Part 1 gives us insights into memcached's resource sensitivity patterns.

## Memcached

- Distributed in-memory caching system that serves as a temporary store for frequently accessed data.

- As a latency-critical application, memcached's performance is typically measured by tail latency rather than average latency, as tail latency better represents the worst-case user experience.

### Infrastructure Setup for Measurement

The experimental setup consists of four virtual machines (VMs) in Google Cloud:

1. Kubernetes Cluster Master: Controls the overall experiment orchestration

2. Memcached Server VM: Hosts both the memcached application and the iBench interference workloads

3. Client-Agent VM: Runs the mcperf load generation agent

4. Client-Measure VM: Initiates test scenarios and collects performance measurements

## Memcache-perf

- mcperf is a specialized load generator designed for benchmarking memcached performance

In this project, `mcperf` is configured to:

- Use 8 threads (-T 8)
- Establish 8 connections per thread (-C 8)
- Create a depth of 4 outstanding requests per connection (-D 4)
- Send 1000 requests per connection (-Q 1000)
- Run each test for 5 seconds (-t 5)
- Use a warm-up period of 2 seconds (-w 2)

## iBench Resource Interference Suite

- iBench is a collection of microbenchmarks specifically designed to create controllable, targeted interference in various hardware resources. Each benchmark targets a specific shared resource:
    - ibench-cpu: Creates contention for CPU processing cycles
    - ibench-l1d: Generates L1 data cache interference
    - ibench-l1i: Creates L1 instruction cache contention
    - ibench-l2: Targets the L2 cache
    - ibench-llc: Interferes with the last-level cache (LLC)
    - ibench-membw: Competes for memory bandwidth

These benchmarks allow for precise investigation of how different types of resource contention affect memcached performance.

## Conceptual Significance

### Resource Interference and Performance Implications

In multi-tenant cloud environments, applications often compete for shared hardware resources. This contention can significantly impact performance, especially for latency-critical applications like memcached. Understanding which resources most significantly affect memcached performance helps in:

- Resource allocation decisions: Determining appropriate resource guarantees
- Application co-location strategies: Identifying which applications can safely share infrastructure
- Performance prediction: Anticipating performance degradation under resource contention
- Hardware design decisions: Guiding the design of future server architectures

### Tail Latency vs. Average Latency

The project focuses on tail latency (95th percentile) rather than average latency because:

- End-user experience is often determined by the worst-case rather than average performance.

- In distributed systems, the overall response time is often gated by the slowest component.

- Tail latency is more sensitive to resource interference than average latency.

### QPS vs. Latency Curve

By scanning QPS from 5000 to 80000 in increment steps(5000), the experiment captures the complete performance profile of memcached. This curve typically shows:

- A flat region at low QPS where latency is stable
- A knee point where latency begins to increase
- A steep region where latency increases rapidly as the system approaches saturation

Different interference types affects different regions of this curve, revealing important insights about memcached's resource sensitivity.
