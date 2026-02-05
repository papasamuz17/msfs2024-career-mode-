"""
Random Failures System for V2
Simulates aircraft system failures during flight
"""

import logging
import random
from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Failures")


class FailureType(Enum):
    """Types of failures"""
    ENGINE = "engine"
    ELECTRICAL = "electrical"
    PITOT = "pitot"
    FUEL = "fuel"
    HYDRAULIC = "hydraulic"
    GEAR = "gear"
    FLAPS = "flaps"
    RADIO = "radio"
    NAV = "navigation"
    AUTOPILOT = "autopilot"


class FailureSeverity(Enum):
    """Failure severity levels"""
    MINOR = "minor"           # Annoyance, no action required
    MODERATE = "moderate"      # Requires attention
    SERIOUS = "serious"        # Requires immediate action
    CRITICAL = "critical"      # Emergency


@dataclass
class Failure:
    """A specific failure event"""
    id: str
    failure_type: FailureType
    severity: FailureSeverity
    name: str
    description: str
    effects: List[str]
    recovery_actions: List[str]
    probability: float = 0.01  # Base probability per hour
    duration_minutes: float = -1  # -1 = until recovered, >0 = auto-resolves
    triggered: bool = False
    triggered_at: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[str] = None

    def trigger(self) -> None:
        """Trigger the failure"""
        self.triggered = True
        self.triggered_at = datetime.now().isoformat()
        logger.warning(f"FAILURE: {self.name} - {self.description}")

    def resolve(self) -> None:
        """Resolve the failure"""
        self.resolved = True
        self.resolved_at = datetime.now().isoformat()
        logger.info(f"RESOLVED: {self.name}")


# Predefined failures
AVAILABLE_FAILURES: List[Failure] = [
    # Engine failures
    Failure(
        id="eng_roughness",
        failure_type=FailureType.ENGINE,
        severity=FailureSeverity.MODERATE,
        name="Engine Roughness",
        description="Engine running rough, possible carburetor icing",
        effects=["Reduced power", "Vibrations"],
        recovery_actions=["Apply carburetor heat", "Adjust mixture"],
        probability=0.02
    ),
    Failure(
        id="eng_partial_power_loss",
        failure_type=FailureType.ENGINE,
        severity=FailureSeverity.SERIOUS,
        name="Partial Power Loss",
        description="Engine not developing full power",
        effects=["Reduced climb rate", "Reduced cruise speed"],
        recovery_actions=["Check fuel selector", "Check mixture", "Divert if necessary"],
        probability=0.005
    ),
    Failure(
        id="eng_failure",
        failure_type=FailureType.ENGINE,
        severity=FailureSeverity.CRITICAL,
        name="Engine Failure",
        description="Complete engine failure",
        effects=["No thrust", "Glide only"],
        recovery_actions=["Attempt restart", "Find landing spot", "Declare emergency"],
        probability=0.001
    ),

    # Electrical failures
    Failure(
        id="elec_alternator",
        failure_type=FailureType.ELECTRICAL,
        severity=FailureSeverity.MODERATE,
        name="Alternator Failure",
        description="Alternator not charging",
        effects=["Battery discharge", "Limited time on battery"],
        recovery_actions=["Reduce electrical load", "Land within battery endurance"],
        probability=0.01
    ),
    Failure(
        id="elec_partial",
        failure_type=FailureType.ELECTRICAL,
        severity=FailureSeverity.SERIOUS,
        name="Partial Electrical Failure",
        description="Partial bus failure",
        effects=["Some instruments inoperative", "Radio may be affected"],
        recovery_actions=["Check circuit breakers", "Use backup instruments"],
        probability=0.005
    ),

    # Pitot/Static failures
    Failure(
        id="pitot_blockage",
        failure_type=FailureType.PITOT,
        severity=FailureSeverity.SERIOUS,
        name="Pitot Tube Blockage",
        description="Airspeed indicator unreliable",
        effects=["Erratic airspeed", "Possible icing"],
        recovery_actions=["Use pitot heat", "Use alternate static", "Maintain power/attitude"],
        probability=0.015
    ),

    # Fuel system failures
    Failure(
        id="fuel_leak",
        failure_type=FailureType.FUEL,
        severity=FailureSeverity.SERIOUS,
        name="Fuel Leak Indication",
        description="Fuel quantity decreasing faster than expected",
        effects=["Reduced range", "Possible fire hazard"],
        recovery_actions=["Land as soon as practical", "Monitor fuel quantity"],
        probability=0.003
    ),
    Failure(
        id="fuel_contamination",
        failure_type=FailureType.FUEL,
        severity=FailureSeverity.MODERATE,
        name="Fuel Contamination",
        description="Water or debris in fuel",
        effects=["Engine roughness", "Possible engine stoppage"],
        recovery_actions=["Switch tanks", "Land and drain sumps"],
        probability=0.005
    ),

    # Landing gear failures
    Failure(
        id="gear_unsafe",
        failure_type=FailureType.GEAR,
        severity=FailureSeverity.SERIOUS,
        name="Gear Unsafe Indication",
        description="Gear position uncertain",
        effects=["Cannot confirm gear down", "Possible gear-up landing"],
        recovery_actions=["Cycle gear", "Use manual extension", "Tower flyby"],
        probability=0.004
    ),

    # Radio/Nav failures
    Failure(
        id="radio_comm_fail",
        failure_type=FailureType.RADIO,
        severity=FailureSeverity.MODERATE,
        name="Communications Radio Failure",
        description="Cannot transmit or receive",
        effects=["No ATC communication", "Squawk 7600"],
        recovery_actions=["Squawk 7600", "Follow lost comm procedures"],
        probability=0.008
    ),
    Failure(
        id="nav_gps_degraded",
        failure_type=FailureType.NAV,
        severity=FailureSeverity.MINOR,
        name="GPS Signal Degraded",
        description="GPS accuracy reduced",
        effects=["Navigation may be imprecise"],
        recovery_actions=["Use VOR/NDB backup", "Continue VFR if possible"],
        probability=0.02,
        duration_minutes=10  # Auto-resolves
    ),

    # Autopilot failures
    Failure(
        id="ap_disconnect",
        failure_type=FailureType.AUTOPILOT,
        severity=FailureSeverity.MINOR,
        name="Autopilot Disconnect",
        description="Autopilot disconnected unexpectedly",
        effects=["Manual flight required"],
        recovery_actions=["Hand-fly the aircraft", "Reset autopilot if safe"],
        probability=0.025
    )
]


class FailureManager:
    """Manages random failure events"""

    def __init__(self, enabled: bool = False):
        self._enabled = enabled
        self._active_failures: List[Failure] = []
        self._failure_history: List[Failure] = []
        self._callbacks: List[Callable[[Failure], None]] = []

        # Probability modifiers
        self._base_multiplier = 1.0
        self._weather_modifier = 1.0
        self._maintenance_modifier = 1.0

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        if not value:
            self.clear_failures()

    @property
    def active_failures(self) -> List[Failure]:
        return [f for f in self._active_failures if not f.resolved]

    def register_callback(self, callback: Callable[[Failure], None]) -> None:
        """Register callback for failure events"""
        self._callbacks.append(callback)

    def set_modifiers(self, base: float = 1.0, weather: float = 1.0,
                      maintenance: float = 1.0) -> None:
        """Set probability modifiers"""
        self._base_multiplier = base
        self._weather_modifier = weather
        self._maintenance_modifier = maintenance

    def check_for_failures(self, elapsed_hours: float = 0.0167,
                           flight_phase: str = "cruise") -> List[Failure]:
        """
        Check for random failures based on elapsed time

        Args:
            elapsed_hours: Time elapsed (default ~1 minute)
            flight_phase: Current flight phase

        Returns:
            List of newly triggered failures
        """
        if not self._enabled:
            return []

        new_failures = []

        # Phase multipliers
        phase_mult = {
            'parked': 0.1,
            'taxi': 0.2,
            'takeoff': 1.5,
            'climb': 1.2,
            'cruise': 1.0,
            'descent': 1.1,
            'approach': 1.3,
            'landing': 1.5
        }.get(flight_phase, 1.0)

        total_mult = (self._base_multiplier * self._weather_modifier *
                      self._maintenance_modifier * phase_mult)

        for failure_template in AVAILABLE_FAILURES:
            # Skip if already active
            if any(f.id == failure_template.id for f in self._active_failures):
                continue

            # Calculate probability
            prob = failure_template.probability * total_mult * elapsed_hours

            if random.random() < prob:
                # Create new failure instance
                failure = Failure(
                    id=failure_template.id,
                    failure_type=failure_template.failure_type,
                    severity=failure_template.severity,
                    name=failure_template.name,
                    description=failure_template.description,
                    effects=failure_template.effects.copy(),
                    recovery_actions=failure_template.recovery_actions.copy(),
                    probability=failure_template.probability,
                    duration_minutes=failure_template.duration_minutes
                )
                failure.trigger()

                self._active_failures.append(failure)
                self._failure_history.append(failure)
                new_failures.append(failure)

                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        callback(failure)
                    except Exception as e:
                        logger.error(f"Failure callback error: {e}")

        return new_failures

    def resolve_failure(self, failure_id: str) -> bool:
        """Resolve a specific failure"""
        for failure in self._active_failures:
            if failure.id == failure_id and not failure.resolved:
                failure.resolve()
                return True
        return False

    def clear_failures(self) -> None:
        """Clear all active failures"""
        for failure in self._active_failures:
            failure.resolve()
        self._active_failures.clear()

    def get_failure_summary(self) -> Dict:
        """Get summary of current failures"""
        active = self.active_failures

        return {
            'count': len(active),
            'critical': sum(1 for f in active if f.severity == FailureSeverity.CRITICAL),
            'serious': sum(1 for f in active if f.severity == FailureSeverity.SERIOUS),
            'moderate': sum(1 for f in active if f.severity == FailureSeverity.MODERATE),
            'minor': sum(1 for f in active if f.severity == FailureSeverity.MINOR),
            'failures': [f.name for f in active]
        }

    def get_stats(self) -> Dict:
        """Get failure statistics"""
        return {
            'enabled': self._enabled,
            'total_failures': len(self._failure_history),
            'active_failures': len(self.active_failures),
            'multiplier': self._base_multiplier * self._weather_modifier * self._maintenance_modifier
        }


# Global failure manager instance
_failure_manager: Optional[FailureManager] = None

def get_failure_manager() -> FailureManager:
    """Get or create global failure manager"""
    global _failure_manager
    if _failure_manager is None:
        _failure_manager = FailureManager()
    return _failure_manager
