import re
from datetime import datetime
import os

# Job names as in SchedulerLogger
JOBS = [
    "scheduler",
    "memcached",
    "blackscholes",
    "canneal",
    "dedup",
    "ferret",
    "freqmine",
    "radix",
    "vips",
]

# Track job statuses
job_statuses = {}


# Helper to get job enum name
def get_job_name(name):
    name = name.lower()
    for job in JOBS:
        if job in name:
            return job
    return "scheduler"


# Parse a log line and convert to SchedulerLogger format
def parse_line(line):
    # Example: [1746539176] [policy: 1_2_cores] [INFO] [job] Job ferret started with cores 2,3 and 2 threads
    m = re.match(r"\[(\d+)\].*?\[(job|__main__)\] (.*)", line)
    if not m:
        return None
    timestamp, section, msg = m.groups()
    # Convert timestamp to ISO format
    dt = datetime.fromtimestamp(int(timestamp)).isoformat()

    # Job events
    if section == "job":
        # Job start
        m2 = re.match(r"Job (\w+) started with cores ([\d,]+) and (\d+) threads", msg)
        if m2:
            job_name, cores, threads = m2.groups()
            job_name = job_name.lower()
            job_statuses[job_name] = "RUNNING"
            return f"{dt} start {job_name} [{cores}] {threads}"

        # Job end/completed
        m2 = re.match(r"Job (\w+) completed.*", msg)
        if m2:
            job_name = m2.group(1).lower()
            if job_statuses.get(job_name) != "COMPLETED":
                job_statuses[job_name] = "COMPLETED"
                return f"{dt} end {job_name}"
            return None

        # Job status
        m2 = re.match(r"Job (\w+) status: JobStatus\.(\w+)", msg)
        if m2:
            job_name, status = m2.groups()
            job_name = job_name.lower()
            old_status = job_statuses.get(job_name)

            if status == "PAUSED" and old_status != "PAUSED":
                job_statuses[job_name] = "PAUSED"
                return f"{dt} pause {job_name}"
            elif status == "COMPLETED" and old_status != "COMPLETED":
                job_statuses[job_name] = "COMPLETED"
                return f"{dt} end {job_name}"
            elif status == "RUNNING" and old_status == "PAUSED":
                job_statuses[job_name] = "RUNNING"
                return f"{dt} unpause {job_name}"
            return None

        # Job paused/unpaused (explicit commands)
        m2 = re.match(r"Job (\w+) paused", msg)
        if m2:
            job_name = m2.group(1).lower()
            if job_statuses.get(job_name) != "PAUSED":
                job_statuses[job_name] = "PAUSED"
                return f"{dt} pause {job_name}"
            return None

        m2 = re.match(r"Job (\w+) unpaused", msg)
        if m2:
            job_name = m2.group(1).lower()
            if job_statuses.get(job_name) == "PAUSED":
                job_statuses[job_name] = "RUNNING"
                return f"{dt} unpause {job_name}"
            return None

        # Job updated to cores
        m2 = re.match(r"Job (\w+) updated to cores ([\d,]+)", msg)
        if m2:
            job_name, cores = m2.groups()
            job_name = job_name.lower()
            if job_statuses.get(job_name) == "RUNNING":
                return f"{dt} update_cores {job_name} [{cores}]"
            return None

    elif section == "__main__":
        # Taskset command (memcached core update)
        if "CompletedProcess" in msg:
            m2 = re.search(r"taskset.*-cp.*?(\d+(?:[,-]\d+)*)", msg)
            if not m2:
                return None
            cores_str = m2.group(1)
            if "-" in cores_str:
                start, end = map(int, cores_str.split("-"))
                cores = list(map(str, range(start, end + 1)))
            else:
                cores = cores_str.split(",")
            if job_statuses.get("memcached") == "RUNNING":
                return f"{dt} update_cores memcached [{','.join(cores)}]"
            return None

        m2 = re.match(r"CPU_LOW: \d+", msg)
        if m2:
            job_statuses["scheduler"] = "RUNNING"
            return f"{dt} start scheduler"

        # Scheduler start (detected by Memcached PID)
        if "Memcached PID" in msg:
            job_statuses["memcached"] = "RUNNING"
            return f"{dt} start memcached [0,1] 2"

        # Scheduler end
        if "Scheduler completed" in msg:
            if job_statuses.get("scheduler") != "COMPLETED":
                job_statuses["scheduler"] = "COMPLETED"
                return f"{dt} end scheduler"
            return None
    return None


def main(input_log: str, output_log: str):
    with open(input_log, "r") as fin, open(output_log, "w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            out = parse_line(line)
            if out:
                fout.write(out + "\n")


if __name__ == "__main__":
    files = os.listdir("../part4_2_logs_run2")
    for file in files:
        if (
            file.endswith(".log")
            and not file.endswith("_converted.txt")
            and not file.startswith("mcperf")
        ):
            main(
                f"../part4_2_logs_run2/{file}",
                f"../part4_2_logs_run2/{file.replace('.log', '_converted.txt')}",
            )
