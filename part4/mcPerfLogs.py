import os


class McPerfLogs:
    log_file = None
    data = []

    def __init__(self, log_file):
        self.log_file = log_file
        self.data = []

    def parse_log_file(self):
        if not os.path.exists(self.log_file):
            print(f"Error: {self.log_file} not found")
            return []

        try:
            with open(self.log_file, "r") as f:
                lines = f.readlines()

            for line in lines:
                if line.startswith("#") or not line.strip():
                    continue

                parts = line.strip().split()
                if len(parts) < 16 or parts[0] != "read":
                    continue

                try:
                    metrics = {
                        "type": parts[0],
                        "avg": float(parts[1]),
                        "std": float(parts[2]),
                        "min": float(parts[3]),
                        "p5": float(parts[4]),
                        "p10": float(parts[5]),
                        "p50": float(parts[6]),
                        "p67": float(parts[7]),
                        "p75": float(parts[8]),
                        "p80": float(parts[9]),
                        "p85": float(parts[10]),
                        "p90": float(parts[11]),
                        "p95": float(parts[12]),
                        "p99": float(parts[13]),
                        "p999": float(parts[14]),
                        "p9999": float(parts[15]),
                        "qps": float(parts[16]),
                        "target": float(parts[17]),
                        "ts_start": int(parts[18]),
                        "ts_end": int(parts[19]),
                    }
                    self.data.append(metrics)
                except (ValueError, IndexError) as e:
                    print(f"Error parsing line: {e}")
                    continue

            return self.data

        except Exception as e:
            print(f"Error processing file {self.log_file}: {e}")
            return []
