"""
Performance Monitoring and Mode Management for V2
Monitors CPU/RAM usage and adjusts application behavior accordingly
"""

import logging
import time
from enum import Enum
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from threading import Thread, Event

logger = logging.getLogger("MissionGenerator.Performance")

# Try to import psutil for system monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - performance monitoring limited")


class PerformanceMode(Enum):
    """Application performance modes"""
    POWER_SAVER = "power_saver"    # Minimal resource usage
    BALANCED = "balanced"          # Default balanced mode
    PERFORMANCE = "performance"    # Maximum features, higher resource usage


@dataclass
class PerformanceSettings:
    """Settings for each performance mode"""
    simconnect_poll_ms: int       # SimConnect polling interval
    ui_update_ms: int             # UI refresh interval
    cache_cleanup_interval: int    # Cache cleanup frequency (seconds)
    enable_animations: bool        # UI animations
    voice_cache_enabled: bool      # TTS voice caching
    max_logbook_entries: int       # Max logbook entries to load
    weather_update_interval: int   # Weather refresh (seconds)


# Performance mode configurations
PERFORMANCE_CONFIGS: Dict[PerformanceMode, PerformanceSettings] = {
    PerformanceMode.POWER_SAVER: PerformanceSettings(
        simconnect_poll_ms=2000,
        ui_update_ms=500,
        cache_cleanup_interval=60,
        enable_animations=False,
        voice_cache_enabled=True,
        max_logbook_entries=50,
        weather_update_interval=300
    ),
    PerformanceMode.BALANCED: PerformanceSettings(
        simconnect_poll_ms=1000,
        ui_update_ms=100,
        cache_cleanup_interval=120,
        enable_animations=True,
        voice_cache_enabled=True,
        max_logbook_entries=200,
        weather_update_interval=180
    ),
    PerformanceMode.PERFORMANCE: PerformanceSettings(
        simconnect_poll_ms=500,
        ui_update_ms=50,
        cache_cleanup_interval=300,
        enable_animations=True,
        voice_cache_enabled=False,
        max_logbook_entries=500,
        weather_update_interval=60
    )
}


class PerformanceMonitor:
    """
    Monitors system performance and provides recommendations
    Can automatically adjust performance mode based on system load
    """

    def __init__(self, auto_adjust: bool = False):
        self._current_mode = PerformanceMode.BALANCED
        self._auto_adjust = auto_adjust
        self._monitoring = False
        self._stop_event = Event()
        self._monitor_thread: Optional[Thread] = None
        self._callbacks: list[Callable[[PerformanceMode], None]] = []

        # Performance history
        self._cpu_history: list[float] = []
        self._ram_history: list[float] = []
        self._history_max_size = 60  # Keep last 60 samples

        # Thresholds for auto-adjustment
        self._cpu_high_threshold = 80.0
        self._cpu_low_threshold = 30.0
        self._ram_high_threshold = 85.0

    @property
    def current_mode(self) -> PerformanceMode:
        return self._current_mode

    @property
    def settings(self) -> PerformanceSettings:
        return PERFORMANCE_CONFIGS[self._current_mode]

    def set_mode(self, mode) -> None:
        """Manually set performance mode"""
        # Convert string to enum if needed
        if isinstance(mode, str):
            mode_map = {
                'power_saver': PerformanceMode.POWER_SAVER,
                'balanced': PerformanceMode.BALANCED,
                'performance': PerformanceMode.PERFORMANCE
            }
            mode = mode_map.get(mode.lower(), PerformanceMode.BALANCED)

        if mode != self._current_mode:
            old_mode = self._current_mode
            self._current_mode = mode
            logger.info(f"Performance mode changed: {old_mode.value} -> {mode.value}")

            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(mode)
                except Exception as e:
                    logger.error(f"Performance callback error: {e}")

    def register_callback(self, callback: Callable[[PerformanceMode], None]) -> None:
        """Register callback for mode changes"""
        self._callbacks.append(callback)

    def get_system_stats(self) -> Dict:
        """Get current system statistics"""
        stats = {
            'cpu_percent': 0.0,
            'ram_percent': 0.0,
            'ram_used_mb': 0,
            'ram_total_mb': 0,
            'available': PSUTIL_AVAILABLE
        }

        if PSUTIL_AVAILABLE:
            try:
                stats['cpu_percent'] = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                stats['ram_percent'] = mem.percent
                stats['ram_used_mb'] = mem.used // (1024 * 1024)
                stats['ram_total_mb'] = mem.total // (1024 * 1024)
            except Exception as e:
                logger.error(f"Error getting system stats: {e}")

        return stats

    def get_process_stats(self) -> Dict:
        """Get stats for current process"""
        stats = {
            'cpu_percent': 0.0,
            'ram_mb': 0,
            'threads': 1,
            'available': PSUTIL_AVAILABLE
        }

        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                stats['cpu_percent'] = process.cpu_percent(interval=0.1)
                stats['ram_mb'] = process.memory_info().rss // (1024 * 1024)
                stats['threads'] = process.num_threads()
            except Exception as e:
                logger.error(f"Error getting process stats: {e}")

        return stats

    def start_monitoring(self, interval_seconds: float = 5.0) -> None:
        """Start background performance monitoring"""
        if self._monitoring:
            return

        self._monitoring = True
        self._stop_event.clear()

        def monitor_loop():
            while not self._stop_event.is_set():
                stats = self.get_system_stats()

                # Update history
                self._cpu_history.append(stats['cpu_percent'])
                self._ram_history.append(stats['ram_percent'])

                # Trim history
                if len(self._cpu_history) > self._history_max_size:
                    self._cpu_history.pop(0)
                if len(self._ram_history) > self._history_max_size:
                    self._ram_history.pop(0)

                # Auto-adjust if enabled
                if self._auto_adjust:
                    self._check_auto_adjust()

                self._stop_event.wait(interval_seconds)

        self._monitor_thread = Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Performance monitoring started")

    def stop_monitoring(self) -> None:
        """Stop background monitoring"""
        if not self._monitoring:
            return

        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)

        self._monitoring = False
        logger.info("Performance monitoring stopped")

    def _check_auto_adjust(self) -> None:
        """Check if performance mode should be auto-adjusted"""
        if len(self._cpu_history) < 10:
            return  # Not enough data

        # Calculate averages
        avg_cpu = sum(self._cpu_history[-10:]) / 10
        avg_ram = sum(self._ram_history[-10:]) / 10

        current = self._current_mode

        # Determine recommended mode
        if avg_cpu > self._cpu_high_threshold or avg_ram > self._ram_high_threshold:
            recommended = PerformanceMode.POWER_SAVER
        elif avg_cpu < self._cpu_low_threshold and avg_ram < 60:
            recommended = PerformanceMode.PERFORMANCE
        else:
            recommended = PerformanceMode.BALANCED

        if recommended != current:
            logger.info(f"Auto-adjusting performance: CPU={avg_cpu:.1f}%, RAM={avg_ram:.1f}%")
            self.set_mode(recommended)

    def get_recommendation(self) -> Dict:
        """Get performance recommendation based on current stats"""
        stats = self.get_system_stats()
        process_stats = self.get_process_stats()

        recommendation = {
            'current_mode': self._current_mode.value,
            'recommended_mode': self._current_mode.value,
            'reason': "System running normally",
            'system_stats': stats,
            'process_stats': process_stats
        }

        if stats['cpu_percent'] > self._cpu_high_threshold:
            recommendation['recommended_mode'] = PerformanceMode.POWER_SAVER.value
            recommendation['reason'] = f"High CPU usage: {stats['cpu_percent']:.1f}%"
        elif stats['ram_percent'] > self._ram_high_threshold:
            recommendation['recommended_mode'] = PerformanceMode.POWER_SAVER.value
            recommendation['reason'] = f"High RAM usage: {stats['ram_percent']:.1f}%"
        elif stats['cpu_percent'] < self._cpu_low_threshold and stats['ram_percent'] < 50:
            recommendation['recommended_mode'] = PerformanceMode.PERFORMANCE.value
            recommendation['reason'] = "System has available resources"

        return recommendation


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None

def get_performance_mode() -> PerformanceMode:
    """Get current performance mode"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor.current_mode

def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor
