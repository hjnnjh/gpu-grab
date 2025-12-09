"""Task execution module."""

import logging
import os
import signal
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Task, TaskStatus

logger = logging.getLogger(__name__)


class TaskRunner:
    """Task executor that manages subprocess lifecycle."""

    def __init__(self, logs_dir: Path) -> None:
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.running_processes: dict[str, subprocess.Popen] = {}

    def start_task(self, task: Task, gpu_ids: list[int]) -> bool:
        """Start a task with specified GPU IDs."""
        try:
            # Set up environment with CUDA_VISIBLE_DEVICES
            env = os.environ.copy()
            env.update(task.env)
            env["CUDA_VISIBLE_DEVICES"] = ",".join(map(str, gpu_ids))

            # Set up log file
            log_file = self.logs_dir / f"task_{task.id}.log"
            task.log_file = str(log_file)

            # Start the process
            with open(log_file, "w") as log_f:
                # Write header to log
                log_f.write(f"=== Task: {task.name or task.id} ===\n")
                log_f.write(f"Command: {task.command}\n")
                log_f.write(f"Working dir: {task.working_dir or os.getcwd()}\n")
                log_f.write(f"GPUs: {gpu_ids}\n")
                log_f.write(f"Started: {datetime.now().isoformat()}\n")
                log_f.write("=" * 50 + "\n\n")
                log_f.flush()

                process = subprocess.Popen(
                    task.command,
                    shell=True,
                    cwd=task.working_dir or None,
                    env=env,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,  # Create new session to avoid signal propagation
                )

            task.pid = process.pid
            task.assigned_gpus = gpu_ids
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()

            self.running_processes[task.id] = process
            logger.info(
                f"Started task {task.id} (PID: {process.pid}) on GPUs {gpu_ids}"
            )
            return True

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.finished_at = datetime.now()
            logger.error(f"Failed to start task {task.id}: {e}")
            return False

    def check_task(self, task: Task) -> Optional[int]:
        """
        Check task status.

        Returns:
            Exit code if completed, None if still running.
        """
        if task.id in self.running_processes:
            process = self.running_processes[task.id]
            exit_code = process.poll()

            if exit_code is not None:
                del self.running_processes[task.id]
                logger.debug(f"Task {task.id} exited with code {exit_code}")

            return exit_code

        # Process not in our tracking, check if it's still running via PID
        if task.pid:
            try:
                os.kill(task.pid, 0)  # Check if process exists
                return None  # Still running
            except OSError:
                logger.debug(f"Task {task.id} process {task.pid} no longer exists")
                return -1  # Process doesn't exist

        return -1

    def kill_task(self, task: Task) -> bool:
        """Kill a running task."""
        try:
            if task.id in self.running_processes:
                process = self.running_processes[task.id]
                try:
                    # Kill the entire process group
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass
                del self.running_processes[task.id]
                logger.info(f"Killed task {task.id} (PID: {task.pid})")
                return True
            elif task.pid:
                try:
                    os.killpg(os.getpgid(task.pid), signal.SIGTERM)
                    logger.info(f"Killed task {task.id} (PID: {task.pid})")
                    return True
                except (ProcessLookupError, PermissionError) as e:
                    logger.warning(f"Could not kill task {task.id}: {e}")
        except Exception as e:
            logger.error(f"Error killing task {task.id}: {e}")

        return False

    def get_log_content(
        self, task: Task, tail: int = 100, follow: bool = False
    ) -> str:
        """Get task log content."""
        if not task.log_file:
            return "No log file available"

        log_path = Path(task.log_file)
        if not log_path.exists():
            return "Log file not found"

        try:
            with open(log_path, "r") as f:
                lines = f.readlines()
                if tail > 0:
                    lines = lines[-tail:]
                return "".join(lines)
        except Exception as e:
            return f"Error reading log: {e}"

    def cleanup(self) -> None:
        """Clean up all running processes (for shutdown)."""
        for task_id, process in list(self.running_processes.items()):
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                logger.info(f"Terminated process for task {task_id}")
            except Exception as e:
                logger.warning(f"Error terminating task {task_id}: {e}")
        self.running_processes.clear()
