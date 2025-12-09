"""Configuration management for GPU Grab."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Config:
    """System configuration."""

    # Path configuration
    base_dir: Path = field(default_factory=lambda: Path.home() / ".gpu-grab")
    data_dir: Optional[Path] = None
    logs_dir: Optional[Path] = None
    socket_path: Optional[Path] = None

    # Scheduling configuration
    check_interval: float = 10.0  # GPU check interval (seconds)
    max_concurrent_tasks: int = 4  # Max concurrent tasks

    # Logging configuration
    log_level: str = "INFO"
    log_max_size_mb: int = 10
    log_backup_count: int = 5

    # Default task configuration
    default_gpu_count: int = 1
    default_min_memory_gb: float = 0.0
    default_max_util_percent: float = 100.0

    def __post_init__(self) -> None:
        if self.data_dir is None:
            self.data_dir = self.base_dir / "data"
        if self.logs_dir is None:
            self.logs_dir = self.base_dir / "logs"
        if self.socket_path is None:
            self.socket_path = self.base_dir / "gpu-grab.sock"

    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> "Config":
        """Load configuration from file."""
        config = cls()

        if config_file is None:
            config_file = config.base_dir / "config.yaml"

        if config_file.exists():
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}

            for key, value in data.items():
                if hasattr(config, key):
                    if key.endswith("_dir") or key.endswith("_path"):
                        value = Path(value)
                    setattr(config, key, value)

        # Ensure __post_init__ is applied after loading
        config.__post_init__()
        return config

    def save(self, config_file: Optional[Path] = None) -> None:
        """Save configuration to file."""
        if config_file is None:
            config_file = self.base_dir / "config.yaml"

        config_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "check_interval": self.check_interval,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "log_level": self.log_level,
            "log_max_size_mb": self.log_max_size_mb,
            "log_backup_count": self.log_backup_count,
            "default_gpu_count": self.default_gpu_count,
            "default_min_memory_gb": self.default_min_memory_gb,
            "default_max_util_percent": self.default_max_util_percent,
        }

        with open(config_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
