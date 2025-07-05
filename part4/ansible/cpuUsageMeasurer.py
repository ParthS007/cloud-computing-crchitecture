#! /usr/bin/env python3

import psutil
import time
import sys


def measure_cpu_usage(file_name: str = "cpuUsage.csv"):
    print("Timestamp, CPU Usage, Memory Usage")
    try:
        with open(file_name, "w") as f:
            while True:
                output = f"{int(time.time())}, {psutil.cpu_percent(interval=1, percpu=True)}, {psutil.virtual_memory().percent}\n"
                f.write(output)
                f.flush()
                print(output)
    # close file if ctrl+c is pressed
    except KeyboardInterrupt:
        print("CPU usage measurement stopped")


if __name__ == "__main__":
    args = sys.argv[1:]
    # check if there is an argument and check if its a file name with csv extension
    if len(args) > 0 and args[0].endswith(".csv"):
        measure_cpu_usage(args[0])
    else:
        measure_cpu_usage()
