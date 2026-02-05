"""
Pilot Error Detection for V2 Copilot
Detects potential pilot errors and provides warnings
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Copilot.Errors")


class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "info"           # Informational
    CAUTION = "caution"     # Attention needed
    WARNING = "warning"     # Action required
    CRITICAL = "critical"   # Immediate action required


class ErrorType(Enum):
    """Types of pilot errors"""
    OVERSPEED = "overspeed"
    STALL_WARNING = "stall_warning"
    BANK_ANGLE = "bank_angle"
    PITCH_ATTITUDE = "pitch_attitude"
    GEAR_NOT_DOWN = "gear_not_down"
    FLAPS_NOT_SET = "flaps_not_set"
    UNSTABLE_APPROACH = "unstable_approach"
    ALTITUDE_DEVIATION = "altitude_deviation"
    HEADING_DEVIATION = "heading_deviation"
    SINK_RATE = "sink_rate"
    TERRAIN = "terrain"
    CONFIGURATION = "configuration"


@dataclass
class PilotError:
    """A detected pilot error"""
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    voice_message: str
    details: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False


@dataclass
class ErrorThresholds:
    """Thresholds for error detection"""
    # Speed limits
    max_speed_vne: float = 350.0      # Never exceed
    max_speed_vno: float = 200.0      # Normal operating
    stall_warning_speed: float = 70.0

    # Attitude limits
    max_bank_angle: float = 45.0
    excessive_bank_angle: float = 60.0
    max_pitch_up: float = 25.0
    max_pitch_down: float = -15.0

    # Approach limits
    max_approach_speed: float = 160.0
    gear_altitude_agl: float = 1500.0
    flaps_altitude_agl: float = 2000.0
    stable_approach_alt: float = 500.0

    # Sink rate
    max_sink_rate: float = -1500.0
    excessive_sink_rate: float = -2000.0

    # Deviations
    max_altitude_deviation: float = 300.0
    max_heading_deviation: float = 20.0


class ErrorDetector:
    """Detects pilot errors based on flight parameters"""

    def __init__(self, thresholds: ErrorThresholds = None, enabled: bool = True):
        self._thresholds = thresholds or ErrorThresholds()
        self._enabled = enabled
        self._active_errors: List[PilotError] = []
        self._error_history: List[PilotError] = []
        self._callbacks: List[Callable[[PilotError], None]] = []

        # State tracking
        self._last_check_time = 0.0
        self._approach_stable = True
        self._assigned_altitude: Optional[float] = None
        self._assigned_heading: Optional[float] = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        if not value:
            self._active_errors.clear()

    @property
    def active_errors(self) -> List[PilotError]:
        return [e for e in self._active_errors if not e.acknowledged]

    def set_assigned_altitude(self, altitude: float) -> None:
        """Set assigned altitude for deviation checking"""
        self._assigned_altitude = altitude

    def set_assigned_heading(self, heading: float) -> None:
        """Set assigned heading for deviation checking"""
        self._assigned_heading = heading

    def register_callback(self, callback: Callable[[PilotError], None]) -> None:
        """Register callback for errors"""
        self._callbacks.append(callback)

    def _add_error(self, error: PilotError) -> None:
        """Add a new error"""
        # Check if similar error already active
        for existing in self._active_errors:
            if existing.error_type == error.error_type and not existing.acknowledged:
                return  # Already have this error

        self._active_errors.append(error)
        self._error_history.append(error)

        logger.warning(f"Error detected: {error.message}")

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")

    def _clear_error(self, error_type: ErrorType) -> None:
        """Clear an error of specific type"""
        self._active_errors = [
            e for e in self._active_errors
            if e.error_type != error_type
        ]

    def check_errors(self, flight_phase: str, altitude_agl: float, altitude_msl: float,
                     airspeed: float, vertical_speed: float, bank_angle: float,
                     pitch_angle: float, gear_down: bool, flaps_position: float,
                     on_ground: bool,
                     # NEW V2 Enhanced parameters (optional for backward compatibility)
                     stall_warning_active: bool = None,
                     overspeed_warning_active: bool = None,
                     g_force: float = None,
                     structural_ice_pct: float = None,
                     pitot_ice_pct: float = None) -> List[PilotError]:
        """
        Check for pilot errors

        Args:
            flight_phase: Current flight phase
            altitude_agl: Altitude above ground (ft)
            altitude_msl: Altitude MSL (ft)
            airspeed: Indicated airspeed (kts)
            vertical_speed: Vertical speed (fpm)
            bank_angle: Bank angle (degrees)
            pitch_angle: Pitch angle (degrees)
            gear_down: True if gear down
            flaps_position: Flaps position (0-1)
            on_ground: True if on ground
            stall_warning_active: SimConnect STALL_WARNING (more reliable than threshold)
            overspeed_warning_active: SimConnect OVERSPEED_WARNING (more reliable)
            g_force: Current G-force (for excessive G warning)
            structural_ice_pct: Structural icing percentage (0-1)
            pitot_ice_pct: Pitot icing percentage (airspeed unreliable if > 0.1)

        Returns:
            List of new errors detected
        """
        if not self._enabled or on_ground:
            return []

        # Skip error checking when in menu/unknown phase
        if flight_phase.lower() == 'unknown':
            return []

        new_errors = []
        t = self._thresholds

        # ==================== ICING WARNING (NEW V2) ====================
        # Check pitot icing first - if airspeed data is unreliable, warn pilot
        if pitot_ice_pct is not None and pitot_ice_pct > 0.1:
            error = PilotError(
                error_type=ErrorType.CONFIGURATION,
                severity=ErrorSeverity.WARNING,
                message=f"PITOT ICE! Airspeed unreliable ({pitot_ice_pct*100:.0f}%)",
                voice_message="Pitot ice! Airspeed unreliable!",
                details={'pitot_ice_pct': pitot_ice_pct}
            )
            self._add_error(error)
            new_errors.append(error)

        # Structural icing warning
        if structural_ice_pct is not None and structural_ice_pct > 0.02:
            severity = ErrorSeverity.CRITICAL if structural_ice_pct > 0.05 else ErrorSeverity.WARNING
            error = PilotError(
                error_type=ErrorType.TERRAIN,  # Using TERRAIN type for icing hazard
                severity=severity,
                message=f"STRUCTURAL ICING! {structural_ice_pct*100:.1f}%",
                voice_message="Icing! Icing!" if severity == ErrorSeverity.CRITICAL else "Ice accumulation",
                details={'structural_ice_pct': structural_ice_pct}
            )
            self._add_error(error)
            new_errors.append(error)

        # ==================== SPEED ERRORS ====================

        # V2 ENHANCED: Use SimConnect OVERSPEED_WARNING if available (more reliable)
        # If SimConnect says NOT overspeed (False), trust it - don't use fallback thresholds
        if overspeed_warning_active is True:
            # SimConnect system warning is active - definitely overspeed
            error = PilotError(
                error_type=ErrorType.OVERSPEED,
                severity=ErrorSeverity.CRITICAL,
                message=f"OVERSPEED! {airspeed:.0f} kts (system warning)",
                voice_message="Overspeed! Overspeed!",
                details={'airspeed': airspeed, 'source': 'simconnect_warning'}
            )
            self._add_error(error)
            new_errors.append(error)
        elif overspeed_warning_active is False:
            # SimConnect says NOT overspeed - trust it, clear any error
            self._clear_error(ErrorType.OVERSPEED)
        # Fallback to threshold-based detection ONLY if SimConnect unavailable
        elif overspeed_warning_active is None:
            if airspeed > t.max_speed_vne:
                error = PilotError(
                    error_type=ErrorType.OVERSPEED,
                    severity=ErrorSeverity.CRITICAL,
                    message=f"OVERSPEED! {airspeed:.0f} kts > VNE {t.max_speed_vne:.0f}",
                    voice_message="Overspeed! Overspeed!",
                    details={'airspeed': airspeed, 'limit': t.max_speed_vne}
                )
                self._add_error(error)
                new_errors.append(error)
            elif airspeed > t.max_speed_vno:
                error = PilotError(
                    error_type=ErrorType.OVERSPEED,
                    severity=ErrorSeverity.WARNING,
                    message=f"Vitesse excessive: {airspeed:.0f} kts",
                    voice_message="Speed!",
                    details={'airspeed': airspeed, 'limit': t.max_speed_vno}
                )
                self._add_error(error)
                new_errors.append(error)
            else:
                self._clear_error(ErrorType.OVERSPEED)

        # V2 ENHANCED: Use SimConnect STALL_WARNING if available (more reliable)
        # Only skip stall check if pitot is iced and no system warning
        pitot_reliable = pitot_ice_pct is None or pitot_ice_pct < 0.1

        if stall_warning_active is not None and stall_warning_active:
            error = PilotError(
                error_type=ErrorType.STALL_WARNING,
                severity=ErrorSeverity.CRITICAL,
                message=f"STALL WARNING! {airspeed:.0f} kts (system warning)",
                voice_message="Stall! Stall! Push!",
                details={'airspeed': airspeed, 'source': 'simconnect_warning'}
            )
            self._add_error(error)
            new_errors.append(error)
        # Fallback to threshold-based detection (only if pitot is reliable)
        elif pitot_reliable and airspeed < t.stall_warning_speed and flight_phase not in ['takeoff_roll', 'landing_roll']:
            error = PilotError(
                error_type=ErrorType.STALL_WARNING,
                severity=ErrorSeverity.CRITICAL,
                message=f"STALL WARNING! {airspeed:.0f} kts",
                voice_message="Stall! Stall! Push!",
                details={'airspeed': airspeed}
            )
            self._add_error(error)
            new_errors.append(error)
        else:
            self._clear_error(ErrorType.STALL_WARNING)

        # ==================== G-FORCE WARNING (NEW V2) ====================
        if g_force is not None:
            if g_force > 3.0 or g_force < -1.0:
                error = PilotError(
                    error_type=ErrorType.BANK_ANGLE,  # Using BANK_ANGLE type for G-force
                    severity=ErrorSeverity.CRITICAL,
                    message=f"EXCESSIVE G! {g_force:.1f}G",
                    voice_message="G limit! G limit!",
                    details={'g_force': g_force}
                )
                self._add_error(error)
                new_errors.append(error)
            elif g_force > 2.5:
                error = PilotError(
                    error_type=ErrorType.BANK_ANGLE,
                    severity=ErrorSeverity.WARNING,
                    message=f"High G: {g_force:.1f}G",
                    voice_message="G force!",
                    details={'g_force': g_force}
                )
                self._add_error(error)
                new_errors.append(error)

        # ==================== ATTITUDE ERRORS ====================

        # Bank angle
        abs_bank = abs(bank_angle)
        if abs_bank > t.excessive_bank_angle:
            error = PilotError(
                error_type=ErrorType.BANK_ANGLE,
                severity=ErrorSeverity.CRITICAL,
                message=f"BANK ANGLE! {abs_bank:.0f} degrees",
                voice_message="Bank angle! Bank angle!",
                details={'bank_angle': bank_angle}
            )
            self._add_error(error)
            new_errors.append(error)
        elif abs_bank > t.max_bank_angle:
            error = PilotError(
                error_type=ErrorType.BANK_ANGLE,
                severity=ErrorSeverity.WARNING,
                message=f"Bank angle excessive: {abs_bank:.0f} degrees",
                voice_message="Bank angle",
                details={'bank_angle': bank_angle}
            )
            self._add_error(error)
            new_errors.append(error)
        else:
            self._clear_error(ErrorType.BANK_ANGLE)

        # Pitch attitude
        if pitch_angle > t.max_pitch_up:
            error = PilotError(
                error_type=ErrorType.PITCH_ATTITUDE,
                severity=ErrorSeverity.WARNING,
                message=f"Pitch excessive: {pitch_angle:.0f} degrees nose up",
                voice_message="Pitch! Pitch!",
                details={'pitch': pitch_angle}
            )
            self._add_error(error)
            new_errors.append(error)
        elif pitch_angle < t.max_pitch_down:
            error = PilotError(
                error_type=ErrorType.PITCH_ATTITUDE,
                severity=ErrorSeverity.WARNING,
                message=f"Pitch excessive: {abs(pitch_angle):.0f} degrees nose down",
                voice_message="Pitch! Pitch!",
                details={'pitch': pitch_angle}
            )
            self._add_error(error)
            new_errors.append(error)
        else:
            self._clear_error(ErrorType.PITCH_ATTITUDE)

        # ==================== CONFIGURATION ERRORS ====================

        # Gear not down on approach
        if flight_phase in ['approach', 'short_final', 'flare']:
            if not gear_down and altitude_agl < t.gear_altitude_agl:
                error = PilotError(
                    error_type=ErrorType.GEAR_NOT_DOWN,
                    severity=ErrorSeverity.CRITICAL,
                    message="TRAIN NON SORTI!",
                    voice_message="Gear! Gear! Check gear!",
                    details={'altitude_agl': altitude_agl}
                )
                self._add_error(error)
                new_errors.append(error)
            else:
                self._clear_error(ErrorType.GEAR_NOT_DOWN)

        # ==================== SINK RATE ====================
        # Only check sink rate during approach/landing phases or below 3000ft AGL
        # In cruise, high VS is normal (controlled descent)
        check_sink_rate = (
            flight_phase in ['approach', 'short_final', 'flare', 'landing_roll'] or
            altitude_agl < 3000
        )

        if check_sink_rate:
            # Use stricter thresholds at low altitude
            sink_threshold = t.excessive_sink_rate if altitude_agl > 1000 else -1500.0
            warn_threshold = t.max_sink_rate if altitude_agl > 1000 else -1000.0

            if vertical_speed < sink_threshold:
                error = PilotError(
                    error_type=ErrorType.SINK_RATE,
                    severity=ErrorSeverity.CRITICAL,
                    message=f"SINK RATE! {abs(vertical_speed):.0f} fpm",
                    voice_message="Sink rate! Pull up!",
                    details={'vertical_speed': vertical_speed}
                )
                self._add_error(error)
                new_errors.append(error)
            elif vertical_speed < warn_threshold:
                error = PilotError(
                    error_type=ErrorType.SINK_RATE,
                    severity=ErrorSeverity.WARNING,
                    message=f"Sink rate: {abs(vertical_speed):.0f} fpm",
                    voice_message="Sink rate",
                    details={'vertical_speed': vertical_speed}
                )
                self._add_error(error)
                new_errors.append(error)
            else:
                self._clear_error(ErrorType.SINK_RATE)
        else:
            self._clear_error(ErrorType.SINK_RATE)

        # ==================== UNSTABLE APPROACH ====================

        if flight_phase == 'short_final' and altitude_agl < t.stable_approach_alt:
            unstable_reasons = []

            if airspeed > t.max_approach_speed:
                unstable_reasons.append("vitesse")
            if abs(vertical_speed) > 1000:
                unstable_reasons.append("taux de descente")
            if abs(bank_angle) > 10:
                unstable_reasons.append("inclinaison")

            if unstable_reasons:
                error = PilotError(
                    error_type=ErrorType.UNSTABLE_APPROACH,
                    severity=ErrorSeverity.WARNING,
                    message=f"Approche non stabilisee: {', '.join(unstable_reasons)}",
                    voice_message="Unstable! Go around!",
                    details={'reasons': unstable_reasons}
                )
                self._add_error(error)
                new_errors.append(error)
                self._approach_stable = False
            else:
                self._clear_error(ErrorType.UNSTABLE_APPROACH)
                self._approach_stable = True

        return new_errors

    def acknowledge_error(self, error_type: ErrorType) -> None:
        """Acknowledge an error"""
        for error in self._active_errors:
            if error.error_type == error_type:
                error.acknowledged = True

    def acknowledge_all(self) -> None:
        """Acknowledge all errors"""
        for error in self._active_errors:
            error.acknowledged = True

    def reset(self) -> None:
        """Reset detector state"""
        self._active_errors.clear()
        self._error_history.clear()
        self._approach_stable = True
        logger.info("Error detector reset")

    def record_violation(self, constraint_type: str, constraint_value: float) -> None:
        """
        Record a constraint violation as an error

        Args:
            constraint_type: Type of constraint violated (bank, altitude_min, etc.)
            constraint_value: The threshold value that was exceeded
        """
        # Map constraint types to error types
        error_type_map = {
            'bank': ErrorType.BANK_ANGLE,
            'speed_max': ErrorType.OVERSPEED,
            'altitude_min': ErrorType.ALTITUDE_DEVIATION,
            'altitude_max': ErrorType.ALTITUDE_DEVIATION,
            'vs_max': ErrorType.SINK_RATE
        }

        error_type = error_type_map.get(constraint_type, ErrorType.OVERSPEED)

        error = PilotError(
            error_type=error_type,
            severity=ErrorSeverity.WARNING,
            message=f"Constraint violation: {constraint_type} > {constraint_value}",
            voice_message=f"Attention, {constraint_type} constraint exceeded",
            details={'constraint_type': constraint_type, 'value': constraint_value}
        )

        self._add_error(error)

    def get_stats(self) -> Dict:
        """Get error statistics"""
        return {
            'total_errors': len(self._error_history),
            'active_errors': len(self.active_errors),
            'critical_errors': sum(1 for e in self._error_history
                                   if e.severity == ErrorSeverity.CRITICAL),
            'approach_stable': self._approach_stable
        }


# Global error detector instance
_error_detector: Optional[ErrorDetector] = None

def get_error_detector() -> ErrorDetector:
    """Get or create global error detector"""
    global _error_detector
    if _error_detector is None:
        _error_detector = ErrorDetector()
    return _error_detector
