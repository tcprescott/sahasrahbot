"""In-process job scheduler.

Runs SahasrahBot's periodic jobs on the main asyncio loop, so they don't live inside
discord.py's ``tasks`` engine or a cog. Jobs are plain async callables registered with
an interval. ``sahasrahbot.py`` creates the scheduler, registers the jobs and starts it.

Semantics match the ``discord.ext.tasks`` loops they replace: a job runs once when it
starts (after its ``wait_for`` gate, if any), then every ``interval`` seconds measured
from the start of the previous run. A job never overlaps itself, and an exception is
logged and does not stop the job.
"""
import asyncio
import dataclasses
import logging
import time
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

JobFunc = Callable[[], Awaitable[None]]
Gate = Callable[[], Awaitable[object]]


@dataclasses.dataclass
class Job:
    name: str
    func: JobFunc
    interval: float
    wait_for: Optional[Gate] = None
    runs: int = 0
    failures: int = 0
    last_started: Optional[float] = None
    last_error: Optional[BaseException] = None


class Scheduler:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    @property
    def jobs(self) -> dict[str, Job]:
        return dict(self._jobs)

    @property
    def running(self) -> bool:
        return any(not task.done() for task in self._tasks.values())

    def add_interval_job(self, name: str, func: JobFunc, *, seconds: float,
                         wait_for: Optional[Gate] = None) -> Job:
        """Register ``func`` to run every ``seconds`` seconds.

        ``wait_for`` is awaited once before the first run, for example the Discord
        client's ``wait_until_ready`` for a job whose output goes to Discord.
        """
        if name in self._jobs:
            raise ValueError(f"A job named {name!r} is already registered.")
        if seconds <= 0:
            raise ValueError("A job's interval must be positive.")
        job = Job(name=name, func=func, interval=float(seconds), wait_for=wait_for)
        self._jobs[name] = job
        self._locks[name] = asyncio.Lock()
        if self.running:
            self._start_job(job)
        return job

    def start(self) -> None:
        """Start every registered job that isn't already running. Needs a running loop."""
        for job in self._jobs.values():
            task = self._tasks.get(job.name)
            if task is None or task.done():
                self._start_job(job)

    async def stop(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    async def run_now(self, name: str) -> None:
        """Run one job immediately, outside its schedule, and wait for it.

        Waits for the job's current run, if one is in progress, rather than overlapping it.
        """
        await self._run_once(self._jobs[name])

    def _start_job(self, job: Job) -> None:
        self._tasks[job.name] = asyncio.get_running_loop().create_task(
            self._loop(job), name=f"scheduler:{job.name}")

    async def _loop(self, job: Job) -> None:
        if job.wait_for is not None:
            logger.info("Scheduled job %s waiting to start...", job.name)
            await job.wait_for()
        logger.info("Scheduled job %s started, every %ss", job.name, job.interval)
        while True:
            started = time.monotonic()
            await self._run_once(job)
            elapsed = time.monotonic() - started
            await asyncio.sleep(max(0.0, job.interval - elapsed))

    async def _run_once(self, job: Job) -> None:
        async with self._locks[job.name]:
            job.last_started = time.time()
            job.runs += 1
            try:
                await job.func()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                job.failures += 1
                job.last_error = e
                logger.exception("Scheduled job %s failed", job.name)
