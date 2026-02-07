"""
Automatic Callouts System for V2 Copilot
Realistic airline-style callouts: V1, Rotate, altitude callouts, warnings, etc.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Copilot.Callouts")


class CalloutType(Enum):
    """Types of callouts"""
    SPEED = "speed"          # V1, Vr, V2, etc.
    ALTITUDE = "altitude"    # Altitude callouts
    DECISION = "decision"    # Decision altitude
    MINIMUMS = "minimums"    # Approach minimums
    TOUCHDOWN = "touchdown"  # Landing callouts
    GEAR = "gear"            # Gear status
    FLAPS = "flaps"          # Flaps status
    WARNING = "warning"      # Warnings
    INFO = "info"            # Informational
    RATE = "rate"            # Descent/climb rate


@dataclass
class Callout:
    """A single callout configuration"""
    id: str
    callout_type: CalloutType
    text: str                    # Text to speak
    condition: str               # Condition type
    value: float                 # Trigger value
    phase_required: List[str] = field(default_factory=list)  # Required flight phases
    one_shot: bool = True        # Only trigger once
    priority: int = 1            # Higher = more important (3 = interrupt)
    cooldown_seconds: float = 0  # Minimum time between repeats
    audio_file: Optional[str] = None  # Optional prerecorded audio


@dataclass
class CalloutEvent:
    """Record of a triggered callout"""
    callout_id: str
    text: str
    timestamp: str
    altitude: float
    airspeed: float


# ============================================================================
# TAKEOFF CALLOUTS - Realistic airline sequence
# ============================================================================
TAKEOFF_CALLOUTS: List[Callout] = [
    # Speed callouts during takeoff roll
    Callout("60kt", CalloutType.SPEED, "60 noeuds", "airspeed_above", 60,
            phase_required=["takeoff_roll"], one_shot=True),
    Callout("80kt", CalloutType.SPEED, "80 noeuds, checks", "airspeed_above", 80,
            phase_required=["takeoff_roll"], one_shot=True),
    Callout("v1", CalloutType.SPEED, "V1", "airspeed_above", 110,
            phase_required=["takeoff_roll"], one_shot=True, priority=3),
    Callout("rotate", CalloutType.SPEED, "Rotate", "airspeed_above", 120,
            phase_required=["takeoff_roll", "rotation"], one_shot=True, priority=3),

    # After liftoff
    Callout("positive_rate", CalloutType.INFO, "Positive rate", "vs_above", 200,
            phase_required=["initial_climb"], one_shot=True, priority=2),
    Callout("gear_up_call", CalloutType.GEAR, "Gear up", "altitude_agl_above", 100,
            phase_required=["initial_climb"], one_shot=True, priority=2),
    Callout("400ft_takeoff", CalloutType.ALTITUDE, "400 pieds", "altitude_agl_above", 400,
            phase_required=["initial_climb"], one_shot=True),
    Callout("1000ft_takeoff", CalloutType.ALTITUDE, "1000 pieds, check flight instruments",
            "altitude_agl_above", 1000, phase_required=["initial_climb"], one_shot=True),
]

# ============================================================================
# CLIMB CALLOUTS
# ============================================================================
CLIMB_CALLOUTS: List[Callout] = [
    Callout("3000ft_climb", CalloutType.ALTITUDE, "Passing 3000 pieds",
            "altitude_msl_above", 3000, phase_required=["climb"], one_shot=True),
    Callout("fl100_climb", CalloutType.ALTITUDE, "Flight level 100, check speed restrictions",
            "altitude_msl_above", 10000, phase_required=["climb"], one_shot=True),
    Callout("fl180_climb", CalloutType.ALTITUDE, "Flight level 180, transition altitude",
            "altitude_msl_above", 18000, phase_required=["climb"], one_shot=True),
    # Top of climb detection
    Callout("leveling_off", CalloutType.INFO, "Leveling off", "vs_near_zero", 150,
            phase_required=["climb"], one_shot=True),
]

# ============================================================================
# CRUISE CALLOUTS
# ============================================================================
CRUISE_CALLOUTS: List[Callout] = [
    # These are triggered by distance/time, handled separately
]

# ============================================================================
# DESCENT CALLOUTS
# ============================================================================
DESCENT_CALLOUTS: List[Callout] = [
    Callout("descent_started", CalloutType.INFO, "Descente initiee", "vs_below", -300,
            phase_required=["descent"], one_shot=True),
    Callout("fl180_descent", CalloutType.ALTITUDE, "Flight level 180, transition level",
            "altitude_msl_below", 18500, phase_required=["descent"], one_shot=True),
    Callout("fl100_descent", CalloutType.ALTITUDE, "10000 pieds, vitesse limite",
            "altitude_msl_below", 10500, phase_required=["descent"], one_shot=True),
]

# ============================================================================
# APPROACH CALLOUTS - Standard airline calls
# ============================================================================
APPROACH_CALLOUTS: List[Callout] = [
    # Higher altitudes
    Callout("5000ft_approach", CalloutType.ALTITUDE, "5000 pieds",
            "altitude_agl_below", 5000, phase_required=["approach"], one_shot=True),
    Callout("3000ft_approach", CalloutType.ALTITUDE, "3000 pieds",
            "altitude_agl_below", 3000, phase_required=["approach"], one_shot=True),
    Callout("2500ft_approach", CalloutType.ALTITUDE, "2500 pieds, gear down",
            "altitude_agl_below", 2500, phase_required=["approach"], one_shot=True, priority=2),
    Callout("1500ft_approach", CalloutType.ALTITUDE, "1500 pieds, stabilized check",
            "altitude_agl_below", 1500, phase_required=["approach"], one_shot=True),

    # Critical altitudes
    Callout("1000ft_approach", CalloutType.ALTITUDE, "1000 pieds",
            "altitude_agl_below", 1000, phase_required=["approach", "short_final"],
            one_shot=True, priority=2),
    Callout("500ft_approach", CalloutType.ALTITUDE, "500",
            "altitude_agl_below", 500, phase_required=["approach", "short_final"],
            one_shot=True, priority=2),

    # Final approach
    Callout("400ft", CalloutType.ALTITUDE, "400",
            "altitude_agl_below", 400, phase_required=["short_final"], one_shot=True),
    Callout("300ft", CalloutType.ALTITUDE, "300",
            "altitude_agl_below", 300, phase_required=["short_final"], one_shot=True),
    Callout("approaching_minimums", CalloutType.MINIMUMS, "Approaching minimums",
            "altitude_agl_below", 250, phase_required=["short_final"], one_shot=True, priority=3),
    Callout("200ft", CalloutType.ALTITUDE, "200",
            "altitude_agl_below", 200, phase_required=["short_final"], one_shot=True, priority=2),
    Callout("minimums", CalloutType.MINIMUMS, "Minimums",
            "altitude_agl_below", 200, phase_required=["short_final"], one_shot=True, priority=3),

    # Flare altitudes
    Callout("100ft", CalloutType.ALTITUDE, "100",
            "altitude_agl_below", 100, phase_required=["short_final", "flare"],
            one_shot=True, priority=3),
    Callout("50ft", CalloutType.ALTITUDE, "50",
            "altitude_agl_below", 50, phase_required=["flare"], one_shot=True, priority=3),
    Callout("40ft", CalloutType.ALTITUDE, "40",
            "altitude_agl_below", 40, phase_required=["flare"], one_shot=True, priority=2),
    Callout("30ft", CalloutType.ALTITUDE, "30",
            "altitude_agl_below", 30, phase_required=["flare"], one_shot=True, priority=2),
    Callout("20ft", CalloutType.ALTITUDE, "20",
            "altitude_agl_below", 20, phase_required=["flare"], one_shot=True, priority=2),
    Callout("10ft", CalloutType.ALTITUDE, "10",
            "altitude_agl_below", 10, phase_required=["flare"], one_shot=True, priority=2),
    Callout("retard", CalloutType.SPEED, "Retard",
            "altitude_agl_below", 25, phase_required=["flare"], one_shot=True, priority=2),
]

# ============================================================================
# LANDING CALLOUTS
# ============================================================================
LANDING_CALLOUTS: List[Callout] = [
    Callout("touchdown", CalloutType.TOUCHDOWN, "", "on_ground", 1,
            phase_required=["flare", "landing_roll"], one_shot=True, priority=3),
    # Touchdown rating is handled separately in code
]

# ============================================================================
# WARNING CALLOUTS - Safety critical
# ============================================================================
WARNING_CALLOUTS: List[Callout] = [
    # These are checked separately with different logic
]


# Aircraft V-speed profiles by category
V_SPEED_PROFILES = {
    'light_piston': {'v1': 55, 'vr': 60, 'v2': 70, 'vref': 65, 'vne': 180},
    'light_turboprop': {'v1': 90, 'vr': 100, 'v2': 110, 'vref': 100, 'vne': 250},
    'medium_turboprop': {'v1': 105, 'vr': 115, 'v2': 125, 'vref': 115, 'vne': 280},
    'light_jet': {'v1': 115, 'vr': 125, 'v2': 140, 'vref': 125, 'vne': 350},
    'medium_jet': {'v1': 130, 'vr': 145, 'v2': 155, 'vref': 140, 'vne': 400},
    'heavy_jet': {'v1': 145, 'vr': 160, 'v2': 175, 'vref': 150, 'vne': 450},
    'airliner': {'v1': 140, 'vr': 155, 'v2': 165, 'vref': 145, 'vne': 400},
    'helicopter': {'v1': 0, 'vr': 0, 'v2': 0, 'vref': 60, 'vne': 150},
}


class CalloutManager:
    """Manages automatic callouts during flight"""

    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._callouts: List[Callout] = []
        self._triggered: Set[str] = set()
        self._history: List[CalloutEvent] = []
        self._callbacks: List[Callable[[Callout], None]] = []
        self._last_callout_time: Dict[str, datetime] = {}

        # Speed references (can be set per aircraft)
        self._v1 = 110
        self._vr = 120
        self._v2 = 130
        self._vref = 120
        self._vne = 250

        # State tracking for warnings
        self._last_vs = 0
        self._last_airspeed = 0
        self._gear_warning_given = False
        self._flaps_warning_given = False

        self._initialize_callouts()

    def _initialize_callouts(self) -> None:
        """Initialize all callouts"""
        self._callouts.clear()
        self._callouts.extend(TAKEOFF_CALLOUTS)
        self._callouts.extend(CLIMB_CALLOUTS)
        self._callouts.extend(DESCENT_CALLOUTS)
        self._callouts.extend(APPROACH_CALLOUTS)
        self._callouts.extend(LANDING_CALLOUTS)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def set_aircraft_category(self, category: str) -> None:
        """Set V-speeds based on aircraft category"""
        profile = V_SPEED_PROFILES.get(category, V_SPEED_PROFILES['light_piston'])
        self.set_v_speeds(
            v1=profile['v1'],
            vr=profile['vr'],
            v2=profile['v2'],
            vref=profile['vref']
        )
        self._vne = profile['vne']
        logger.info(f"V-speeds set for {category}: V1={profile['v1']}, Vr={profile['vr']}")

    def set_v_speeds(self, v1: float, vr: float, v2: float, vref: float = 130) -> None:
        """Set V-speeds for the current aircraft"""
        self._v1 = v1
        self._vr = vr
        self._v2 = v2
        self._vref = vref

        # Update callout values
        for callout in self._callouts:
            if callout.id == "v1":
                callout.value = v1
            elif callout.id == "rotate":
                callout.value = vr
            elif callout.id == "v2" if hasattr(callout, 'id') and callout.id == "v2" else False:
                callout.value = v2

        logger.info(f"V-speeds set: V1={v1}, Vr={vr}, V2={v2}, Vref={vref}")

    def register_callback(self, callback: Callable[[Callout], None]) -> None:
        """Register callback for callouts"""
        self._callbacks.append(callback)

    def reset(self) -> None:
        """Reset triggered callouts for new flight"""
        self._triggered.clear()
        self._history.clear()
        self._last_callout_time.clear()
        self._gear_warning_given = False
        self._flaps_warning_given = False
        logger.info("Callouts reset")

    def check_callouts(self, flight_phase: str, altitude_agl: float, altitude_msl: float,
                       airspeed: float, vertical_speed: float, on_ground: bool,
                       gear_down: bool = True, flaps_position: float = 0) -> List[Callout]:
        """
        Check for callouts that should be triggered

        Returns:
            List of callouts that were triggered
        """
        if not self._enabled:
            return []

        # Skip all callouts when in menu/unknown phase
        phase_lower = flight_phase.lower()
        if phase_lower == 'unknown':
            return []

        triggered = []

        for callout in self._callouts:
            # Skip if already triggered (one-shot)
            if callout.one_shot and callout.id in self._triggered:
                continue

            # Check cooldown
            if callout.id in self._last_callout_time:
                elapsed = (datetime.now() - self._last_callout_time[callout.id]).total_seconds()
                if elapsed < callout.cooldown_seconds:
                    continue

            # Check phase requirement
            if callout.phase_required and phase_lower not in callout.phase_required:
                continue

            # Check condition
            condition_met = self._check_condition(
                callout.condition, callout.value,
                altitude_agl, altitude_msl, airspeed, vertical_speed, on_ground
            )

            if condition_met:
                self._triggered.add(callout.id)
                self._last_callout_time[callout.id] = datetime.now()
                triggered.append(callout)

                # Record event
                event = CalloutEvent(
                    callout_id=callout.id,
                    text=callout.text,
                    timestamp=datetime.now().isoformat(),
                    altitude=altitude_agl,
                    airspeed=airspeed
                )
                self._history.append(event)
                logger.debug(f"Callout triggered: {callout.text}")

        # Check warnings separately
        warning_callouts = self._check_warnings(
            phase_lower, altitude_agl, airspeed, vertical_speed,
            gear_down, on_ground
        )
        triggered.extend(warning_callouts)

        # Sort by priority
        triggered.sort(key=lambda c: c.priority, reverse=True)

        # Notify callbacks
        for callout in triggered:
            for callback in self._callbacks:
                try:
                    callback(callout)
                except Exception as e:
                    logger.error(f"Callout callback error: {e}")

        # Update state
        self._last_vs = vertical_speed
        self._last_airspeed = airspeed

        return triggered

    def _check_condition(self, condition: str, value: float,
                         altitude_agl: float, altitude_msl: float,
                         airspeed: float, vertical_speed: float,
                         on_ground: bool) -> bool:
        """Check if a callout condition is met"""
        if condition == "airspeed_above":
            return airspeed >= value
        elif condition == "airspeed_below":
            return airspeed <= value
        elif condition == "altitude_agl_above":
            return altitude_agl >= value
        elif condition == "altitude_agl_below":
            return altitude_agl <= value
        elif condition == "altitude_msl_above":
            return altitude_msl >= value
        elif condition == "altitude_msl_below":
            return altitude_msl <= value
        elif condition == "vs_above":
            return vertical_speed >= value
        elif condition == "vs_below":
            return vertical_speed <= value
        elif condition == "vs_near_zero":
            return abs(vertical_speed) <= value
        elif condition == "on_ground":
            return on_ground
        return False

    def _check_warnings(self, phase: str, altitude_agl: float, airspeed: float,
                        vertical_speed: float, gear_down: bool, on_ground: bool) -> List[Callout]:
        """Check for warning callouts"""
        warnings = []

        # Gear warning - approaching landing without gear
        if phase in ['approach', 'short_final'] and altitude_agl < 1000:
            if not gear_down and not self._gear_warning_given and not on_ground:
                warning = Callout(
                    "gear_warning", CalloutType.WARNING,
                    "Gear! Gear! Gear!", "custom", 0,
                    priority=3
                )
                warnings.append(warning)
                self._gear_warning_given = True
                logger.warning("GEAR WARNING triggered!")

        # Reset gear warning if we climb back up
        if altitude_agl > 1500:
            self._gear_warning_given = False

        # Sink rate warning
        if not on_ground and vertical_speed < -2000 and altitude_agl < 2500:
            if "sink_rate_warning" not in self._triggered:
                warning = Callout(
                    "sink_rate_warning", CalloutType.WARNING,
                    "Sink rate!", "custom", 0,
                    priority=3
                )
                warnings.append(warning)
                self._triggered.add("sink_rate_warning")
                logger.warning("SINK RATE WARNING triggered!")

        # Reset sink rate warning if VS improves
        if vertical_speed > -1000:
            self._triggered.discard("sink_rate_warning")

        # Overspeed warning
        if airspeed > self._vne * 0.95 and "overspeed_warning" not in self._triggered:
            warning = Callout(
                "overspeed_warning", CalloutType.WARNING,
                "Speed!", "custom", 0,
                priority=3
            )
            warnings.append(warning)
            self._triggered.add("overspeed_warning")
            logger.warning("OVERSPEED WARNING triggered!")

        # Reset overspeed warning
        if airspeed < self._vne * 0.9:
            self._triggered.discard("overspeed_warning")

        # Bank angle warning (would need bank angle input)
        # Stall warning (would need stall speed input)

        return warnings

    def get_landing_rating(self, vertical_speed_fpm: float) -> tuple:
        """
        Get landing rating and callout based on touchdown VS

        Returns:
            Tuple of (rating_text, score)
        """
        vs = abs(vertical_speed_fpm)

        if vs < 60:
            return ("Butter! Perfect landing", 100)
        elif vs < 100:
            return ("Excellent landing", 90)
        elif vs < 150:
            return ("Tres bon atterrissage", 80)
        elif vs < 200:
            return ("Bon atterrissage", 70)
        elif vs < 250:
            return ("Atterrissage normal", 60)
        elif vs < 350:
            return ("Atterrissage ferme", 40)
        elif vs < 500:
            return ("Atterrissage dur", 20)
        else:
            return ("Atterrissage tres dur!", 0)

    def get_history(self) -> List[CalloutEvent]:
        """Get callout history"""
        return self._history.copy()

    def get_stats(self) -> Dict:
        """Get callout statistics"""
        return {
            'total_callouts': len(self._history),
            'triggered_types': list(set(e.callout_id for e in self._history)),
            'enabled': self._enabled,
            'v_speeds': {'v1': self._v1, 'vr': self._vr, 'v2': self._v2, 'vref': self._vref}
        }


# Global callout manager instance
_callout_manager: Optional[CalloutManager] = None

def get_callout_manager() -> CalloutManager:
    """Get or create global callout manager"""
    global _callout_manager
    if _callout_manager is None:
        _callout_manager = CalloutManager()
    return _callout_manager
