"""
System metrics collector.

This module collects system-level metrics including CPU, memory, disk,
and network I/O statistics.
"""

import psutil

from ...config import get_logger
from .base import MetricCollectorInterface


logger = get_logger("metrics.system")


class SystemMetricsCollector(MetricCollectorInterface):
    """
    Collects system-level metrics.

    Gathers metrics about CPU usage, memory consumption, disk I/O,
    and network I/O for both the overall system and the current process.
    """

    def __init__(self, collector):
        """
        Initialize system metrics collector.

        Args:
            collector: Core MetricCollector instance
        """
        super().__init__(collector)
        self.process = psutil.Process()

    def collect(self) -> None:
        """
        Collect current system metrics.

        Gathers CPU, memory, disk, and network metrics and records them
        using the collector.
        """
        try:
            # CPU metrics
            self.collector.gauge("system.cpu.percent", psutil.cpu_percent())
            self.collector.gauge("process.cpu.percent", self.process.cpu_percent())

            # Memory metrics
            memory = psutil.virtual_memory()
            self.collector.gauge("system.memory.percent", memory.percent)
            self.collector.gauge("system.memory.used_gb", memory.used / (1024**3))
            self.collector.gauge(
                "system.memory.available_gb", memory.available / (1024**3)
            )

            # Process memory
            process_memory = self.process.memory_info()
            self.collector.gauge(
                "process.memory.rss_mb", process_memory.rss / (1024**2)
            )
            self.collector.gauge(
                "process.memory.vms_mb", process_memory.vms / (1024**2)
            )

            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                self.collector.gauge(
                    "system.disk.read_mb", disk_io.read_bytes / (1024**2)
                )
                self.collector.gauge(
                    "system.disk.write_mb", disk_io.write_bytes / (1024**2)
                )

            # Network I/O
            net_io = psutil.net_io_counters()
            self.collector.gauge(
                "system.network.sent_mb", net_io.bytes_sent / (1024**2)
            )
            self.collector.gauge(
                "system.network.recv_mb", net_io.bytes_recv / (1024**2)
            )

            logger.debug("[METRICS-SYSTEM] System metrics collected successfully")

        except Exception as e:
            logger.error(f"[METRICS-SYSTEM] Failed to collect system metrics: {e}")
