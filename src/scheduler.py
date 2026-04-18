import logging
import threading
from datetime import datetime, timezone
from typing import Callable, Optional

from .dto import Job, JobResult, JobStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
_log = logging.getLogger("scheduler")


class Scheduler:
    def __init__(self, tick: float = 1.0, max_workers: int = 10):
        self._lock: threading.RLock = threading.RLock()
        self._stop: threading.Event = threading.Event()
        self._sem: threading.BoundedSemaphore = threading.BoundedSemaphore(max_workers)
        self._thread: Optional[threading.Thread] = None

        self._jobs: dict[str, Job] = {}
        self._results: list[JobResult] = []
        self._tick: float = tick

        self._hooks_on_success: list[Callable] = []
        self._hooks_on_failure: list[Callable] = []

    # ── Base Functions (for jobs) ────────────────────────────────────────

    def add(self, job: Job) -> bool:
        with self._lock:
            # -VALIDATION- | Job zaten eklenmiş mi?
            if job.name in self._jobs:
                _log.warning(f"Job with name {job.name} already exists")
                return False

            # -ACTION- | Job Scheduler'a ekle
            self._jobs[job.name] = job
            _log.info(f"Job {job.name} added to scheduler")
        return True

    def remove(self, name: str) -> bool:
        with self._lock:
            # -VALIDATION- | Job var mı?
            if name not in self._jobs:
                _log.warning(f"Job with name {name} not found")
                return False

            # -ACTION- | Job Scheduler'dan sil
            del self._jobs[name]
            _log.info(f"Job {name} removed from scheduler")
        return True

    def get(self, name: str) -> Optional[Job]:
        with self._lock:
            if name not in self._jobs:
                _log.warning(f"Job with name {name} not found")
                return None
            return self._jobs.get(name)

    def get_all(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def activate(self, name: str) -> bool:
        with self._lock:
            job = self._jobs.get(name)
            if job is None:
                _log.warning(f"Job with name {name} not found")
                return False
        job.set_enabled(True)
        _log.info(f"Job {name} activated")
        return True

    def deactivate(self, name: str) -> bool:
        with self._lock:
            job = self._jobs.get(name)
            if job is None:
                _log.warning(f"Job with name {name} not found")
                return False
        job.set_enabled(False)
        _log.info(f"Job {name} deactivated")
        return True

    # ── Internal Functions ────────────────────────────────────────────────

    def _record(self, result: JobResult):
        with self._lock:
            self._results.append(result)
            if len(self._results) > 1000:    # bellek sınırı
                self._results = self._results[-1000:]

    @staticmethod
    def _safe_call(fn, *args):
        try:
            fn(*args)
        except Exception as e:
            _log.error("hook hatası: %s", e)

    def _run_job(self, job: Job) -> None:
        with job._lock:
            if job.status is JobStatus.RUNNING:
                _log.warning(f"Job {job.name} is already running")
                return
            job.status = JobStatus.RUNNING

        start_time = datetime.now(timezone.utc)
        _log.info(f"Job {job.name} started at {start_time}")

        results: list = [None]
        exception: list = [None]

        def target() -> None:
            try:
                results[0] = job.func()
            except Exception as e:
                exception[0] = e

        worker = threading.Thread(target=target, daemon=True)
        worker.start()
        join_timeout = None if job.timeout <= 0 else job.timeout
        worker.join(timeout=join_timeout)

        try:
            if worker.is_alive():
                _log.warning(f"Job {job.name} timed out after {job.timeout} seconds")
                raise TimeoutError(f"Job {job.name} timed out after {job.timeout} seconds")
            if exception[0] is not None:
                _log.error(f"Job {job.name} failed with exception: {exception[0]}")
                raise exception[0]

            job.status = JobStatus.SUCCESS
            job.increment_runs()

            finished_time = datetime.now(timezone.utc)
            duration = finished_time - start_time

            result = JobResult(
                name=job.name,
                status=job.status,
                started=start_time,
                finished=finished_time,
                duration=duration.total_seconds(),
                error=None,
            )
            self._record(result)
            _log.info(f"Job {job.name} finished in {duration.total_seconds()} seconds")

            with self._lock:
                hooks = tuple(self._hooks_on_success)
            for hook in hooks:
                self._safe_call(hook, result)
        except Exception as e:
            job.status = JobStatus.FAILED
            job.increment_runs()

            finished_time = datetime.now(timezone.utc)
            duration = finished_time - start_time

            result = JobResult(
                name=job.name,
                status=job.status,
                started=start_time,
                finished=finished_time,
                duration=duration.total_seconds(),
                error=str(e),
            )
            self._record(result)
            _log.error(f"Job {job.name} failed in {duration.total_seconds()} seconds with exception: {e}")

            with self._lock:
                hooks = tuple(self._hooks_on_failure)
            for hook in hooks:
                self._safe_call(hook, result)
        finally:
            with job._lock:
                if job.max_runs and job._runs >= job.max_runs:
                    job.enabled = False
                    _log.info(f"Job {job.name} reached max runs ({job.max_runs}) and is disabled")
                else:
                    job.status = JobStatus.PENDING
                    job.schedule_next()
                    _log.info(f"Job {job.name} scheduled next run at {job._next_at}")

    def trigger(self, name: str) -> None:
        with self._lock:
            job = self._jobs.get(name)
        if not job:
            _log.warning(f"Job with name {name} not found")
            return

        self._sem.acquire()

        def runner() -> None:
            try:
                self._run_job(job)
            finally:
                self._sem.release()

        threading.Thread(target=runner, daemon=True, name=f"job-{name}").start()

    def _tick_jobs(self) -> None:
        with self._lock:
            due_names = [j.name for j in self._jobs.values() if j.is_due()]
        for name in due_names:
            self.trigger(name)

    def _loop(self) -> None:
        _log.info("Scheduler loop started (tick=%ss)", self._tick)
        while not self._stop.is_set():
            self._tick_jobs()
            if self._stop.wait(timeout=self._tick):
                break
        _log.info("Scheduler loop stopped")

    # ── Hooks ──────────────────────────────────────────────────────────

    def on_success(self, fn: Callable) -> "Scheduler":
        with self._lock:
            self._hooks_on_success.append(fn)
        return self

    def on_failure(self, fn: Callable) -> "Scheduler":
        with self._lock:
            self._hooks_on_failure.append(fn)
        return self

    # ── Main Loop ───────────────────────────────────────────────────────

    def start(self, block: bool = False) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                _log.warning("Scheduler already running")
                return
            self._stop.clear()
            t = threading.Thread(target=self._loop, daemon=True, name="scheduler-loop")
            self._thread = t
        t.start()
        _log.info("Scheduler started (tick=%ss)", self._tick)
        if block:
            t.join()

    def stop(self, join_timeout: float | None = 30.0) -> None:
        self._stop.set()
        with self._lock:
            t = self._thread
        if t is not None and t.is_alive():
            t.join(timeout=join_timeout)
            if t.is_alive():
                _log.warning(
                    "Scheduler loop thread did not finish within %ss",
                    join_timeout,
                )
        with self._lock:
            self._thread = None
        _log.info("Scheduler stopped")

    def __enter__(self) -> "Scheduler":
        self.start(block=False)
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()

    # ── Monitoring ──────────────────────────────────────────────────────

    def status(self) -> list[dict]:
        with self._lock:
            jobs = list(self._jobs.values())
        return [j.monitoring_row() for j in jobs]

    def history(self, name: str | None = None, limit: int = 20) -> list[JobResult]:
        with self._lock:
            all_results = list(self._results)
        if name:
            filtered = [r for r in all_results if r.name == name]
            data = filtered[-limit:]
        else:
            data = all_results[-limit:]
        return list(reversed(data))

# ── Default Scheduler ────────────────────────────────────────────────

_default_scheduler: Optional[Scheduler] = None

def get_scheduler() -> Scheduler:
    global _default_scheduler
    if _default_scheduler is None:
        _default_scheduler = Scheduler()
    return _default_scheduler
 
def schedule(
    cron: str = "",
    interval: float = 60.0,
    timeout: float = 0,
    max_runs: int = 0,
):

    def decorator(fn: Callable):
        job = Job(
            name=fn.__name__,
            func=fn,
            interval=interval,
            cron=cron,
            timeout=timeout,
            max_runs=max_runs,
        )
        get_scheduler().add(job)
        return fn

    return decorator