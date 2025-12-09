"""Main task scheduler."""

import logging
import threading
import time
from datetime import datetime
from typing import Any, Optional

from .config import Config
from .gpu_monitor import GPUMonitor
from .models import TaskStatus
from .queue_manager import QueueManager
from .task_runner import TaskRunner

logger = logging.getLogger(__name__)


class Scheduler:
    """Main scheduler for managing GPU tasks."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.gpu_monitor = GPUMonitor()
        # Ensure directories are correctly set from config
        self.queue_manager = QueueManager(config.data_dir)
        self.task_runner = TaskRunner(config.logs_dir)

        self._running = False
        self._lock = threading.Lock()
        self.start_time: Optional[datetime] = None

    def start(self) -> None:
        """Start the scheduler loop."""
        self._running = True
        self.start_time = datetime.now()
        self.gpu_monitor.initialize()

        logger.info("GPU Grab Scheduler started")
        logger.info(f"Checking interval: {self.config.check_interval}s")
        logger.info(f"Max concurrent tasks: {self.config.max_concurrent_tasks}")

        try:
            while self._running:
                try:
                    self._tick()
                except Exception as e:
                    logger.exception(f"Error in scheduler tick: {e}")
                time.sleep(self.config.check_interval)
        finally:
            self.task_runner.cleanup()
            self.gpu_monitor.shutdown()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        logger.info("GPU Grab Scheduler stopping...")

    def _tick(self) -> None:
        """Single iteration of the scheduling loop."""
        with self._lock:
            # 1. Check running tasks
            self._check_running_tasks()

            # 2. Schedule pending tasks
            self._schedule_pending_tasks()

    def _check_running_tasks(self) -> None:
        """Check status of currently running tasks."""
        running_tasks = self.queue_manager.get_running_tasks()

        for task in running_tasks:
            exit_code = self.task_runner.check_task(task)

            if exit_code is not None:
                task.exit_code = exit_code
                task.finished_at = datetime.now()

                if exit_code == 0:
                    task.status = TaskStatus.COMPLETED
                    logger.info(f"Task {task.id} completed successfully")
                else:
                    task.status = TaskStatus.FAILED
                    task.error_message = f"Process exited with code {exit_code}"
                    logger.warning(
                        f"Task {task.id} failed: {task.error_message}"
                    )

                self.queue_manager.update_task(task)

    def _schedule_pending_tasks(self) -> None:
        """Schedule pending tasks if resources are available."""
        # Check concurrency limit
        running_tasks = self.queue_manager.get_running_tasks()
        if len(running_tasks) >= self.config.max_concurrent_tasks:
            logger.debug("Max concurrent tasks reached, skipping scheduling")
            return

        pending_tasks = self.queue_manager.get_pending_tasks()
        if not pending_tasks:
            return

        logger.debug(f"Found {len(pending_tasks)} pending tasks")

        for task in pending_tasks:
            # Check concurrency limit again (in case we started tasks in this loop)
            if (
                len(self.queue_manager.get_running_tasks())
                >= self.config.max_concurrent_tasks
            ):
                break

            # Check if GPU resources are available
            available_gpus = self.gpu_monitor.check_requirements(task.requirements)

            if available_gpus:
                logger.info(
                    f"Scheduling task {task.id} ('{task.name}') on GPUs {available_gpus}"
                )

                if self.task_runner.start_task(task, available_gpus):
                    self.queue_manager.update_task(task)
                else:
                    self.queue_manager.update_task(task)
                    logger.error(f"Failed to start task {task.id}")
            else:
                logger.debug(f"No suitable GPUs for task {task.id}")

    def get_status(self) -> dict[str, Any]:
        """Get current system status."""
        stats = self.queue_manager.get_statistics()
        try:
            gpus = self.gpu_monitor.get_all_gpu_status()
            gpu_data = [g.to_dict() for g in gpus]
        except Exception as e:
            logger.error(f"Error getting GPU status: {e}")
            gpu_data = []

        uptime = 0.0
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            "running": self._running,
            "uptime_seconds": uptime,
            "tasks": stats,
            "gpus": gpu_data,
            "last_check": datetime.now().isoformat(),
            "config": {
                "check_interval": self.config.check_interval,
                "max_concurrent_tasks": self.config.max_concurrent_tasks,
            },
        }
