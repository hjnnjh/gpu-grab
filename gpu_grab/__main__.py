"""Service entry point."""

import logging
import signal
import sys
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any

from .config import Config
from .models import GPURequirement, Task, TaskStatus
from .scheduler import Scheduler
from .server import UnixSocketServer

logger = logging.getLogger(__name__)


def setup_logging(config: Config) -> None:
    """Configure logging."""
    if not config.logs_dir:
        return

    config.logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = config.logs_dir / "gpu-grab.log"

    handler = RotatingFileHandler(
        log_file,
        maxBytes=config.log_max_size_mb * 1024 * 1024,
        backupCount=config.log_backup_count,
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level))
    root_logger.addHandler(handler)

    # Output to stdout as well (captured by systemd)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    root_logger.addHandler(stdout_handler)


def main() -> None:
    """Main service function."""
    config = Config.load()
    setup_logging(config)

    logger.info("GPU Grab Service starting...")

    scheduler = Scheduler(config)

    # Request handlers
    def handle_submit(**params: Any) -> dict[str, Any]:
        req = GPURequirement(
            gpu_ids=params.get("gpu_ids"),
            min_free_memory_gb=params.get("min_free_memory_gb", 0),
            max_util_percent=params.get("max_util_percent", 100),
            gpu_count=params.get("gpu_count", 1),
        )
        task = Task(
            name=params.get("name", ""),
            command=params["command"],
            working_dir=params.get("working_dir", ""),
            env=params.get("env", {}),
            requirements=req,
            priority=params.get("priority", 0),
        )
        task_id = scheduler.queue_manager.add_task(task)
        return {"task_id": task_id}

    def handle_status() -> dict[str, Any]:
        return scheduler.get_status()

    def handle_list(status_filter: str = "all") -> dict[str, Any]:
        tasks = scheduler.queue_manager.get_all_tasks()
        if status_filter != "all":
            tasks = [t for t in tasks if t.status.value == status_filter]
        return {
            "tasks": [t.to_dict() for t in tasks]
        }

    def handle_cancel(task_id: str) -> dict[str, Any]:
        task = scheduler.queue_manager.get_task(task_id)
        if task and task.status == TaskStatus.RUNNING:
            scheduler.task_runner.kill_task(task)
            task.status = TaskStatus.CANCELLED
            task.finished_at = datetime.now()
            scheduler.queue_manager.update_task(task)
            return {"cancelled": True}
        elif task:
            success = scheduler.queue_manager.cancel_task(task_id)
            return {"cancelled": success}
        return {"cancelled": False, "error": "Task not found"}

    def handle_logs(
        task_id: str, tail: int = 100, follow: bool = False
    ) -> dict[str, Any]:
        task = scheduler.queue_manager.get_task(task_id)
        if not task:
            return {"logs": "Task not found"}

        logs = scheduler.task_runner.get_log_content(task, tail, follow)
        return {"logs": logs}

    handlers = {
        "submit": handle_submit,
        "status": handle_status,
        "list": handle_list,
        "cancel": handle_cancel,
        "logs": handle_logs,
    }

    server = UnixSocketServer(config.socket_path, handlers)

    # Signal handling
    def signal_handler(signum: int, frame: Any) -> None:
        logger.info(f"Received signal {signum}, shutting down...")
        server.stop()
        scheduler.stop()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start server in thread
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()

    # Run scheduler in main thread
    try:
        scheduler.start()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        logger.info("GPU Grab Service stopped")


if __name__ == "__main__":
    main()
