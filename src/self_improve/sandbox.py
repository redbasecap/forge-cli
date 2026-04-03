"""MicroVM sandbox — lightweight VM isolation for parallel task execution."""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MicroVMSandbox:
    """Manages MicroVM instances for isolated, parallel task execution.

    Falls back to subprocess execution when the ``microvm`` binary is not
    installed.

    Parameters
    ----------
    max_parallel : int
        Maximum number of VMs to run concurrently.
    memory_mb : int
        DRAM allocation per VM in megabytes.
    vm_timeout : int
        Per-VM timeout in seconds.  The VM is killed if the task exceeds this.
    """

    max_parallel: int = 10
    memory_mb: int = 64
    vm_timeout: int = 120

    _semaphore: asyncio.Semaphore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._semaphore = asyncio.Semaphore(self.max_parallel)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return *True* if the ``microvm`` binary is on ``$PATH``."""
        return shutil.which("microvm") is not None

    def status(self) -> dict:
        """Return a summary dict suitable for CLI display."""
        available = self.is_available()
        return {
            "available": available,
            "binary": shutil.which("microvm") or "not found",
            "max_parallel": self.max_parallel,
            "memory_mb": self.memory_mb,
            "vm_timeout": self.vm_timeout,
            "mode": "microvm" if available else "subprocess (fallback)",
        }

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    async def run_task(self, task: dict, *, runner: object | None = None) -> dict:
        """Run a single task inside an isolated MicroVM (or subprocess fallback).

        Parameters
        ----------
        task : dict
            Task descriptor as returned by :pymethod:`TaskRunner.discover_tasks`.
        runner : TaskRunner | None
            A :class:`TaskRunner` used for the subprocess fallback path.
        """
        async with self._semaphore:
            if self.is_available():
                return await self._run_in_vm(task)
            return await self._run_in_subprocess(task, runner)

    async def run_tasks_parallel(
        self, tasks: list[dict], *, runner: object | None = None
    ) -> list[dict]:
        """Run *tasks* in parallel (up to *max_parallel* concurrently).

        Results are returned in the same order as *tasks*.
        """
        coros = [self.run_task(t, runner=runner) for t in tasks]
        return list(await asyncio.gather(*coros))

    # ------------------------------------------------------------------
    # VM execution path
    # ------------------------------------------------------------------

    async def _run_in_vm(self, task: dict) -> dict:
        """Execute *task* in a MicroVM instance."""
        from pathlib import Path

        task_dir = Path(task["path"])
        test_script = task_dir / "tests" / "test.sh"
        name = task["name"]

        if not test_script.exists():
            return {
                "name": name,
                "passed": False,
                "score": 0.0,
                "output": f"test script not found: {test_script}",
                "duration": 0.0,
            }

        cmd = [
            "microvm",
            "--memory", f"{self.memory_mb}M",
            "--timeout", str(self.vm_timeout),
            "--mount", f"{task_dir}:/task",
            "--exec", f"/task/tests/test.sh",
        ]

        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(task_dir),
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.vm_timeout
            )
            elapsed = time.monotonic() - start
            passed = proc.returncode == 0
            output = (stdout or b"").decode() + (stderr or b"").decode()
            return {
                "name": name,
                "passed": passed,
                "score": 1.0 if passed else 0.0,
                "output": output.strip(),
                "duration": round(elapsed, 3),
            }
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start
            logger.warning("VM timed out for task %s after %ds", name, self.vm_timeout)
            return {
                "name": name,
                "passed": False,
                "score": 0.0,
                "output": f"VM timed out after {self.vm_timeout}s",
                "duration": round(elapsed, 3),
            }
        except FileNotFoundError:
            elapsed = time.monotonic() - start
            return {
                "name": name,
                "passed": False,
                "score": 0.0,
                "output": "microvm binary not found",
                "duration": round(elapsed, 3),
            }
        except Exception as exc:
            elapsed = time.monotonic() - start
            return {
                "name": name,
                "passed": False,
                "score": 0.0,
                "output": f"VM error: {exc}",
                "duration": round(elapsed, 3),
            }

    # ------------------------------------------------------------------
    # Subprocess fallback path
    # ------------------------------------------------------------------

    async def _run_in_subprocess(
        self, task: dict, runner: object | None
    ) -> dict:
        """Fall back to async subprocess execution (no VM)."""
        from pathlib import Path

        task_dir = Path(task["path"])
        test_script = task_dir / "tests" / "test.sh"
        name = task["name"]
        timeout = task.get("timeout", self.vm_timeout)

        if not test_script.exists():
            return {
                "name": name,
                "passed": False,
                "score": 0.0,
                "output": f"test script not found: {test_script}",
                "duration": 0.0,
            }

        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                "bash", str(test_script),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(task_dir),
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            elapsed = time.monotonic() - start
            passed = proc.returncode == 0
            output = (stdout or b"").decode() + (stderr or b"").decode()
            return {
                "name": name,
                "passed": passed,
                "score": 1.0 if passed else 0.0,
                "output": output.strip(),
                "duration": round(elapsed, 3),
            }
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start
            return {
                "name": name,
                "passed": False,
                "score": 0.0,
                "output": f"task timed out after {timeout}s",
                "duration": round(elapsed, 3),
            }
        except Exception as exc:
            elapsed = time.monotonic() - start
            return {
                "name": name,
                "passed": False,
                "score": 0.0,
                "output": f"unexpected error: {exc}",
                "duration": round(elapsed, 3),
            }
