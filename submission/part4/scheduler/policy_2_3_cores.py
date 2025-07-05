# Scheduling Policy:
# This policy has 2 and 3 core jobs. It maintains 2 queues to run the jobs.
# It will run the 3 core jobs sequentially.
# It will run the 2 core job if a 4th core is available.
# If there are no 3 core jobs left, it will run the 2 core jobs on the remaining cores.
# If no more 2 core jobs are left, it will run the 3 core jobs on all available cores.

from typing import List, Optional
from job import JobInstance, JobStatus
import logging
from job import JobInfo
from policy import Policy

logger = logging.getLogger(__name__)


class Policy2And3Cores(Policy):
    def __init__(self):
        self.two_core_queue: List[JobInstance] = []
        self.three_core_queue: List[JobInstance] = []
        self.running_two_core: Optional[JobInstance] = None
        self.running_three_core: Optional[JobInstance] = None
        self.isCompleted = False
        self.policy_name = "2_3_cores"

    def add_job(self, job: JobInfo):
        """Add a job to the appropriate queue based on its paralellizability."""
        job_instance = JobInstance(
            job["name"],
            job["image"],
            job["command"],
            2 if job["paralellizability"] == 1 else 3,
        )
        if job["paralellizability"] == 1:
            self.two_core_queue.append(job_instance)
        elif job["paralellizability"] == 2:
            self.three_core_queue.append(job_instance)

    def schedule(self, available_cores: set[int]):
        """Implement the scheduling policy:
        1. Run 3-core jobs sequentially
        2. Run 2-core jobs if only 2 cores are available
        3. If no 3-core jobs left, run 2-core jobs on remaining cores
        4. If no 2-core jobs left, run 3-core jobs on all available cores
        """
        # Check for completed jobs and free up cores
        self._check_completed_jobs()

        if (
            len(self.two_core_queue) == 0
            and len(self.three_core_queue) == 0
            and self.running_two_core is None
            and self.running_three_core is None
        ):
            self.isCompleted = True
            return

        # Sort available cores
        sorted_cores = sorted(available_cores)

        if len(available_cores) == 2:
            # If both queues are empty and there's a running job, give it all cores
            if len(self.two_core_queue) == 0 and len(self.three_core_queue) == 0:
                if (
                    self.running_two_core is None
                    and self.running_three_core
                    and self.running_three_core._status != JobStatus.COMPLETED
                ):
                    self.running_three_core.update_job_cpus(
                        f"{sorted_cores[0]},{sorted_cores[1]}"
                    )
                    try:
                        self.running_three_core.unpause_job()
                    except Exception as e:
                        logger.warning(f"Error unpausing 3-core job: {e}")
                elif (
                    self.running_three_core is None
                    and self.running_two_core
                    and self.running_two_core._status != JobStatus.COMPLETED
                ):
                    self.running_two_core.update_job_cpus(
                        f"{sorted_cores[0]},{sorted_cores[1]}"
                    )
                    try:
                        self.running_two_core.unpause_job()
                    except Exception as e:
                        logger.warning(f"Error unpausing 2-core job: {e}")
                return

            # Pause running 3-core job if exists
            if (
                self.running_three_core
                and self.running_three_core._status == JobStatus.RUNNING
            ):
                self.running_three_core.pause_job()

            # Start new 2-core job if none running
            if self.running_two_core is None:
                if len(self.two_core_queue) > 0:
                    self.running_two_core = self.two_core_queue.pop(0)
                    self.running_two_core.start_job(
                        f"{sorted_cores[0]},{sorted_cores[1]}"
                    )
                elif len(self.three_core_queue) > 0:
                    # If no 2-core jobs, run a 3-core job on 2 cores
                    self.running_two_core = self.three_core_queue.pop(0)
                    self.running_two_core.start_job(
                        f"{sorted_cores[0]},{sorted_cores[1]}"
                    )
            elif (
                self.running_two_core
                and self.running_two_core._status == JobStatus.PAUSED
            ):
                self.running_two_core.unpause_job()

        elif len(available_cores) == 3:
            # If both queues are empty and there's a running job, give it all cores
            if len(self.two_core_queue) == 0 and len(self.three_core_queue) == 0:
                if (
                    self.running_two_core is None
                    and self.running_three_core
                    and self.running_three_core._status != JobStatus.COMPLETED
                ):
                    self.running_three_core.update_job_cpus(
                        f"{sorted_cores[0]},{sorted_cores[1]},{sorted_cores[2]}"
                    )
                    try:
                        self.running_three_core.unpause_job()
                    except Exception as e:
                        logger.warning(f"Error unpausing 3-core job: {e}")
                elif (
                    self.running_three_core is None
                    and self.running_two_core
                    and self.running_two_core._status != JobStatus.COMPLETED
                ):
                    self.running_two_core.update_job_cpus(
                        f"{sorted_cores[0]},{sorted_cores[1]},{sorted_cores[2]}"
                    )
                    try:
                        self.running_two_core.unpause_job()
                    except Exception as e:
                        logger.warning(f"Error unpausing 2-core job: {e}")
                return

            # Pause running 2-core job if exists
            if (
                self.running_two_core
                and self.running_two_core._status == JobStatus.RUNNING
            ):
                self.running_two_core.pause_job()

            # Start new 3-core job if none running
            if self.running_three_core is None:
                if len(self.three_core_queue) > 0:
                    self.running_three_core = self.three_core_queue.pop(0)
                    self.running_three_core.start_job(
                        f"{sorted_cores[0]},{sorted_cores[1]},{sorted_cores[2]}"
                    )
                elif len(self.two_core_queue) > 0:
                    # If no 3-core jobs, run a 2-core job on 3 cores
                    self.running_three_core = self.two_core_queue.pop(0)
                    self.running_three_core.start_job(
                        f"{sorted_cores[0]},{sorted_cores[1]},{sorted_cores[2]}"
                    )
            elif (
                self.running_three_core
                and self.running_three_core._status == JobStatus.PAUSED
            ):
                self.running_three_core.unpause_job()

        return

    def _check_completed_jobs(self):
        """Check for completed jobs and update running jobs accordingly."""
        if self.running_two_core:
            status = self.running_two_core.check_job_completed()
            if status == JobStatus.COMPLETED:
                self.running_two_core = None
            elif status == JobStatus.ERROR:
                self.two_core_queue.append(self.running_two_core)
                self.running_two_core = None

        if self.running_three_core:
            status = self.running_three_core.check_job_completed()
            if status == JobStatus.COMPLETED:
                self.running_three_core = None
            elif status == JobStatus.ERROR:
                self.three_core_queue.append(self.running_three_core)
                self.running_three_core = None
