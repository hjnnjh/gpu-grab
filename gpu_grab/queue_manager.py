"""Task queue management with JSON persistence."""

import fcntl
import json
import logging
from pathlib import Path
from typing import Any, Optional

from .models import Task, TaskStatus

logger = logging.getLogger(__name__)


class QueueManager:
    """Task queue manager with file-based persistence."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.tasks_file = data_dir / "tasks.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Ensure the tasks file exists."""
        if not self.tasks_file.exists():
            self._save_tasks([])

    def _load_tasks(self) -> list[Task]:
        """Load tasks from file."""
        try:
            with open(self.tasks_file, "r") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    return [Task.from_dict(t) for t in data]
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Error loading tasks: {e}, returning empty list")
            return []

    def _save_tasks(self, tasks: list[Task]) -> None:
        """Save tasks to file."""
        with open(self.tasks_file, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                data = [t.to_dict() for t in tasks]
                json.dump(data, f, indent=2, default=str)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def add_task(self, task: Task) -> str:
        """Add a task to the queue."""
        tasks = self._load_tasks()
        tasks.append(task)
        self._save_tasks(tasks)
        logger.info(f"Added task {task.id}: {task.name}")
        return task.id

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a single task by ID."""
        tasks = self._load_tasks()
        for task in tasks:
            if task.id == task_id:
                return task
        return None

    def update_task(self, task: Task) -> None:
        """Update a task."""
        tasks = self._load_tasks()
        for i, t in enumerate(tasks):
            if t.id == task.id:
                tasks[i] = task
                break
        self._save_tasks(tasks)
        logger.debug(f"Updated task {task.id}")

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the queue."""
        tasks = self._load_tasks()
        original_len = len(tasks)
        tasks = [t for t in tasks if t.id != task_id]
        if len(tasks) < original_len:
            self._save_tasks(tasks)
            logger.info(f"Removed task {task_id}")
            return True
        return False

    def get_all_tasks(self) -> list[Task]:
        """Get all tasks."""
        return self._load_tasks()

    def get_pending_tasks(self) -> list[Task]:
        """Get pending tasks sorted by priority."""
        tasks = self._load_tasks()
        pending = [t for t in tasks if t.status == TaskStatus.PENDING]
        return sorted(pending, key=lambda x: (-x.priority, x.created_at))

    def get_running_tasks(self) -> list[Task]:
        """Get running tasks."""
        tasks = self._load_tasks()
        return [t for t in tasks if t.status == TaskStatus.RUNNING]

    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        """Get tasks by status."""
        tasks = self._load_tasks()
        return [t for t in tasks if t.status == status]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        task = self.get_task(task_id)
        if task and task.status == TaskStatus.PENDING:
            from datetime import datetime

            task.status = TaskStatus.CANCELLED
            task.finished_at = datetime.now()
            self.update_task(task)
            logger.info(f"Cancelled task {task_id}")
            return True
        return False

    def get_statistics(self) -> dict[str, Any]:
        """Get queue statistics."""
        tasks = self._load_tasks()
        return {
            "total": len(tasks),
            "pending": len([t for t in tasks if t.status == TaskStatus.PENDING]),
            "running": len([t for t in tasks if t.status == TaskStatus.RUNNING]),
            "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
            "failed": len([t for t in tasks if t.status == TaskStatus.FAILED]),
            "cancelled": len([t for t in tasks if t.status == TaskStatus.CANCELLED]),
        }

    def cleanup_old_tasks(self, max_age_days: int = 7) -> int:
        """Remove completed/failed/cancelled tasks older than max_age_days."""
        from datetime import datetime, timedelta

        tasks = self._load_tasks()
        cutoff = datetime.now() - timedelta(days=max_age_days)
        terminal_states = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}

        original_len = len(tasks)
        tasks = [
            t
            for t in tasks
            if t.status not in terminal_states
            or (t.finished_at and t.finished_at > cutoff)
        ]
        removed = original_len - len(tasks)

        if removed > 0:
            self._save_tasks(tasks)
            logger.info(f"Cleaned up {removed} old tasks")

        return removed
