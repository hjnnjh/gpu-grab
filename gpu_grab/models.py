"""Data models for GPU Grab."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class TaskStatus(Enum):
    """Task status enumeration."""

    PENDING = "pending"  # Waiting to be scheduled
    RUNNING = "running"  # Currently running
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"  # Execution failed
    CANCELLED = "cancelled"  # Cancelled by user


@dataclass
class GPURequirement:
    """GPU resource requirements."""

    gpu_ids: Optional[list[int]] = None  # Specific GPU IDs, None means any
    min_free_memory_gb: float = 0.0  # Minimum free memory (GB)
    max_util_percent: float = 100.0  # Maximum allowed utilization
    gpu_count: int = 1  # Number of GPUs required

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gpu_ids": self.gpu_ids,
            "min_free_memory_gb": self.min_free_memory_gb,
            "max_util_percent": self.max_util_percent,
            "gpu_count": self.gpu_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GPURequirement":
        """Create from dictionary."""
        return cls(
            gpu_ids=data.get("gpu_ids"),
            min_free_memory_gb=data.get("min_free_memory_gb", 0.0),
            max_util_percent=data.get("max_util_percent", 100.0),
            gpu_count=data.get("gpu_count", 1),
        )


@dataclass
class Task:
    """Training task."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    command: str = ""
    working_dir: str = ""
    env: dict[str, str] = field(default_factory=dict)
    requirements: GPURequirement = field(default_factory=GPURequirement)

    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0  # Higher = more urgent

    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    assigned_gpus: list[int] = field(default_factory=list)
    pid: Optional[int] = None
    exit_code: Optional[int] = None
    error_message: str = ""
    log_file: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "working_dir": self.working_dir,
            "env": self.env,
            "requirements": self.requirements.to_dict(),
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "assigned_gpus": self.assigned_gpus,
            "pid": self.pid,
            "exit_code": self.exit_code,
            "error_message": self.error_message,
            "log_file": self.log_file,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            command=data.get("command", ""),
            working_dir=data.get("working_dir", ""),
            env=data.get("env", {}),
            requirements=GPURequirement.from_dict(data.get("requirements", {})),
            status=TaskStatus(data.get("status", "pending")),
            priority=data.get("priority", 0),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else datetime.now(),
            started_at=datetime.fromisoformat(data["started_at"])
            if data.get("started_at")
            else None,
            finished_at=datetime.fromisoformat(data["finished_at"])
            if data.get("finished_at")
            else None,
            assigned_gpus=data.get("assigned_gpus", []),
            pid=data.get("pid"),
            exit_code=data.get("exit_code"),
            error_message=data.get("error_message", ""),
            log_file=data.get("log_file", ""),
        )


@dataclass
class GPUStatus:
    """GPU status information."""

    index: int
    name: str
    total_memory_mb: int
    used_memory_mb: int
    free_memory_mb: int
    utilization_percent: int
    temperature: int = 0

    @property
    def free_memory_gb(self) -> float:
        """Get free memory in GB."""
        return self.free_memory_mb / 1024.0

    @property
    def is_idle(self) -> bool:
        """Check if GPU is idle (utilization < 5%)."""
        return self.utilization_percent < 5

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "index": self.index,
            "name": self.name,
            "total_memory_mb": self.total_memory_mb,
            "used_memory_mb": self.used_memory_mb,
            "free_memory_mb": self.free_memory_mb,
            "free_memory_gb": round(self.free_memory_gb, 2),
            "utilization_percent": self.utilization_percent,
            "temperature": self.temperature,
            "is_idle": self.is_idle,
        }
