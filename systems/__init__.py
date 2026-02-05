"""
V2 Systems Module
Game systems: fuel, maintenance, failures, passengers, challenges, checkride, weather, pattern training
"""

from .fuel import FuelManager, get_fuel_manager
from .maintenance import MaintenanceManager, AircraftStatus, get_maintenance
from .failures import FailureManager, Failure, get_failure_manager
from .passengers import PassengerManager, PassengerComfort, get_passenger_manager
from .challenges import ChallengeManager, Challenge, get_challenge_manager
from .checkride import CheckrideManager, Checkride, get_checkride_manager
from .weather_sim import WeatherSimConnect, get_weather_system
from .pattern_training import PatternTrainer, PatternLeg, PatternSession, get_pattern_trainer

__all__ = [
    'FuelManager',
    'get_fuel_manager',
    'MaintenanceManager',
    'AircraftStatus',
    'get_maintenance',
    'FailureManager',
    'Failure',
    'get_failure_manager',
    'PassengerManager',
    'PassengerComfort',
    'get_passenger_manager',
    'ChallengeManager',
    'Challenge',
    'get_challenge_manager',
    'CheckrideManager',
    'Checkride',
    'get_checkride_manager',
    'WeatherSimConnect',
    'get_weather_system',
    'PatternTrainer',
    'PatternLeg',
    'PatternSession',
    'get_pattern_trainer'
]
