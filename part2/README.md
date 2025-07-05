# Part 2 Explaination

## Problem Context and Concepts

This part of the project explores how throughput-oriented "batch" workloads behave in cloud environments:

1. Resource Interference Sensitivity: How batch applications perform when sharing hardware resources with other workloads

2. Application Resource Profiling: Understanding which specific hardware resources are critical for different applications

## Parsec Benchmark

A collection of multi-threaded applications representing diverse workload characteristics:

- blackscholes: Financial analysis (option pricing) - typically compute-intensive
- canneal: Engineering optimization for chip design - memory and cache intensive
- dedup: Data deduplication - mixed I/O, memory, and compute requirements
- ferret: Content-based image search - pipeline parallelism with varied resources
- freqmine: Data mining workload - memory and compute intensive
- radix: Sorting algorithm - memory bandwidth intensive
- vips: Image processing - varied compute and memory needs
