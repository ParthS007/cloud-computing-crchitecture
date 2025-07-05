from job import JobInfo, JobInstance
from typing import List, Optional


class Policy:
    def __init__(self):
        pass

    def schedule(self, available_cores: set[int]):
        raise NotImplementedError("Subclasses must implement this method")

    def add_job(self, job: JobInfo):
        raise NotImplementedError("Subclasses must implement this method")
