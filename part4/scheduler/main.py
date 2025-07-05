#! /usr/bin/env python3

import subprocess
import psutil
import time
from typing import Dict
from policy_1_2_cores import Policy1And2Cores
from policy_2_3_cores import Policy2And3Cores
from job import JobInfo
from policy import Policy
import logging
import sys
from colorama import init, Fore, Style
from scheduler_logger import SchedulerLogger, Job as JobEnum

# Initialize colorama
init()


# Custom formatter with colors
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.INFO:
            record.levelname = f"{Fore.GREEN}{record.levelname}{Style.RESET_ALL}"
        elif record.levelno == logging.WARNING:
            record.levelname = f"{Fore.YELLOW}{record.levelname}{Style.RESET_ALL}"
        elif record.levelno == logging.ERROR:
            record.levelname = f"{Fore.RED}{record.levelname}{Style.RESET_ALL}"
        elif record.levelno == logging.DEBUG:
            record.levelname = f"{Fore.BLUE}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)


logger = logging.getLogger(__name__)
# CPU usage in percent for when to assign more cores to memcached
CPU_LOW = 70
# CPU usage in percent for when to assign less cores to memcached
CPU_HIGH = 100
# Number of consecutive samples below CPU_HIGH for which to switch back to 1 core
CPU_HIGH_THRESHOLD = 2

jobs: Dict[str, JobInfo] = {
    "blackscholes": {
        "name": "blackscholes",
        "logger_job": JobEnum.BLACKSCHOLES,
        "image": "anakli/cca:parsec_blackscholes",
        "command": [
            "/bin/sh",
            "-c",
            "./run -a run -S parsec -p blackscholes -i native -n {threads}",
        ],
        "paralellizability": 1,
    },
    "canneal": {
        "name": "canneal",
        "logger_job": JobEnum.CANNEAL,
        "image": "anakli/cca:parsec_canneal",
        "command": [
            "/bin/sh",
            "-c",
            "./run -a run -S parsec -p canneal -i native -n {threads}",
        ],
        "paralellizability": 1,
    },
    "dedup": {
        "name": "dedup",
        "logger_job": JobEnum.DEDUP,
        "image": "anakli/cca:parsec_dedup",
        "command": [
            "/bin/sh",
            "-c",
            "./run -a run -S parsec -p dedup -i native -n {threads}",
        ],
        "paralellizability": 1,
    },
    "ferret": {
        "name": "ferret",
        "logger_job": JobEnum.FERRET,
        "image": "anakli/cca:parsec_ferret",
        "command": [
            "/bin/sh",
            "-c",
            "./run -a run -S parsec -p ferret -i native -n {threads}",
        ],
        "paralellizability": 2,
    },
    "freqmine": {
        "name": "freqmine",
        "logger_job": JobEnum.FREQMINE,
        "image": "anakli/cca:parsec_freqmine",
        "command": [
            "/bin/sh",
            "-c",
            "./run -a run -S parsec -p freqmine -i native -n {threads}",
        ],
        "paralellizability": 2,
    },
    "radix": {
        "name": "radix",
        "logger_job": JobEnum.RADIX,
        "image": "anakli/cca:splash2x_radix",
        "command": [
            "/bin/sh",
            "-c",
            "./run -a run -S splash2x -p radix -i native -n {threads}",
        ],
        "paralellizability": 2,
    },
    "vips": {
        "name": "vips",
        "logger_job": JobEnum.VIPS,
        "image": "anakli/cca:parsec_vips",
        "command": [
            "/bin/sh",
            "-c",
            "./run -a run -S parsec -p vips -i native -n {threads}",
        ],
        "paralellizability": 2,
    },
}

schedulerLogger = SchedulerLogger()


def get_memcached_pid():
    # get the pid of the memcached process
    return subprocess.check_output(["pgrep", "-f", "memcached"]).decode("utf-8").strip()


def set_memcached_cpu_affinity(pid: int, cores: str):
    # set the cpu affinity of the memcached process
    # taskset -a -p <pid> -c <cores>
    logger.info(
        subprocess.run(
            ["sudo", "taskset", "-a", "-cp", cores, str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    )


# create two policies.
# 1) One has 2 and 3 core jobs. It maintains 2 queues to run 2 and 3 core jobs.
# when three cores are available it will start/resume the first job in the 3 core queue and pause the 2 core job currently running
# when two cores are available it will start/resume the first job in the 2 core queue and pause the 3 core job currently running
# if
# 2) The other has 1 and 2 core jobs. It maintains 2 queues to run the jobs.
# it will run the 2 core jobs sequentially.
# it will run the 1 core if a 3rd core is available.
# If there are no 2 core jobs left, it will run the 1 core jobs on the remaining cores.
# If no more 1 core jobs are left, it will run the 2 core jobs on all available cores.


def main(policy: Policy, logfile: str | None):
    # log to a file (scheduler_04052025_17h36.log) with epoch time
    formatter = ColoredFormatter(
        f"[%(created)d] [policy: {policy.policy_name}] [%(levelname)s] [%(name)s] %(message)s"
    )

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    if not logfile is None:
        # File handler without colors
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(formatter)
        logging.basicConfig(
            level=logging.INFO, handlers=[file_handler, console_handler]
        )
    else:
        logging.basicConfig(level=logging.INFO, handlers=[console_handler])

    logger.info(f"CPU_LOW: {CPU_LOW}")
    logger.info(f"CPU_HIGH: {CPU_HIGH}")
    logger.info(f"CPU_HIGH_THRESHOLD: {CPU_HIGH_THRESHOLD}")

    memcached_pid = get_memcached_pid()
    logger.info(f"Memcached PID: {memcached_pid}")
    memcached_target_cores = 2
    set_memcached_cpu_affinity(memcached_pid, "0,1")
    logger.info(f"Memcached CPU affinity set to 0,1")

    schedulerLogger.job_start(JobEnum.MEMCACHED, [0, 1], 2)

    for job in jobs:
        if job == "radix":
            # radix cant run with 3 cores
            temp = jobs[job]
            temp["paralellizability"] = 1
            policy.add_job(temp)
        else:
            policy.add_job(jobs[job])

    logger.info(f"Starting scheduler with policy: {policy.policy_name}")

    start_time = time.time()

    # store the last 10 cpu usage samples
    cpu_usage_samples = []

    while True:
        cpu_usage = psutil.cpu_percent(interval=1, percpu=True)
        cpu_usage_samples.append(cpu_usage)

        if len(cpu_usage_samples) > 10:
            cpu_usage_samples.pop(0)

        logger.info(f"CPU usage: {cpu_usage}")

        old_memcached_target_cores = memcached_target_cores

        # Respond quickly to high CPU usage by checking current sample
        if memcached_target_cores == 1 and cpu_usage[0] > CPU_LOW:
            memcached_target_cores = 2
        # Respond slowly to low CPU usage by requiring multiple low samples
        elif memcached_target_cores == 2 and all(
            (sample[0] + sample[1]) < CPU_HIGH
            for sample in cpu_usage_samples[-CPU_HIGH_THRESHOLD:]
        ):
            # Only scale down if we see consistently low usage across last 5 samples
            memcached_target_cores = 1

        memcached_cores = range(memcached_target_cores)

        available_cores = set(range(len(cpu_usage))) - set(memcached_cores)

        logger.info(f"Cores available for jobs: {available_cores}")

        policy.schedule(available_cores)

        if old_memcached_target_cores != memcached_target_cores:
            set_memcached_cpu_affinity(
                memcached_pid, ",".join(map(str, memcached_cores))
            )

        if policy.isCompleted:
            set_memcached_cpu_affinity(memcached_pid, "0-3")
            schedulerLogger.end()
            break

        time.sleep(1)

    end_time = time.time()
    logger.info(f"Scheduler completed in {end_time - start_time} seconds")


if __name__ == "__main__":

    # read policy from command line with -p flag
    policy = None
    if "-p" in sys.argv:
        if sys.argv[sys.argv.index("-p") + 1] == "1":
            policy = Policy1And2Cores(schedulerLogger)
        elif sys.argv[sys.argv.index("-p") + 1] == "2":
            policy = Policy2And3Cores(schedulerLogger)
        else:
            raise ValueError(f"Invalid policy: {sys.argv[sys.argv.index('-p') + 1]}")
    else:
        policy = Policy1And2Cores(schedulerLogger)

    # read logfile from command line with -l flag
    if "-l" in sys.argv:
        logfile = sys.argv[sys.argv.index("-l") + 1]
    else:
        logfile = None

    main(policy, logfile)
