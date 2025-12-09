"""GPU monitoring module using pynvml."""

import logging
from typing import Optional

from pynvml import (
    NVMLError,
    nvmlDeviceGetCount,
    nvmlDeviceGetHandleByIndex,
    nvmlDeviceGetMemoryInfo,
    nvmlDeviceGetName,
    nvmlDeviceGetTemperature,
    nvmlDeviceGetUtilizationRates,
    nvmlInit,
    nvmlShutdown,
    NVML_TEMPERATURE_GPU,
)

from .models import GPURequirement, GPUStatus

logger = logging.getLogger(__name__)


class GPUMonitor:
    """GPU status monitor using NVML."""

    def __init__(self) -> None:
        self._initialized = False

    def initialize(self) -> None:
        """Initialize NVML."""
        if not self._initialized:
            try:
                nvmlInit()
                self._initialized = True
                logger.info("NVML initialized successfully")
            except NVMLError as e:
                logger.error(f"Failed to initialize NVML: {e}")
                raise

    def shutdown(self) -> None:
        """Shutdown NVML."""
        if self._initialized:
            try:
                nvmlShutdown()
                self._initialized = False
                logger.info("NVML shutdown")
            except NVMLError as e:
                logger.warning(f"Error shutting down NVML: {e}")

    def get_gpu_count(self) -> int:
        """Get the number of GPUs."""
        self.initialize()
        try:
            return nvmlDeviceGetCount()
        except NVMLError as e:
            logger.error(f"Failed to get GPU count: {e}")
            return 0

    def get_gpu_status(self, index: int) -> GPUStatus:
        """Get status of a single GPU."""
        self.initialize()
        try:
            handle = nvmlDeviceGetHandleByIndex(index)

            name = nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8")

            memory = nvmlDeviceGetMemoryInfo(handle)
            util = nvmlDeviceGetUtilizationRates(handle)
            temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)

            return GPUStatus(
                index=index,
                name=name,
                total_memory_mb=memory.total // (1024 * 1024),
                used_memory_mb=memory.used // (1024 * 1024),
                free_memory_mb=memory.free // (1024 * 1024),
                utilization_percent=util.gpu,
                temperature=temp,
            )
        except NVMLError as e:
            logger.error(f"Failed to get GPU {index} status: {e}")
            raise

    def get_all_gpu_status(self) -> list[GPUStatus]:
        """Get status of all GPUs."""
        count = self.get_gpu_count()
        return [self.get_gpu_status(i) for i in range(count)]

    def check_requirements(
        self, requirements: GPURequirement
    ) -> Optional[list[int]]:
        """
        Check if there are GPUs meeting the requirements.

        Returns:
            List of available GPU IDs if requirements are met, None otherwise.
        """
        try:
            all_gpus = self.get_all_gpu_status()
        except NVMLError:
            return None

        candidates: list[int] = []

        for gpu in all_gpus:
            # If specific GPU IDs are requested, only consider those
            if requirements.gpu_ids and gpu.index not in requirements.gpu_ids:
                continue

            # Check memory requirement
            if gpu.free_memory_gb < requirements.min_free_memory_gb:
                logger.debug(
                    f"GPU {gpu.index}: insufficient memory "
                    f"({gpu.free_memory_gb:.1f}GB < {requirements.min_free_memory_gb}GB)"
                )
                continue

            # Check utilization requirement
            if gpu.utilization_percent > requirements.max_util_percent:
                logger.debug(
                    f"GPU {gpu.index}: utilization too high "
                    f"({gpu.utilization_percent}% > {requirements.max_util_percent}%)"
                )
                continue

            candidates.append(gpu.index)

        # Check if we have enough GPUs
        if len(candidates) >= requirements.gpu_count:
            selected = candidates[: requirements.gpu_count]
            logger.debug(f"Found suitable GPUs: {selected}")
            return selected

        logger.debug(
            f"Not enough GPUs: need {requirements.gpu_count}, found {len(candidates)}"
        )
        return None
