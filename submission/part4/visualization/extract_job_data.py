import os
import csv
import pandas as pd
import statistics

def parse_scheduler_line(line):
    """Parses a line from the log file and returns the relevant parts."""
    parts = line.split("] ")
    parts = [part.strip() for part in parts]
    parts.pop(2)
    for i in range(3):
        parts[i] = parts[i][1:]
    return parts

def extract_job_times_to_csv(input_file_path, output_file_path):
    """Extracts job status into a CSV file."""
    headers = ["job_name", "timestamp", "status"]

    with open(output_file_path, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)

        with open(input_file_path, 'r') as log_file:
            for line in log_file:
                line_parts = parse_scheduler_line(line)
                # Check for lines that contain job status information
                if line_parts[2] == "job" and "status" in line_parts[3]:
                    info_parts = line_parts[3].split(" ")
                    job_name = info_parts[1]
                    timestamp = line_parts[0]
                    status = info_parts[3].split(".")[1]

                    writer.writerow([job_name, timestamp, status])

def extract_memcached_cores_usage_to_csv(input_file_path, output_file_path):
    """Extracts Memcached cores usage into a CSV file."""
    headers = ["timestamp", "memcached_cores_usage"]

    with open(output_file_path, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)

        with open(input_file_path, 'r') as log_file:
            for line in log_file:
                line_parts = parse_scheduler_line(line)
                # Check for lines that contain Memcached cores usage information
                if line_parts[2] == "__main__" and line_parts[3].startswith("Cores available for jobs:"):
                    timestamp = line_parts[0]
                    info_parts = line_parts[3].split(": ")
                    memcached_cores_usage = 4 - len(info_parts[-1].split(" "))
                    writer.writerow([timestamp, memcached_cores_usage])

def extract_job_times_to_csv_all(input_directory_path, output_directory_path):
    """Extracts job times from all log files in the specified directory.""" 
    print(f"START: Extracting job times")   
    runs = [1, 2, 3]

    for run in runs:
        log_file_path = os.path.join(input_directory_path, f"scheduler_policy1_run{run}.log")
        output_file_path = os.path.join(output_directory_path, f"job_start_end_times/job_times_policy1_run{run}.csv")
        
        extract_job_times_to_csv(log_file_path, output_file_path)
    
    print(f"END: Extracted job times")

def extract_memcached_cores_usage_to_csv_all(input_directory_path, output_directory_path):
    """Extracts Memcached cores usage from all log files in the specified directory."""
    print(f"START: Extracting Memcached cores usage")
    runs = [1, 2, 3]

    for run in runs:
        log_file_path = os.path.join(input_directory_path, f"scheduler_policy1_run{run}.log")
        output_file_path = os.path.join(output_directory_path, f"memcached_cpu_usage/memcached_cpu_usage_policy1_run{run}.csv")
        
        extract_memcached_cores_usage_to_csv(log_file_path, output_file_path)
    
    print(f"END: Extracted Memcached cores usage")

def calculate_execution_intervals(csv_file_path):
    # Are the jobs running or not
    blackscholes_is_running = False
    canneal_is_running = False
    dedup_is_running = False
    ferret_is_running = False
    freqmine_is_running = False
    radix_is_running = False
    vips_is_running = False

    blackscholes_timestamps = []
    canneal_timestamps = []
    dedup_timestamps = []
    ferret_timestamps = []
    freqmine_timestamps = []
    radix_timestamps = []
    vips_timestamps = []

    df = pd.read_csv(csv_file_path)

    for index, row in df.iterrows():
        job_name = row["job_name"]
        timestamp = row["timestamp"]
        status = row["status"]

        if job_name == "blackscholes":
            if status == "RUNNING" and not blackscholes_is_running:
                blackscholes_is_running = True
                blackscholes_timestamps.append((timestamp, "start"))
            elif (status == "PAUSED" or status == "COMPLETED") and blackscholes_is_running:
                blackscholes_is_running = False
                blackscholes_timestamps.append((timestamp, "end"))

        elif job_name == "canneal":
            if status == "RUNNING" and not canneal_is_running:
                canneal_is_running = True
                canneal_timestamps.append((timestamp, "start"))
            elif (status == "PAUSED" or status == "COMPLETED") and canneal_is_running:
                canneal_is_running = False
                canneal_timestamps.append((timestamp, "end"))

        elif job_name == "dedup":
            if status == "RUNNING" and not dedup_is_running:
                dedup_is_running = True
                dedup_timestamps.append((timestamp, "start"))
            elif (status == "PAUSED" or status == "COMPLETED") and dedup_is_running:
                dedup_is_running = False
                dedup_timestamps.append((timestamp, "end"))

        elif job_name == "ferret":
            if status == "RUNNING" and not ferret_is_running:
                ferret_is_running = True
                ferret_timestamps.append((timestamp, "start"))
            elif (status == "PAUSED" or status == "COMPLETED") and ferret_is_running:
                ferret_is_running = False
                ferret_timestamps.append((timestamp, "end"))

        elif job_name == "freqmine":
            if status == "RUNNING" and not freqmine_is_running:
                freqmine_is_running = True
                freqmine_timestamps.append((timestamp, "start"))
            elif (status == "PAUSED" or status == "COMPLETED") and freqmine_is_running:
                freqmine_is_running = False
                freqmine_timestamps.append((timestamp, "end"))

        elif job_name == "radix":
            if status == "RUNNING" and not radix_is_running:
                radix_is_running = True
                radix_timestamps.append((timestamp, "start"))
            elif (status == "PAUSED" or status == "COMPLETED") and radix_is_running:
                radix_is_running = False
                radix_timestamps.append((timestamp, "end"))

        elif job_name == "vips":
            if status == "RUNNING" and not vips_is_running:
                vips_is_running = True
                vips_timestamps.append((timestamp, "start"))
            elif (status == "PAUSED" or status == "COMPLETED") and vips_is_running:
                vips_is_running = False
                vips_timestamps.append((timestamp, "end"))

    return (
        blackscholes_timestamps,
        canneal_timestamps,
        dedup_timestamps,
        ferret_timestamps,
        freqmine_timestamps,
        radix_timestamps,
        vips_timestamps
    )

def calculate_execution_time(timestamps):
    total_execution_time_s = 0

    for i in range(0, len(timestamps), 2):
        start_time_s = int(timestamps[i][0])
        end_time_s = int(timestamps[i + 1][0])

        total_execution_time_s += end_time_s - start_time_s

    return total_execution_time_s

def extract_job_exec_times_to_csv_all(input_directory_path, output_directory_path):
    """Extracts job execution times from all log files in the specified directory."""    
    print(f"START: Calculating execution times")
    runs = [1, 2, 3]

    for run in runs:
        input_file_path = os.path.join(input_directory_path, f"job_times/job_start_end_times/job_times_policy1_run{run}.csv")
        output_file_path = os.path.join(output_directory_path, f"job_exec_times/job_tot_exec_times_policy1_run{run}.csv")

        blackscholes_timestamps, canneal_timestamps, \
        dedup_timestamps, ferret_timestamps, \
        freqmine_timestamps, radix_timestamps, vips_timestamps = calculate_execution_intervals(input_file_path)

        blackscholes_tot_exec_time = calculate_execution_time(blackscholes_timestamps)
        canneal_tot_exec_time = calculate_execution_time(canneal_timestamps)
        dedup_tot_exec_time = calculate_execution_time(dedup_timestamps)
        ferret_tot_exec_time = calculate_execution_time(ferret_timestamps)
        freqmine_tot_exec_time = calculate_execution_time(freqmine_timestamps)
        radix_tot_exec_time = calculate_execution_time(radix_timestamps)  
        vips_tot_exec_time = calculate_execution_time(vips_timestamps)          

        with open(output_file_path, mode='w', newline='') as output_file:
            writer = csv.writer(output_file)
            writer.writerow(["job_name", "total_execution_time_seconds"])
            writer.writerow(["blackscholes", blackscholes_tot_exec_time])
            writer.writerow(["canneal", canneal_tot_exec_time])
            writer.writerow(["dedup", dedup_tot_exec_time])
            writer.writerow(["ferret", ferret_tot_exec_time])
            writer.writerow(["freqmine", freqmine_tot_exec_time])
            writer.writerow(["radix", radix_tot_exec_time])
            writer.writerow(["vips", vips_tot_exec_time])

    print("END: Execution times calculated and written to CSV files.")

def calculate_total_exec_time(input_directory_path):
    """Calculates total execution time statistics for all runs."""
    print(f"START: Calculating total execution time statistics")
    runs = [1, 2, 3]
    tot_times = []

    for run in runs:
        input_file_path = os.path.join(input_directory_path, f"scheduler_policy1_run{run}.log")
        with open(input_file_path, 'r') as log_file:
            for line in log_file:
                if "Scheduler completed in" in line:
                    time = float(line.split()[-2])
                    tot_times.append(time)
                    break
    return tot_times

def extract_job_stats_to_csv_all(input_directory_path, output_directory_path):
    """Extracts job statistics from all log files in the specified directory."""     
    print(f"START: Calculating job execution times statistics")
    runs = [1, 2, 3]

    output_file_path = os.path.join(output_directory_path, f"job_stat_exec_times/job_stat_exec_times_policy1.csv")

    job_exec_times = {
            "blackscholes": [],
            "canneal": [],
            "dedup": [],
            "ferret": [],
            "freqmine": [],
            "radix": [],
            "vips": [],
        }
    
    for run in runs:
        input_file_path = os.path.join(input_directory_path, f"job_times/job_exec_times/job_tot_exec_times_policy1_run{run}.csv")

        df = pd.read_csv(input_file_path)
        for index, row in df.iterrows():
            job_name = row["job_name"]
            exec_time = row["total_execution_time_seconds"]
            if job_name in job_exec_times:
                job_exec_times[job_name].append(exec_time)

    # Calculate average and standard deviation
    job_stats = []
    for job_name, exec_times in job_exec_times.items():
        if exec_times:
            avg_exec_time = statistics.mean(exec_times)
            std_dev_exec_time = statistics.stdev(exec_times) if len(exec_times) > 1 else 0
            job_stats.append((job_name, avg_exec_time, std_dev_exec_time))

    # Calculate average and standard deviation for total execution time
    total_times = calculate_total_exec_time(input_directory_path)
    avg_tot_time = statistics.mean(total_times)
    std_dev_tot_time = statistics.stdev(total_times) if len(total_times) > 1 else 0
    job_stats.append(("Total", avg_tot_time, std_dev_tot_time))

    # Write statistics to the output file
    with open(output_file_path, mode='w', newline='') as stat_output_file:
        writer = csv.writer(stat_output_file)
        writer.writerow(["job_name", "average_execution_time_seconds", "std_dev_execution_time_seconds"])
        for job_name, avg_exec_time, std_dev_exec_time in job_stats:
            writer.writerow([job_name, avg_exec_time, std_dev_exec_time])

    print(f"END: Job execution times statistics calculated and written to CSV files.")

def create_required_directories(output_directory_path):
    """Creates all necessary directories for output files."""
    required_dirs = [
        os.path.join(output_directory_path, "job_start_end_times"),
        os.path.join(output_directory_path, "memcached_cpu_usage"),
        os.path.join(output_directory_path, "job_exec_times"),
        os.path.join(output_directory_path, "job_stat_exec_times")
    ]
    
    for directory in required_dirs:
        os.makedirs(directory, exist_ok=True)
        print(f"Ensured directory exists: {directory}")

def main():
    # log_directory_path_4_3 = "part4/part4_3_logs"
    # log_directory_path_4_4_5s = "part4/part4_4_logs/5s_interval"
    # log_directory_path_4_4_9s = "part4/part4_4_logs/9s_interval"
    log_directory_path_4_4_7s = "part4/part4_4_logs/7s_interval"

    # output_directory_path_4_3 = "part4/part4_3_logs/job_times"
    # output_directory_path_4_4_5s = "part4/part4_4_logs/5s_interval/job_times"
    # output_directory_path_4_4_9s = "part4/part4_4_logs/9s_interval/job_times"
    output_directory_path_4_4_7s = "part4/part4_4_logs/7s_interval/job_times"

    # Create necessary directories
    create_required_directories(output_directory_path_4_4_7s)

    # extract_job_times_to_csv_all(log_directory_path_4_3, output_directory_path_4_3)
    # extract_job_times_to_csv_all(log_directory_path_4_4_5s, output_directory_path_4_4_5s)
    # extract_job_times_to_csv_all(log_directory_path_4_4_9s, output_directory_path_4_4_9s)
    extract_job_times_to_csv_all(log_directory_path_4_4_7s, output_directory_path_4_4_7s)

    # extract_memcached_cores_usage_to_csv_all(log_directory_path_4_3, output_directory_path_4_3)
    # extract_memcached_cores_usage_to_csv_all(log_directory_path_4_4_5s, output_directory_path_4_4_5s)
    # extract_memcached_cores_usage_to_csv_all(log_directory_path_4_4_9s, output_directory_path_4_4_9s)
    extract_memcached_cores_usage_to_csv_all(log_directory_path_4_4_7s, output_directory_path_4_4_7s)
    
    # extract_job_exec_times_to_csv_all(log_directory_path_4_3, output_directory_path_4_3)
    # extract_job_exec_times_to_csv_all(log_directory_path_4_4_5s, output_directory_path_4_4_5s)
    # extract_job_exec_times_to_csv_all(log_directory_path_4_4_9s, output_directory_path_4_4_9s)
    extract_job_exec_times_to_csv_all(log_directory_path_4_4_7s, output_directory_path_4_4_7s)

    # extract_job_stats_to_csv_all(log_directory_path_4_3, output_directory_path_4_3)
    # extract_job_stats_to_csv_all(log_directory_path_4_4_5s, output_directory_path_4_4_5s)
    # extract_job_stats_to_csv_all(log_directory_path_4_4_9s, output_directory_path_4_4_9s)
    extract_job_stats_to_csv_all(log_directory_path_4_4_7s, output_directory_path_4_4_7s)

if __name__ == "__main__":
    main()