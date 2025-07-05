import __future__
import enum
from typing import Dict, Union, List
from docker.client import DockerClient
import docker
import logging
import signal
import sys
import time
import atexit
from scheduler_logger import SchedulerLogger, Job as JobEnum

logger = logging.getLogger(__name__)


Job = Union[str, list[str], JobEnum]
JobInfo = Dict[str, Job]


class JobStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class JobManager:
    _instance = None
    _jobs: List["JobInstance"] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JobManager, cls).__new__(cls)
            atexit.register(cls._instance.cleanup_all)
            signal.signal(signal.SIGINT, cls._instance._handle_interrupt)
            signal.signal(signal.SIGTERM, cls._instance._handle_interrupt)
        return cls._instance

    def register_job(self, job: "JobInstance"):
        self._jobs.append(job)

    def unregister_job(self, job: "JobInstance"):
        if job in self._jobs:
            self._jobs.remove(job)

    def _handle_interrupt(self, signum, frame):
        logger.error(f"Received interrupt signal {signum} stopping all jobs")
        self.cleanup_all()
        sys.exit(0)

    def cleanup_all(self):
        for job in self._jobs[:]:  # Copy list to avoid modification during iteration
            try:
                job.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up job {job._jobName}: {str(e)}")


class JobInstance:
    def __init__(
        self,
        jobName: str,
        image: str,
        command: list[str],
        threads: int,
        schedulerLogger: SchedulerLogger,
        job: JobEnum,
        docker_client: DockerClient = docker.from_env(),
    ):
        self._jobName = jobName
        self._job = job
        self._image = image
        self._command = command
        self._container = None
        self._status = JobStatus.PENDING
        self._docker_client = docker_client
        self._error_count = 0
        self._threads = threads
        self._start_time = None
        self._end_time = None
        self._schedulerLogger = schedulerLogger
        JobManager().register_job(self)

    def _handle_interrupt(self, signum, frame):
        logger.info(f"Received interrupt signal {signum} for job {self._jobName}")
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        if self._container is not None:
            try:
                self._container.stop(timeout=5)
                self._container.remove(force=True)
            except docker.errors.NotFound:
                pass
            except Exception as e:
                logger.error(f"Cleanup error for {self._jobName}: {str(e)}")
            finally:
                self._container = None
        JobManager().unregister_job(self)

    def __del__(self):
        self.cleanup()

    def start_job(self, cores: str):
        # return the container
        # docker run --cpuset-cpus="0" -d --rm --name parsec anakli/cca:parsec_blackscholes ./run -a run -S parsec -p blackscholes -i native -n 2

        if self._error_count > 3:
            logger.error(
                f"Job {self._jobName} failed {self._error_count} times, skipping"
            )
            raise Exception(
                f"Job {self._jobName} failed {self._error_count} times, skipping"
            )

        command = []
        for arg in self._command:
            try:
                command.append(arg.format(threads=self._threads))
            except:
                command.append(arg)

        container = self._docker_client.containers.run(
            self._image,
            command,
            cpuset_cpus=cores,
            name=f"{self._jobName}",
            detach=True,
        )

        logger.info(
            f"Job {self._jobName} started with cores {cores} and {self._threads} threads"
        )
        self._schedulerLogger.job_start(self._job, cores.split(","), self._threads)
        self._container = container
        self._status = JobStatus.RUNNING
        self._start_time = time.time()

    def pause_job(self):
        # pause the job
        if self._container is None or self._status != JobStatus.RUNNING:
            raise ValueError(f"Job {self._jobName} is not running")
        self._container.pause()
        logger.info(f"Job {self._jobName} paused")
        self._schedulerLogger.job_pause(self._job)
        self._status = JobStatus.PAUSED

    def unpause_job(self):
        # unpause the job
        if self._container is None or self._status != JobStatus.PAUSED:
            raise ValueError(f"Job {self._jobName} is not paused")
        self._container.unpause()
        logger.info(f"Job {self._jobName} unpaused")
        self._status = JobStatus.RUNNING
        self._schedulerLogger.job_unpause(self._job)

    def update_job_cpus(self, cores: str):
        # update the cpu affinity of the job
        if self._container is None:
            raise ValueError(f"Job {self._jobName} is not running")
        self._container.update(cpuset_cpus=cores)
        logger.info(f"Job {self._jobName} updated to cores {cores}")
        self._schedulerLogger.update_cores(self._job, cores.split(","))

    def check_job_completed(self):
        # check if the job is completed
        if self._container is None:
            raise ValueError(f"Job {self._jobName} is not running")

        container_logs = self._container.logs().decode("utf-8")

        done = "[PARSEC] Done." in container_logs
        error = "Error" in container_logs

        if done and not error:
            self._status = JobStatus.COMPLETED
            self._end_time = time.time()
            logger.info(
                f"Job {self._jobName} completed in {self._end_time - self._start_time} seconds"
            )
            self._schedulerLogger.job_end(self._job)
        elif error:
            self._status = JobStatus.ERROR
            self._error_count += 1
            self._container.remove()
            self._container = None
        elif self._container is None:
            self._status = JobStatus.PENDING

        if self._status == JobStatus.ERROR:
            logger.error(
                f"Job {self._jobName} failed {self._error_count} times, marking as error"
            )
        else:
            logger.info(f"Job {self._jobName} status: {self._status}")

        return self._status
