"""Guarded background rebuild.

Design:
  * The actual runner is an INJECTABLE callable (`RunnerFn`). The default
    (`subprocess_runner`) shells out to PIPELINE_CMD with cwd=DATA_DIR -- that is
    the SEPARATE process where pandas/core.py load. The web process never imports
    pandas. Tests inject a fake runner so the real pipeline never runs.
  * Jobs are tracked in a thread-safe in-memory registry.
  * Only ONE job may be active (queued/running) at a time -> Conflict (409) otherwise.
  * Each job runs on a daemon thread; status transitions queued -> running ->
    succeeded|failed, capturing returncode + a tail of combined output.
"""
from __future__ import annotations

import subprocess
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Callable, Deque, Dict, List, Optional

from app.errors import Conflict, NotFound

# A runner takes (cmd, cwd) and yields output lines; it returns the process exit code.
RunnerFn = Callable[[List[str], str], "RunnerResult"]

_LOG_TAIL_MAX = 50


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class RunnerResult:
    """Result of a runner invocation."""
    def __init__(self, returncode: int, log_lines: List[str]) -> None:
        self.returncode = returncode
        self.log_lines = log_lines


def subprocess_runner(cmd: List[str], cwd: str) -> RunnerResult:
    """Default runner: shell the pipeline in a SEPARATE process (pandas lives there)."""
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    lines = (proc.stdout or "").splitlines()
    return RunnerResult(returncode=proc.returncode, log_lines=lines[-_LOG_TAIL_MAX:])


class Job:
    __slots__ = ("job_id", "status", "started_at", "finished_at", "returncode", "log_tail")

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        self.status = "queued"  # queued|running|succeeded|failed
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.returncode: Optional[int] = None
        self.log_tail: List[str] = []

    def view(self) -> Dict[str, object]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "returncode": self.returncode,
            "log_tail": list(self.log_tail),
        }


class RebuildManager:
    """Thread-safe registry + launcher for rebuild jobs."""

    def __init__(self, cmd: List[str], cwd: str, runner: RunnerFn = subprocess_runner) -> None:
        self._cmd = cmd
        self._cwd = cwd
        self._runner = runner
        self._lock = threading.Lock()
        self._jobs: Dict[str, Job] = {}
        self._order: Deque[str] = deque(maxlen=200)  # bound memory; keep recent jobs
        self._active_id: Optional[str] = None

    def _active(self) -> bool:
        if self._active_id is None:
            return False
        job = self._jobs.get(self._active_id)
        return job is not None and job.status in ("queued", "running")

    def start(self) -> Job:
        """Create + launch a job, or raise Conflict if one is already active."""
        with self._lock:
            if self._active():
                raise Conflict(
                    "A rebuild is already in progress.",
                    code="rebuild_in_progress",
                    details=[{"active_job_id": self._active_id}],
                )
            job = Job(uuid.uuid4().hex)
            self._jobs[job.job_id] = job
            self._order.append(job.job_id)
            self._active_id = job.job_id

        t = threading.Thread(target=self._run, args=(job.job_id,), daemon=True)
        t.start()
        return job

    def _run(self, job_id: str) -> None:
        job = self._jobs[job_id]
        with self._lock:
            job.status = "running"
            job.started_at = _now()
        try:
            result = self._runner(self._cmd, self._cwd)
            with self._lock:
                job.returncode = result.returncode
                job.log_tail = list(result.log_lines)[-_LOG_TAIL_MAX:]
                job.status = "succeeded" if result.returncode == 0 else "failed"
        except Exception as exc:  # runner blew up; record as failed, don't crash the thread
            with self._lock:
                job.status = "failed"
                job.returncode = -1
                job.log_tail = [f"runner error: {exc!r}"]
        finally:
            with self._lock:
                job.finished_at = _now()
                if self._active_id == job_id:
                    self._active_id = None

    def get(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise NotFound(f"No rebuild job with id '{job_id}'.", code="job_not_found")
        return job
