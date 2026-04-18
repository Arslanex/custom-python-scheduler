import threading
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Callable, Optional

from .cron_schedule import next_fire

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class JobResult:
    name: str
    status: JobStatus
    started: datetime
    finished: datetime
    duration: float
    error: Optional[str] = None


@dataclass
class Job:
    name: str
    func: Callable
    interval: float
    cron: str = ""
    enabled: bool = True
    max_runs: int = 0
    timeout: float = 0.0

    _runs: int = field(default=0, init=False, repr=False)
    _status: JobStatus = field(default=JobStatus.PENDING, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _next_at: datetime = field(default_factory=datetime.now, init=False, repr=False)

    def __post_init__(self) -> None:
        cron = self.cron.strip()
        if cron:
            self._next_at = next_fire(cron, datetime.now())

    @property
    def status(self) -> JobStatus:
        with self._lock:
            return self._status

    @status.setter
    def status(self, value: JobStatus) -> None:
        with self._lock:
            self._status = value

    @property
    def runs(self) -> int:
        with self._lock:
            return self._runs

    def increment_runs(self) -> None:
        with self._lock:
            self._runs += 1

    def set_enabled(self, value: bool) -> None:
        with self._lock:
            self.enabled = value

    def is_due(self) -> bool:
        with self._lock:
            return self.enabled and datetime.now() >= self._next_at

    def schedule_next(self) -> None:
        with self._lock:
            cron = self.cron.strip()
            if cron:
                self._next_at = next_fire(cron, datetime.now())
            else:
                self._next_at = datetime.now() + timedelta(seconds=self.interval)

    def monitoring_row(self) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "cron": self.cron or f"her {self.interval}s",
                "enabled": self.enabled,
                "status": self._status.value,
                "runs": self._runs,
                "next_in": max(
                    0.0,
                    (self._next_at - datetime.now()).total_seconds(),
                ),
            }
