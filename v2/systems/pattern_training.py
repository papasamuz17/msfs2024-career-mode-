"""
Pattern Training Module - Tour de Piste Training
Tracks traffic pattern practice with scoring for takeoffs and landings
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Callable

logger = logging.getLogger("MissionGenerator.Systems.PatternTraining")


class PatternLeg(Enum):
    """Traffic pattern legs"""
    GROUND = "ground"
    TAKEOFF_ROLL = "takeoff_roll"
    INITIAL_CLIMB = "initial_climb"
    CROSSWIND = "crosswind"
    DOWNWIND = "downwind"
    BASE = "base"
    FINAL = "final"
    LANDING = "landing"
    TOUCH_AND_GO = "touch_and_go"
    FULL_STOP = "full_stop"


@dataclass
class TakeoffScore:
    """Score for a single takeoff"""
    rotation_speed_target: float = 0  # Target Vr
    rotation_speed_actual: float = 0  # Actual rotation speed
    rotation_score: int = 0  # 0-100

    centerline_deviation: float = 0  # Max deviation in degrees
    centerline_score: int = 0  # 0-100

    climb_rate: float = 0  # Initial climb rate
    climb_score: int = 0  # 0-100

    total_score: int = 0  # 0-100
    grade: str = "F"  # A, B, C, D, F

    timestamp: str = ""
    feedback: List[str] = field(default_factory=list)


@dataclass
class LandingScore:
    """Score for a single landing"""
    touchdown_rate: float = 0  # fpm at touchdown
    touchdown_score: int = 0  # 0-100

    centerline_deviation: float = 0  # Distance from centerline in meters
    centerline_score: int = 0  # 0-100

    approach_speed_target: float = 0  # Target Vref
    approach_speed_actual: float = 0  # Actual approach speed
    speed_score: int = 0  # 0-100

    glideslope_deviation: float = 0  # Degrees from ideal 3°
    glideslope_score: int = 0  # 0-100

    total_score: int = 0  # 0-100
    grade: str = "F"  # A, B, C, D, F

    timestamp: str = ""
    feedback: List[str] = field(default_factory=list)
    landing_type: str = "touch_and_go"  # touch_and_go or full_stop


@dataclass
class PatternScore:
    """Score for a complete pattern"""
    pattern_number: int = 0

    altitude_maintained: bool = True
    altitude_deviation_avg: float = 0  # Average deviation from pattern altitude
    altitude_score: int = 0  # 0-100

    coordination_score: int = 0  # Bank/slip coordination 0-100

    takeoff: Optional[TakeoffScore] = None
    landing: Optional[LandingScore] = None

    total_score: int = 0
    grade: str = "F"

    duration_seconds: float = 0
    timestamp_start: str = ""
    timestamp_end: str = ""


@dataclass
class PatternSession:
    """Complete training session"""
    airport_icao: str = ""
    runway: str = ""
    pattern_altitude: int = 1000  # AGL
    pattern_direction: str = "left"  # left or right

    patterns: List[PatternScore] = field(default_factory=list)

    session_start: str = ""
    session_end: str = ""

    best_landing_score: int = 0
    worst_landing_score: int = 100
    average_landing_score: float = 0

    best_takeoff_score: int = 0
    average_takeoff_score: float = 0

    total_patterns: int = 0
    total_touch_and_go: int = 0
    total_full_stop: int = 0


class PatternTrainer:
    """
    Traffic Pattern Training System
    Tracks and scores takeoffs, pattern flying, and landings
    """

    def __init__(self):
        self._active = False
        self._session: Optional[PatternSession] = None
        self._current_pattern: Optional[PatternScore] = None
        self._current_leg = PatternLeg.GROUND
        self._previous_leg = PatternLeg.GROUND

        # Airport/runway info
        self._airport_lat = 0.0
        self._airport_lon = 0.0
        self._runway_heading = 0
        self._airport_elevation = 0

        # Pattern settings
        self._pattern_altitude_agl = 1000  # Default 1000 ft AGL
        self._pattern_direction = "left"  # left or right hand pattern

        # V-speeds
        self._vr = 55  # Rotation speed
        self._vref = 65  # Approach speed

        # State tracking
        self._was_on_ground = True
        self._takeoff_started = False
        self._rotation_detected = False
        self._max_centerline_deviation = 0
        self._climb_rate_samples = []

        # Landing tracking
        self._on_final = False
        self._approach_speed_samples = []
        self._glideslope_samples = []
        self._touchdown_detected = False

        # Altitude tracking for pattern
        self._altitude_samples = []
        self._bank_samples = []

        # Callbacks
        self._on_leg_change: Optional[Callable] = None
        self._on_pattern_complete: Optional[Callable] = None
        self._on_session_end: Optional[Callable] = None

        logger.info("Pattern trainer initialized")

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def current_leg(self) -> PatternLeg:
        return self._current_leg

    @property
    def session(self) -> Optional[PatternSession]:
        return self._session

    @property
    def current_pattern(self) -> Optional[PatternScore]:
        return self._current_pattern

    def set_callbacks(self, on_leg_change: Callable = None,
                      on_pattern_complete: Callable = None,
                      on_session_end: Callable = None):
        """Set event callbacks"""
        self._on_leg_change = on_leg_change
        self._on_pattern_complete = on_pattern_complete
        self._on_session_end = on_session_end

    def set_vspeeds(self, vr: float, vref: float):
        """Set V-speeds for scoring"""
        self._vr = vr
        self._vref = vref
        logger.info(f"V-speeds set: Vr={vr}, Vref={vref}")

    def start_session(self, airport_icao: str, runway: str,
                      airport_lat: float, airport_lon: float,
                      runway_heading: float, airport_elevation: float,
                      pattern_altitude_agl: int = 1000,
                      pattern_direction: str = "left") -> PatternSession:
        """Start a new training session"""
        self._session = PatternSession(
            airport_icao=airport_icao,
            runway=runway,
            pattern_altitude=pattern_altitude_agl,
            pattern_direction=pattern_direction,
            session_start=datetime.now().isoformat()
        )

        self._airport_lat = airport_lat
        self._airport_lon = airport_lon
        self._runway_heading = runway_heading
        self._airport_elevation = airport_elevation
        self._pattern_altitude_agl = pattern_altitude_agl
        self._pattern_direction = pattern_direction

        self._active = True
        self._current_leg = PatternLeg.GROUND
        self._current_pattern = None

        # Reset tracking
        self._was_on_ground = True
        self._takeoff_started = False

        logger.info(f"Pattern training started: {airport_icao} RWY {runway}, "
                   f"pattern alt {pattern_altitude_agl}ft AGL, {pattern_direction} hand")

        return self._session

    def stop_session(self) -> PatternSession:
        """Stop the training session and return results"""
        if not self._session:
            return None

        self._session.session_end = datetime.now().isoformat()
        self._active = False

        # Calculate session statistics
        self._calculate_session_stats()

        if self._on_session_end:
            self._on_session_end(self._session)

        logger.info(f"Pattern training ended: {self._session.total_patterns} patterns completed")

        result = self._session
        self._session = None
        self._current_pattern = None

        return result

    def _calculate_session_stats(self):
        """Calculate session statistics"""
        if not self._session or not self._session.patterns:
            return

        landing_scores = []
        takeoff_scores = []

        for pattern in self._session.patterns:
            if pattern.landing:
                landing_scores.append(pattern.landing.total_score)
                if pattern.landing.landing_type == "touch_and_go":
                    self._session.total_touch_and_go += 1
                else:
                    self._session.total_full_stop += 1

            if pattern.takeoff:
                takeoff_scores.append(pattern.takeoff.total_score)

        self._session.total_patterns = len(self._session.patterns)

        if landing_scores:
            self._session.best_landing_score = max(landing_scores)
            self._session.worst_landing_score = min(landing_scores)
            self._session.average_landing_score = sum(landing_scores) / len(landing_scores)

        if takeoff_scores:
            self._session.best_takeoff_score = max(takeoff_scores)
            self._session.average_takeoff_score = sum(takeoff_scores) / len(takeoff_scores)

    def update(self, latitude: float, longitude: float,
               altitude_msl: float, altitude_agl: float,
               heading: float, airspeed: float,
               vertical_speed: float, on_ground: bool,
               bank_angle: float = 0, gear_down: bool = True):
        """
        Update pattern tracking with current flight data
        Call this every update cycle
        """
        if not self._active:
            return

        # Detect leg changes
        new_leg = self._detect_leg(
            latitude, longitude, altitude_agl, heading,
            airspeed, vertical_speed, on_ground, bank_angle
        )

        if new_leg != self._current_leg:
            self._on_leg_changed(new_leg, airspeed, vertical_speed,
                                altitude_agl, bank_angle, on_ground)

        # Track data for scoring
        self._track_data(altitude_agl, airspeed, vertical_speed,
                        heading, bank_angle, on_ground)

        self._was_on_ground = on_ground

    def _detect_leg(self, lat: float, lon: float, alt_agl: float,
                    heading: float, airspeed: float, vs: float,
                    on_ground: bool, bank: float) -> PatternLeg:
        """Detect current pattern leg based on flight parameters"""

        # On ground
        if on_ground:
            if self._current_leg == PatternLeg.LANDING:
                # Just landed - check if touch and go or full stop
                if airspeed > 30:  # Still rolling fast - might be touch and go
                    return PatternLeg.LANDING
                else:
                    return PatternLeg.FULL_STOP
            elif self._current_leg in [PatternLeg.TOUCH_AND_GO, PatternLeg.TAKEOFF_ROLL]:
                if airspeed > 40:
                    return PatternLeg.TAKEOFF_ROLL
                return self._current_leg
            elif airspeed > 30:
                # Accelerating on ground - takeoff roll
                return PatternLeg.TAKEOFF_ROLL
            return PatternLeg.GROUND

        # In the air
        if self._was_on_ground and not on_ground:
            # Just lifted off
            return PatternLeg.INITIAL_CLIMB

        # Calculate relative heading to runway
        rel_heading = self._normalize_heading(heading - self._runway_heading)

        # Pattern altitude check (within 200ft of target)
        at_pattern_alt = abs(alt_agl - self._pattern_altitude_agl) < 300

        # Determine leg based on heading and position
        if self._current_leg == PatternLeg.INITIAL_CLIMB:
            # Check for crosswind turn (90° turn from runway heading)
            if self._pattern_direction == "left":
                crosswind_heading = self._normalize_heading(self._runway_heading - 90)
            else:
                crosswind_heading = self._normalize_heading(self._runway_heading + 90)

            heading_diff = abs(self._normalize_heading(heading - crosswind_heading))
            if heading_diff < 30 and alt_agl > 300:
                return PatternLeg.CROSSWIND

            # Still climbing straight out
            if vs > 200:
                return PatternLeg.INITIAL_CLIMB

        if self._current_leg == PatternLeg.CROSSWIND:
            # Check for downwind (opposite runway heading)
            downwind_heading = self._normalize_heading(self._runway_heading + 180)
            heading_diff = abs(self._normalize_heading(heading - downwind_heading))
            if heading_diff < 30:
                return PatternLeg.DOWNWIND
            return PatternLeg.CROSSWIND

        if self._current_leg == PatternLeg.DOWNWIND:
            # Check for base turn
            if self._pattern_direction == "left":
                base_heading = self._normalize_heading(self._runway_heading + 90)
            else:
                base_heading = self._normalize_heading(self._runway_heading - 90)

            heading_diff = abs(self._normalize_heading(heading - base_heading))
            if heading_diff < 45:
                return PatternLeg.BASE

            # Check if starting descent (might be turning base)
            if vs < -200 and abs(bank) > 15:
                return PatternLeg.BASE

            return PatternLeg.DOWNWIND

        if self._current_leg == PatternLeg.BASE:
            # Check for final (aligned with runway)
            heading_diff = abs(self._normalize_heading(heading - self._runway_heading))
            if heading_diff < 30:
                return PatternLeg.FINAL
            return PatternLeg.BASE

        if self._current_leg == PatternLeg.FINAL:
            if on_ground:
                return PatternLeg.LANDING
            return PatternLeg.FINAL

        if self._current_leg == PatternLeg.LANDING:
            if not on_ground and vs > 100:
                # Touch and go - lifting off again
                return PatternLeg.TOUCH_AND_GO
            return PatternLeg.LANDING

        if self._current_leg == PatternLeg.TOUCH_AND_GO:
            if vs > 200 and alt_agl > 50:
                return PatternLeg.INITIAL_CLIMB
            return PatternLeg.TOUCH_AND_GO

        # Default: try to determine from heading if we're established in pattern
        if at_pattern_alt:
            downwind_heading = self._normalize_heading(self._runway_heading + 180)
            if abs(self._normalize_heading(heading - downwind_heading)) < 30:
                return PatternLeg.DOWNWIND

        # On final approach?
        heading_diff = abs(self._normalize_heading(heading - self._runway_heading))
        if heading_diff < 30 and vs < -200 and alt_agl < self._pattern_altitude_agl:
            return PatternLeg.FINAL

        return self._current_leg

    def _on_leg_changed(self, new_leg: PatternLeg, airspeed: float,
                        vs: float, alt_agl: float, bank: float, on_ground: bool):
        """Handle leg change"""
        old_leg = self._current_leg
        self._previous_leg = old_leg
        self._current_leg = new_leg

        logger.info(f"Pattern leg: {old_leg.value} -> {new_leg.value}")

        # Start new pattern on takeoff
        if new_leg == PatternLeg.TAKEOFF_ROLL and old_leg == PatternLeg.GROUND:
            self._start_new_pattern()
            self._takeoff_started = True
            self._rotation_detected = False
            self._max_centerline_deviation = 0
            self._climb_rate_samples = []

        # Rotation detected
        if new_leg == PatternLeg.INITIAL_CLIMB and old_leg == PatternLeg.TAKEOFF_ROLL:
            self._rotation_detected = True
            if self._current_pattern and self._current_pattern.takeoff:
                self._current_pattern.takeoff.rotation_speed_actual = airspeed
                self._current_pattern.takeoff.rotation_speed_target = self._vr

        # Touch and go - score landing and start new pattern
        if new_leg == PatternLeg.TOUCH_AND_GO:
            self._score_landing(vs, "touch_and_go")
            self._complete_pattern()
            self._start_new_pattern()
            self._takeoff_started = True

        # Full stop - score landing and complete pattern
        if new_leg == PatternLeg.FULL_STOP:
            self._score_landing(vs, "full_stop")
            self._complete_pattern()

        # Entering final - reset approach tracking
        if new_leg == PatternLeg.FINAL:
            self._on_final = True
            self._approach_speed_samples = []
            self._glideslope_samples = []

        # Callback
        if self._on_leg_change:
            self._on_leg_change(old_leg, new_leg)

    def _start_new_pattern(self):
        """Start tracking a new pattern"""
        pattern_num = len(self._session.patterns) + 1 if self._session else 1

        self._current_pattern = PatternScore(
            pattern_number=pattern_num,
            timestamp_start=datetime.now().isoformat(),
            takeoff=TakeoffScore(timestamp=datetime.now().isoformat()),
            landing=LandingScore()
        )

        self._altitude_samples = []
        self._bank_samples = []

        logger.info(f"Starting pattern #{pattern_num}")

    def _complete_pattern(self):
        """Complete current pattern and add to session"""
        if not self._current_pattern:
            return

        self._current_pattern.timestamp_end = datetime.now().isoformat()

        # Calculate pattern duration
        try:
            start = datetime.fromisoformat(self._current_pattern.timestamp_start)
            end = datetime.fromisoformat(self._current_pattern.timestamp_end)
            self._current_pattern.duration_seconds = (end - start).total_seconds()
        except:
            pass

        # Score altitude maintenance
        if self._altitude_samples:
            avg_deviation = sum(self._altitude_samples) / len(self._altitude_samples)
            self._current_pattern.altitude_deviation_avg = avg_deviation
            self._current_pattern.altitude_score = self._score_altitude(avg_deviation)
            self._current_pattern.altitude_maintained = avg_deviation < 150

        # Score coordination (bank angles)
        if self._bank_samples:
            # Good coordination = smooth, consistent banks
            max_bank = max(abs(b) for b in self._bank_samples) if self._bank_samples else 0
            self._current_pattern.coordination_score = max(0, 100 - int(max_bank - 30) * 2) if max_bank > 30 else 100

        # Score takeoff
        self._score_takeoff()

        # Calculate total pattern score
        scores = []
        if self._current_pattern.takeoff:
            scores.append(self._current_pattern.takeoff.total_score)
        if self._current_pattern.landing:
            scores.append(self._current_pattern.landing.total_score)
        scores.append(self._current_pattern.altitude_score)
        scores.append(self._current_pattern.coordination_score)

        if scores:
            self._current_pattern.total_score = int(sum(scores) / len(scores))
            self._current_pattern.grade = self._score_to_grade(self._current_pattern.total_score)

        # Add to session
        if self._session:
            self._session.patterns.append(self._current_pattern)

        logger.info(f"Pattern #{self._current_pattern.pattern_number} completed: "
                   f"Score {self._current_pattern.total_score} ({self._current_pattern.grade})")

        if self._on_pattern_complete:
            self._on_pattern_complete(self._current_pattern)

        self._current_pattern = None

    def _track_data(self, alt_agl: float, airspeed: float, vs: float,
                    heading: float, bank: float, on_ground: bool):
        """Track data for scoring"""

        # Track altitude deviation on downwind
        if self._current_leg == PatternLeg.DOWNWIND:
            deviation = abs(alt_agl - self._pattern_altitude_agl)
            self._altitude_samples.append(deviation)

        # Track bank angles in turns
        if self._current_leg in [PatternLeg.CROSSWIND, PatternLeg.BASE]:
            self._bank_samples.append(bank)

        # Track approach speed on final
        if self._current_leg == PatternLeg.FINAL:
            self._approach_speed_samples.append(airspeed)
            # Estimate glideslope from VS and groundspeed (simplified)
            if airspeed > 50:
                gs_angle = math.degrees(math.atan2(-vs, airspeed * 101.269))  # Convert to ft/min basis
                self._glideslope_samples.append(abs(gs_angle - 3.0))  # Deviation from 3°

        # Track centerline deviation during takeoff roll
        if self._current_leg == PatternLeg.TAKEOFF_ROLL and not on_ground:
            heading_dev = abs(self._normalize_heading(heading - self._runway_heading))
            if heading_dev > self._max_centerline_deviation:
                self._max_centerline_deviation = heading_dev

        # Track initial climb rate
        if self._current_leg == PatternLeg.INITIAL_CLIMB and vs > 0:
            self._climb_rate_samples.append(vs)

    def _score_takeoff(self):
        """Score the takeoff"""
        if not self._current_pattern or not self._current_pattern.takeoff:
            return

        takeoff = self._current_pattern.takeoff

        # Rotation speed score
        if takeoff.rotation_speed_actual > 0 and self._vr > 0:
            speed_diff = abs(takeoff.rotation_speed_actual - self._vr)
            takeoff.rotation_score = max(0, 100 - int(speed_diff * 5))
        else:
            takeoff.rotation_score = 70  # Default if not detected

        # Centerline score
        takeoff.centerline_deviation = self._max_centerline_deviation
        takeoff.centerline_score = max(0, 100 - int(self._max_centerline_deviation * 5))

        # Climb score
        if self._climb_rate_samples:
            avg_climb = sum(self._climb_rate_samples) / len(self._climb_rate_samples)
            takeoff.climb_rate = avg_climb
            # Good climb rate is 500-1000 fpm for light aircraft
            if 400 <= avg_climb <= 1200:
                takeoff.climb_score = 100
            elif avg_climb < 400:
                takeoff.climb_score = max(0, int(avg_climb / 4))
            else:
                takeoff.climb_score = max(0, 100 - int((avg_climb - 1200) / 10))
        else:
            takeoff.climb_score = 70

        # Total score
        takeoff.total_score = int(
            takeoff.rotation_score * 0.3 +
            takeoff.centerline_score * 0.4 +
            takeoff.climb_score * 0.3
        )
        takeoff.grade = self._score_to_grade(takeoff.total_score)

        # Generate feedback
        takeoff.feedback = []
        if takeoff.rotation_score < 70:
            if takeoff.rotation_speed_actual < self._vr:
                takeoff.feedback.append(f"Rotation precoce ({takeoff.rotation_speed_actual:.0f} kt vs Vr {self._vr:.0f} kt)")
            else:
                takeoff.feedback.append(f"Rotation tardive ({takeoff.rotation_speed_actual:.0f} kt vs Vr {self._vr:.0f} kt)")
        if takeoff.centerline_score < 70:
            takeoff.feedback.append(f"Deviation d'axe: {takeoff.centerline_deviation:.0f} degres")
        if takeoff.climb_score < 70:
            takeoff.feedback.append(f"Taux de montee: {takeoff.climb_rate:.0f} fpm")

    def _score_landing(self, touchdown_vs: float, landing_type: str):
        """Score the landing"""
        if not self._current_pattern:
            return

        if not self._current_pattern.landing:
            self._current_pattern.landing = LandingScore()

        landing = self._current_pattern.landing
        landing.landing_type = landing_type
        landing.timestamp = datetime.now().isoformat()

        # Touchdown rate score
        landing.touchdown_rate = abs(touchdown_vs)
        if landing.touchdown_rate < 100:
            landing.touchdown_score = 100  # Butter!
        elif landing.touchdown_rate < 200:
            landing.touchdown_score = 90
        elif landing.touchdown_rate < 300:
            landing.touchdown_score = 75
        elif landing.touchdown_rate < 400:
            landing.touchdown_score = 60
        elif landing.touchdown_rate < 600:
            landing.touchdown_score = 40
        else:
            landing.touchdown_score = max(0, 100 - int(landing.touchdown_rate / 10))

        # Approach speed score
        if self._approach_speed_samples:
            landing.approach_speed_actual = sum(self._approach_speed_samples) / len(self._approach_speed_samples)
            landing.approach_speed_target = self._vref
            speed_diff = abs(landing.approach_speed_actual - self._vref)
            landing.speed_score = max(0, 100 - int(speed_diff * 4))
        else:
            landing.speed_score = 70

        # Glideslope score
        if self._glideslope_samples:
            avg_deviation = sum(self._glideslope_samples) / len(self._glideslope_samples)
            landing.glideslope_deviation = avg_deviation
            landing.glideslope_score = max(0, 100 - int(avg_deviation * 20))
        else:
            landing.glideslope_score = 70

        # Centerline score (simplified - would need lateral position data)
        landing.centerline_score = 80  # Default good score

        # Total score
        landing.total_score = int(
            landing.touchdown_score * 0.4 +
            landing.speed_score * 0.25 +
            landing.glideslope_score * 0.2 +
            landing.centerline_score * 0.15
        )
        landing.grade = self._score_to_grade(landing.total_score)

        # Generate feedback
        landing.feedback = []
        if landing.touchdown_score >= 90:
            landing.feedback.append("Excellent atterrissage!")
        elif landing.touchdown_score >= 75:
            landing.feedback.append("Bon atterrissage")
        elif landing.touchdown_score >= 60:
            landing.feedback.append("Atterrissage acceptable")
        elif landing.touchdown_score < 40:
            landing.feedback.append(f"Atterrissage dur ({landing.touchdown_rate:.0f} fpm)")

        if landing.speed_score < 70:
            if landing.approach_speed_actual > self._vref + 10:
                landing.feedback.append(f"Approche trop rapide ({landing.approach_speed_actual:.0f} kt)")
            elif landing.approach_speed_actual < self._vref - 5:
                landing.feedback.append(f"Approche trop lente ({landing.approach_speed_actual:.0f} kt)")

        logger.info(f"Landing scored: {landing.total_score} ({landing.grade}) - "
                   f"VS: {landing.touchdown_rate:.0f} fpm")

    def _score_altitude(self, deviation: float) -> int:
        """Score altitude maintenance"""
        if deviation < 50:
            return 100
        elif deviation < 100:
            return 90
        elif deviation < 150:
            return 75
        elif deviation < 200:
            return 60
        elif deviation < 300:
            return 40
        else:
            return max(0, 100 - int(deviation / 5))

    def _score_to_grade(self, score: int) -> str:
        """Convert numeric score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _normalize_heading(self, heading: float) -> float:
        """Normalize heading to -180 to +180"""
        while heading > 180:
            heading -= 360
        while heading < -180:
            heading += 360
        return heading

    def get_leg_callout(self) -> Optional[str]:
        """Get callout text for current leg"""
        callouts = {
            PatternLeg.TAKEOFF_ROLL: "Decollage",
            PatternLeg.INITIAL_CLIMB: "Montee initiale",
            PatternLeg.CROSSWIND: "Vent traversier",
            PatternLeg.DOWNWIND: f"Vent arriere, verifiez altitude {self._pattern_altitude_agl} pieds",
            PatternLeg.BASE: "Base",
            PatternLeg.FINAL: "Finale, train sorti, volets",
            PatternLeg.LANDING: "Atterrissage",
            PatternLeg.TOUCH_AND_GO: "Touch and go",
            PatternLeg.FULL_STOP: "Arret complet"
        }
        return callouts.get(self._current_leg)

    def get_session_summary(self) -> str:
        """Get text summary of current session"""
        if not self._session:
            return "Pas de session active"

        self._calculate_session_stats()

        lines = [
            f"=== Session Tour de Piste ===",
            f"Aeroport: {self._session.airport_icao} RWY {self._session.runway}",
            f"Patterns completes: {self._session.total_patterns}",
            f"Touch & Go: {self._session.total_touch_and_go}",
            f"Full Stop: {self._session.total_full_stop}",
            "",
            f"Meilleur atterrissage: {self._session.best_landing_score}",
            f"Pire atterrissage: {self._session.worst_landing_score}",
            f"Moyenne atterrissages: {self._session.average_landing_score:.0f}",
            "",
            f"Meilleur decollage: {self._session.best_takeoff_score}",
            f"Moyenne decollages: {self._session.average_takeoff_score:.0f}"
        ]

        return "\n".join(lines)


# Singleton instance
_pattern_trainer: Optional[PatternTrainer] = None


def get_pattern_trainer() -> PatternTrainer:
    """Get or create pattern trainer instance"""
    global _pattern_trainer
    if _pattern_trainer is None:
        _pattern_trainer = PatternTrainer()
    return _pattern_trainer
