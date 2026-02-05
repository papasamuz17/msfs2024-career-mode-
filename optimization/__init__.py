"""
V2 Optimization Module
Includes cache, performance monitoring, adaptive SimConnect polling, and airport spatial index
"""

from .cache import UnifiedCache, get_cache
from .performance import PerformanceMonitor, get_performance_mode, get_performance_monitor
from .simconnect_opt import AdaptiveSimConnect, get_adaptive_simconnect
from .airport_index import AirportSpatialIndex, get_airport_index

__all__ = [
    'UnifiedCache',
    'get_cache',
    'PerformanceMonitor',
    'get_performance_mode',
    'get_performance_monitor',
    'AdaptiveSimConnect',
    'get_adaptive_simconnect',
    'AirportSpatialIndex',
    'get_airport_index'
]
