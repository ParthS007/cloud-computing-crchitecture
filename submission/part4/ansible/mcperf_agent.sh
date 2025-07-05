#!/bin/bash

# Start mcperf agent with 8 threads and restart if killed
while true; do
  ./mcperf -T 8 -A
  sleep 5
done
