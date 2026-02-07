"""
Passenger Comfort System for V2
Tracks passenger comfort and satisfaction during flight
"""

import logging
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Passengers")


class ComfortLevel(Enum):
    """Comfort level ratings"""
    EXCELLENT = "excellent"    # 90-100
    GOOD = "good"              # 70-89
    FAIR = "fair"              # 50-69
    POOR = "poor"              # 30-49
    TERRIBLE = "terrible"      # 0-29


# Comfort penalty factors
COMFORT_PENALTIES = {
    # G-forces
    'high_g_positive': -5,     # > 1.5G per second
    'high_g_negative': -10,    # < 0.5G per second
    'sustained_bank': -2,      # > 30 degrees for > 10s
    'rapid_roll': -3,          # Roll rate > 15 deg/s

    # Turbulence / VS
    'high_vs_positive': -3,    # > 1000 fpm climb per second
    'high_vs_negative': -3,    # > 1000 fpm descent per second
    'turbulence': -5,          # Rapid altitude changes

    # Speed
    'overspeed': -8,           # VNE approach
    'low_speed': -4,           # Near stall

    # Landing
    'hard_landing': -15,       # > 300 fpm
    'very_hard_landing': -25,  # > 500 fpm
    'go_around': -5,           # Missed approach

    # Cabin
    'rapid_descent': -4,       # > 1500 fpm descent
    'high_altitude': -2,       # > FL350 for extended time
    'pressurization': -10,     # Pressurization warning

    # Time
    'long_delay': -3,          # Extended ground time
    'long_flight': -1          # Per hour over 4 hours
}

# Comfort bonus factors
COMFORT_BONUSES = {
    'smooth_flight': 2,        # Low variance in flight parameters
    'soft_landing': 5,         # < 100 fpm
    'perfect_landing': 10,     # < 60 fpm
    'on_time_arrival': 3,
    'scenic_route': 2,
    'smooth_approach': 3
}


@dataclass
class PassengerComfort:
    """Tracks passenger comfort during a flight"""

    # Score tracking (starts at 100)
    current_score: float = 100.0
    min_score: float = 100.0
    max_score: float = 100.0

    # Event counts
    events: Dict[str, int] = field(default_factory=dict)
    bonuses: Dict[str, int] = field(default_factory=dict)

    # Flight data
    flight_start: Optional[str] = None
    flight_end: Optional[str] = None
    passenger_count: int = 0

    # Tracking state
    last_bank: float = 0.0
    last_vs: float = 0.0
    last_altitude: float = 0.0
    sustained_bank_time: float = 0.0

    def start_flight(self, passengers: int = 0) -> None:
        """Start tracking for a new flight"""
        self.current_score = 100.0
        self.min_score = 100.0
        self.max_score = 100.0
        self.events.clear()
        self.bonuses.clear()
        self.flight_start = datetime.now().isoformat()
        self.flight_end = None
        self.passenger_count = passengers
        self.sustained_bank_time = 0.0

        logger.info(f"Passenger comfort tracking started ({passengers} PAX)")

    def end_flight(self) -> Dict:
        """End flight and return summary"""
        self.flight_end = datetime.now().isoformat()

        summary = {
            'final_score': self.current_score,
            'rating': self.get_rating().value,
            'min_score': self.min_score,
            'events': self.events.copy(),
            'bonuses': self.bonuses.copy(),
            'passenger_count': self.passenger_count,
            'satisfaction_multiplier': self.get_satisfaction_multiplier()
        }

        logger.info(f"Passenger comfort: {self.current_score:.1f}% - {self.get_rating().value}")

        return summary

    def apply_penalty(self, penalty_type: str, multiplier: float = 1.0) -> float:
        """Apply a comfort penalty"""
        base_penalty = COMFORT_PENALTIES.get(penalty_type, 0)
        penalty = base_penalty * multiplier

        self.current_score = max(0, self.current_score + penalty)
        self.min_score = min(self.min_score, self.current_score)

        # Track event
        self.events[penalty_type] = self.events.get(penalty_type, 0) + 1

        logger.debug(f"Comfort penalty: {penalty_type} ({penalty:.1f}), score: {self.current_score:.1f}")

        return penalty

    def apply_bonus(self, bonus_type: str, multiplier: float = 1.0) -> float:
        """Apply a comfort bonus"""
        base_bonus = COMFORT_BONUSES.get(bonus_type, 0)
        bonus = base_bonus * multiplier

        self.current_score = min(100, self.current_score + bonus)
        self.max_score = max(self.max_score, self.current_score)

        # Track bonus
        self.bonuses[bonus_type] = self.bonuses.get(bonus_type, 0) + 1

        logger.debug(f"Comfort bonus: {bonus_type} (+{bonus:.1f}), score: {self.current_score:.1f}")

        return bonus

    def update(self, bank_degrees: float, vertical_speed: float,
               altitude: float, airspeed: float, delta_time: float = 1.0) -> None:
        """
        Update comfort based on current flight parameters

        Args:
            bank_degrees: Current bank angle
            vertical_speed: Current VS in fpm
            altitude: Current altitude
            airspeed: Current airspeed
            delta_time: Time since last update (seconds)
        """
        # Bank angle checks
        if abs(bank_degrees) > 35:
            self.apply_penalty('rapid_roll', delta_time * 0.1)
        elif abs(bank_degrees) > 30:
            self.sustained_bank_time += delta_time
            if self.sustained_bank_time > 10:
                self.apply_penalty('sustained_bank', delta_time * 0.1)
        else:
            self.sustained_bank_time = 0

        # Vertical speed checks
        vs_change = abs(vertical_speed - self.last_vs)
        if vs_change > 500:  # Rapid VS change
            self.apply_penalty('turbulence', vs_change / 500 * 0.5)

        if vertical_speed > 1500:
            self.apply_penalty('high_vs_positive', delta_time * 0.05)
        elif vertical_speed < -1500:
            self.apply_penalty('rapid_descent', delta_time * 0.05)
        elif vertical_speed < -1000:
            self.apply_penalty('high_vs_negative', delta_time * 0.03)

        # Altitude checks
        if altitude > 35000:
            self.apply_penalty('high_altitude', delta_time * 0.01)

        # Update tracking
        self.last_bank = bank_degrees
        self.last_vs = vertical_speed
        self.last_altitude = altitude

    def record_landing(self, vertical_speed_fpm: float) -> None:
        """Record landing quality"""
        vs = abs(vertical_speed_fpm)

        if vs > 500:
            self.apply_penalty('very_hard_landing')
        elif vs > 300:
            self.apply_penalty('hard_landing')
        elif vs < 60:
            self.apply_bonus('perfect_landing')
        elif vs < 100:
            self.apply_bonus('soft_landing')

    def record_go_around(self) -> None:
        """Record a go-around/missed approach"""
        self.apply_penalty('go_around')

    def get_rating(self) -> ComfortLevel:
        """Get current comfort rating"""
        score = self.current_score
        if score >= 90:
            return ComfortLevel.EXCELLENT
        elif score >= 70:
            return ComfortLevel.GOOD
        elif score >= 50:
            return ComfortLevel.FAIR
        elif score >= 30:
            return ComfortLevel.POOR
        else:
            return ComfortLevel.TERRIBLE

    def get_satisfaction_multiplier(self) -> float:
        """Get pay multiplier based on passenger satisfaction"""
        score = self.current_score
        if score >= 95:
            return 1.15  # +15% tip
        elif score >= 85:
            return 1.10
        elif score >= 70:
            return 1.0   # Base pay
        elif score >= 50:
            return 0.95  # Small deduction
        elif score >= 30:
            return 0.85  # Complaints
        else:
            return 0.70  # Serious complaints

    def get_feedback(self) -> List[str]:
        """Get passenger feedback messages"""
        feedback = []
        score = self.current_score

        if score >= 95:
            feedback.append("Les passagers sont ravis du vol!")
        elif score >= 85:
            feedback.append("Tres bon vol, passagers satisfaits.")
        elif score >= 70:
            feedback.append("Vol correct, quelques remarques mineures.")
        elif score >= 50:
            feedback.append("Plusieurs passagers ont eu des inquietudes.")
        elif score >= 30:
            feedback.append("De nombreuses plaintes ont ete enregistrees.")
        else:
            feedback.append("Les passagers sont tres mecontents!")

        # Specific feedback based on events
        if self.events.get('very_hard_landing', 0) > 0:
            feedback.append("L'atterrissage etait tres brutal.")
        if self.events.get('turbulence', 0) > 5:
            feedback.append("Le vol etait trop turbulent.")
        if self.events.get('rapid_descent', 0) > 0:
            feedback.append("La descente etait trop rapide.")

        if self.bonuses.get('perfect_landing', 0) > 0:
            feedback.append("Atterrissage tout en douceur!")

        return feedback


class PassengerManager:
    """Manages passenger comfort system"""

    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._current_comfort: Optional[PassengerComfort] = None
        self._history: List[Dict] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def current(self) -> Optional[PassengerComfort]:
        return self._current_comfort

    def start_flight(self, passengers: int = 0) -> PassengerComfort:
        """Start tracking a new flight"""
        self._current_comfort = PassengerComfort()
        self._current_comfort.start_flight(passengers)
        return self._current_comfort

    def end_flight(self) -> Optional[Dict]:
        """End current flight and return summary"""
        if self._current_comfort:
            summary = self._current_comfort.end_flight()
            self._history.append(summary)
            return summary
        return None

    def update(self, bank: float, vs: float, alt: float,
               speed: float, delta_time: float = 1.0) -> None:
        """Update comfort tracking"""
        if self._enabled and self._current_comfort:
            self._current_comfort.update(bank, vs, alt, speed, delta_time)

    def record_landing(self, vs_fpm: float) -> None:
        """Record landing"""
        if self._current_comfort:
            self._current_comfort.record_landing(vs_fpm)

    def get_stats(self) -> Dict:
        """Get passenger comfort statistics"""
        if not self._history:
            return {'flights': 0, 'average_score': 0}

        scores = [h['final_score'] for h in self._history]
        return {
            'flights': len(self._history),
            'average_score': sum(scores) / len(scores),
            'best_score': max(scores),
            'worst_score': min(scores)
        }


# Global passenger manager instance
_passenger_manager: Optional[PassengerManager] = None

def get_passenger_manager() -> PassengerManager:
    """Get or create global passenger manager"""
    global _passenger_manager
    if _passenger_manager is None:
        _passenger_manager = PassengerManager()
    return _passenger_manager
