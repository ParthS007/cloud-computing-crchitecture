#!/bin/bash

# Update package list
sudo apt-get update

# Install required dependencies
sudo apt-get install libevent-dev libzmq3-dev git make g++ --yes

# Add deb-src to sources
sudo sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/ubuntu.sources

# Update package list again
sudo apt-get update

# Install build dependencies for memcached
sudo apt-get build-dep memcached --yes

# Clone and build mcperf
cd && git clone https://github.com/shaygalon/memcache-perf.git
cd memcache-perf
git checkout 0afbe9b
make 