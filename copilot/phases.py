"""
Flight Phase Detection for V2 Copilot
Detects current flight phase based on aircraft state
"""

import logging
import math
from enum import Enum
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Copilot.Phases")


class FlightPhase(Enum):
    """Flight phases"""
    UNKNOWN = "unknown"           # Not in active flight (menu, loading, etc.)
    PREFLIGHT = "preflight"       # Cold & dark, before engine start
    ENGINE_START = "engine_start" # Engine starting/running, parked
    TAXI_OUT = "taxi_out"         # Taxiing to runway (before takeoff)
    HOLDING = "holding"           # Holding short of runway
    TAKEOFF_ROLL = "takeoff_roll" # Accelerating on runway
    ROTATION = "rotation"         # Liftoff moment
    INITIAL_CLIMB = "initial_climb"  # Below transition altitude
    CLIMB = "climb"               # Climbing to cruise
    CRUISE = "cruise"             # Level flight
    DESCENT = "descent"           # Descending from cruise
    APPROACH = "approach"         # Approaching airport
    SHORT_FINAL = "short_final"   # Below 500ft AGL
    FLARE = "flare"               # Touchdown imminent
    LANDING_ROLL = "landing_roll" # Decelerating on runway
    TAXI_IN = "taxi_in"           # Taxiing to parking (after landing)
    SHUTDOWN = "shutdown"         # Engine shutdown
    PARKED = "parked"             # Parked, engines off


@dataclass
class AircraftProfile:
    """Aircraft-specific thresholds for phase detection"""
    name: str

    # Ground speeds (kts)
    taxi_min_speed: float = 2.0      # Below = stopped
    taxi_max_speed: float = 25.0     # Normal taxi speed max
    takeoff_roll_speed: float = 40.0 # Speed to detect takeoff roll
    rotation_speed: float = 55.0     # Typical Vr

    # Altitudes (ft AGL)
    initial_climb_alt: float = 1000.0
    approach_alt: float = 3000.0
    short_final_alt: float = 500.0
    flare_alt: float = 50.0

    # Vertical speeds (fpm)
    climb_vs_threshold: float = 500.0
    descent_vs_threshold: float = -500.0
    level_vs_tolerance: float = 300.0

    # Rotation
    rotation_pitch: float = 5.0  # degrees nose up


# Aircraft profiles by category
AIRCRAFT_PROFILES = {
    'light_piston': AircraftProfile(
        name="Light Piston (C172, PA28)",
        taxi_min_speed=2.0,
        taxi_max_speed=20.0,
        takeoff_roll_speed=35.0,
        rotation_speed=55.0,
        climb_vs_threshold=400.0,
        descent_vs_threshold=-400.0,
        level_vs_tolerance=250.0,
    ),
    'light_turboprop': AircraftProfile(
        name="Light Turboprop (PC-12, TBM)",
        taxi_min_speed=2.0,
        taxi_max_speed=25.0,
        takeoff_roll_speed=50.0,
        rotation_speed=85.0,
        climb_vs_threshold=1000.0,  # Increased for turboprop variability
        descent_vs_threshold=-1000.0,
        level_vs_tolerance=800.0,  # More tolerance for AP oscillation and turbulence
    ),
    'medium_turboprop': AircraftProfile(
        name="Medium Turboprop (ATR, Dash-8)",
        taxi_min_speed=2.0,
        taxi_max_speed=25.0,
        takeoff_roll_speed=60.0,
        rotation_speed=110.0,
        climb_vs_threshold=1200.0,
        descent_vs_threshold=-1200.0,
        level_vs_tolerance=900.0,  # More tolerance for turboprop variability
    ),
    'light_jet': AircraftProfile(
        name="Light Jet (Citation, Phenom)",
        taxi_min_speed=2.0,
        taxi_max_speed=30.0,
        takeoff_roll_speed=80.0,
        rotation_speed=120.0,
        climb_vs_threshold=1200.0,
        descent_vs_threshold=-1200.0,
        level_vs_tolerance=800.0,
    ),
    'medium_jet': AircraftProfile(
        name="Medium Jet (A320, B737)",
        taxi_min_speed=2.0,
        taxi_max_speed=30.0,
        takeoff_roll_speed=100.0,
        rotation_speed=145.0,
        climb_vs_threshold=1800.0,
        descent_vs_threshold=-1800.0,
        level_vs_tolerance=900.0,
    ),
    'heavy_jet': AircraftProfile(
        name="Heavy Jet (B777, A350)",
        taxi_min_speed=2.0,
        taxi_max_speed=30.0,
        takeoff_roll_speed=120.0,
        rotation_speed=160.0,
        climb_vs_threshold=2500.0,
        descent_vs_threshold=-2500.0,
        level_vs_tolerance=1000.0,
    ),
}


@dataclass
class FlightState:
    """Current flight state from SimConnect"""
    # Core state
    sim_running: bool = False        # True if simulation is active (not in menu)
    on_ground: bool = True
    altitude_agl: float = 0.0
    altitude_msl: float = 0.0
    airspeed: float = 0.0
    ground_speed: float = 0.0
    vertical_speed: float = 0.0      # fpm
    pitch: float = 0.0               # degrees
    heading: float = 0.0             # degrees true
    has_flown: bool = False          # True if aircraft has flown at least 1nm this session

    # Aircraft systems
    engine_running: bool = False
    parking_brake: bool = True
    gear_down: bool = True
    flaps_percent: float = 0.0
    throttle_percent: float = 0.0    # Throttle position 0-100%
    spoilers_percent: float = 0.0    # Spoilers/speedbrakes position 0-100%

    # Lights (for phase detection)
    light_beacon: bool = False       # Beacon ON = ready for departure
    light_landing: bool = False      # Landing lights = approach/landing
    light_taxi: bool = False         # Taxi lights = taxiing

    # Parking state (from SimConnect)
    in_parking_state: bool = False   # PLANE IN PARKING STATE

    # Position
    latitude: float = 0.0
    longitude: float = 0.0

    # === NEW V2 ENHANCED DATA ===

    # System warnings (from SimConnect - more reliable than thresholds)
    stall_warning: bool = False      # STALL_WARNING - system stall warning active
    overspeed_warning: bool = False  # OVERSPEED_WARNING - system overspeed warning

    # Landing metrics
    g_force: float = 1.0             # G_FORCE - current G-forces
    touchdown_velocity: float = 0.0  # PLANE_TOUCHDOWN_NORMAL_VELOCITY - ft/s at last touchdown

    # Engine stress metrics
    engine_rpm_percent: float = 0.0  # GENERAL_ENG_PCT_MAX_RPM - % of max RPM
    engine_oil_temp: float = 0.0     # GENERAL_ENG_OIL_TEMPERATURE - Rankine

    # Fuel flow
    fuel_flow_gph: float = 0.0       # Total fuel flow from all engines (GPH)

    # Weather data
    density_altitude: float = 0.0    # DENSITY_ALTITUDE - calculated from conditions
    structural_ice_pct: float = 0.0  # STRUCTURAL_ICE_PCT - icing accumulation (0-1)
    pitot_ice_pct: float = 0.0       # PITOT_ICE_PCT - pitot tube icing (0-1)

    # Autopilot state
    autopilot_master: bool = False   # AUTOPILOT_MASTER - AP engaged
    autopilot_approach: bool = False # AUTOPILOT_APPROACH_HOLD - approach mode
    autopilot_glideslope: bool = False  # AUTOPILOT_GLIDESLOPE_ACTIVE - G/S captured


@dataclass
class PhaseTransition:
    """Record of a phase transition"""
    from_phase: FlightPhase
    to_phase: FlightPhase
    timestamp: str
    altitude_ft: float
    airspeed_kts: float
    vertical_speed_fpm: float


class FlightPhaseDetector:
    """
    Detects current flight phase based on aircraft parameters
    """

    # Smoothing samples for vertical speed
    VS_SMOOTH_SAMPLES = 5

    # Minimum time in phase before allowing change (seconds)
    MIN_PHASE_DURATION = 5.0    # Increased from 3s for stability
    MIN_CRUISE_DURATION = 30.0  # Much longer to prevent oscillation in cruise

    def __init__(self, aircraft_category: str = 'light_piston'):
        self._profile = AIRCRAFT_PROFILES.get(aircraft_category, AIRCRAFT_PROFILES['light_piston'])
        self._current_phase = FlightPhase.UNKNOWN
        self._previous_phase = FlightPhase.UNKNOWN
        self._phase_start_time: Optional[datetime] = None
        self._transitions: List[PhaseTransition] = []
        self._callbacks: List[Callable[[FlightPhase, FlightPhase], None]] = []

        # Flight tracking
        self._flight_started = False      # True once we've taken off
        self._has_landed = False          # True once we've landed after takeoff
        self._was_on_ground = True
        self._was_airborne = False
        self._first_update = True

        # Vertical speed smoothing
        self._vs_buffer: List[float] = []

        # Airport/runway info
        self._departure_lat: Optional[float] = None
        self._departure_lon: Optional[float] = None
        self._departure_heading: Optional[float] = None
        self._arrival_lat: Optional[float] = None
        self._arrival_lon: Optional[float] = None
        self._arrival_heading: Optional[float] = None

        logger.info(f"Phase detector initialized with profile: {self._profile.name}")

    def set_aircraft_category(self, category: str) -> None:
        """Change aircraft profile"""
        if category in AIRCRAFT_PROFILES:
            self._profile = AIRCRAFT_PROFILES[category]
            logger.info(f"Aircraft profile changed to: {self._profile.name}")
        else:
            logger.warning(f"Unknown aircraft category: {category}, using light_piston")
            self._profile = AIRCRAFT_PROFILES['light_piston']

    def set_departure(self, lat: float, lon: float, runway_heading: float = None) -> None:
        """Set departure airport info"""
        self._departure_lat = lat
        self._departure_lon = lon
        self._departure_heading = runway_heading
        logger.info(f"Departure set: {lat:.4f}, {lon:.4f}, heading: {runway_heading}")

    def set_arrival(self, lat: float, lon: float, runway_heading: float = None) -> None:
        """Set arrival airport info"""
        self._arrival_lat = lat
        self._arrival_lon = lon
        self._arrival_heading = runway_heading
        logger.info(f"Arrival set: {lat:.4f}, {lon:.4f}, heading: {runway_heading}")

    @property
    def current_phase(self) -> FlightPhase:
        return self._current_phase

    @property
    def previous_phase(self) -> FlightPhase:
        return self._previous_phase

    @property
    def profile(self) -> AircraftProfile:
        return self._profile

    @property
    def flight_started(self) -> bool:
        return self._flight_started

    @property
    def has_landed(self) -> bool:
        return self._has_landed

    def _phase_duration(self) -> float:
        """Seconds in current phase"""
        if not self._phase_start_time:
            return 0.0
        return (datetime.now() - self._phase_start_time).total_seconds()

    def _smooth_vs(self, vs: float) -> float:
        """Apply smoothing to vertical speed"""
        self._vs_buffer.append(vs)
        if len(self._vs_buffer) > self.VS_SMOOTH_SAMPLES:
            self._vs_buffer.pop(0)
        if len(self._vs_buffer) >= 2:
            return sum(self._vs_buffer) / len(self._vs_buffer)
        return vs

    def _distance_to(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance in meters"""
        if lat2 is None or lon2 is None:
            return float('inf')
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    def _heading_aligned(self, hdg: float, runway_hdg: Optional[float], tolerance: float = 20.0) -> bool:
        """Check if heading is aligned with runway (either direction)"""
        if runway_hdg is None:
            return False
        diff1 = abs((hdg - runway_hdg + 180) % 360 - 180)
        diff2 = abs((hdg - (runway_hdg + 180) + 180) % 360 - 180)
        return min(diff1, diff2) <= tolerance

    def _set_phase(self, new_phase: FlightPhase, state: FlightState, force: bool = False) -> None:
        """Set new phase with hysteresis check"""
        if new_phase == self._current_phase:
            return

        # Hysteresis - minimum time in phase
        min_duration = self.MIN_CRUISE_DURATION if self._current_phase == FlightPhase.CRUISE else self.MIN_PHASE_DURATION
        if not force and self._phase_duration() < min_duration:
            return

        old_phase = self._current_phase
        self._previous_phase = old_phase
        self._current_phase = new_phase
        self._phase_start_time = datetime.now()

        # Record transition
        self._transitions.append(PhaseTransition(
            from_phase=old_phase,
            to_phase=new_phase,
            timestamp=self._phase_start_time.isoformat(),
            altitude_ft=state.altitude_agl,
            airspeed_kts=state.airspeed,
            vertical_speed_fpm=state.vertical_speed
        ))

        logger.info(f"Phase: {old_phase.value} -> {new_phase.value}")

        # Notify callbacks
        for cb in self._callbacks:
            try:
                cb(new_phase, old_phase)
            except Exception as e:
                logger.error(f"Phase callback error: {e}")

    def register_callback(self, callback: Callable[[FlightPhase, FlightPhase], None]) -> None:
        """Register phase change callback"""
        self._callbacks.append(callback)

    def update(self, state: FlightState) -> FlightPhase:
        """
        Update phase detection with current flight state

        Args:
            state: Current FlightState from SimConnect

        Returns:
            Current FlightPhase
        """
        p = self._profile  # Shorthand for profile

        # ========== CHECK IF SIM IS RUNNING ==========
        if not state.sim_running:
            if self._current_phase != FlightPhase.UNKNOWN:
                self._set_phase(FlightPhase.UNKNOWN, state, force=True)
            return self._current_phase

        # ========== COMING OUT OF PAUSE - RE-DETECT PHASE ==========
        # When sim resumes from pause (UNKNOWN -> running), re-detect the current phase
        # MUST use force=True to bypass hysteresis check
        if self._current_phase == FlightPhase.UNKNOWN:
            vs = self._smooth_vs(state.vertical_speed)
            if state.on_ground:
                # Ground state detection with has_flown awareness
                if state.ground_speed < p.taxi_min_speed:
                    if state.has_flown and state.parking_brake and not state.engine_running:
                        # After flight, stopped, parked, engine off = PARKED (post-flight)
                        new_phase = FlightPhase.PARKED
                    elif not state.engine_running:
                        # Engine off, hasn't flown = PREFLIGHT
                        new_phase = FlightPhase.PREFLIGHT
                    elif state.parking_brake:
                        # Engine running, parking brake = PARKED
                        new_phase = FlightPhase.PARKED
                    elif state.has_flown:
                        # After flight, stopped, engine running = TAXI_IN
                        new_phase = FlightPhase.TAXI_IN
                    else:
                        # Before flight, stopped, engine running = ENGINE_START
                        new_phase = FlightPhase.ENGINE_START
                else:
                    # Moving on ground
                    if state.has_flown:
                        new_phase = FlightPhase.TAXI_IN
                    else:
                        new_phase = FlightPhase.TAXI_OUT
            else:
                # In air - determine phase from flight parameters
                if state.altitude_agl < p.initial_climb_alt and vs > 200:
                    new_phase = FlightPhase.INITIAL_CLIMB
                elif vs > p.climb_vs_threshold:
                    new_phase = FlightPhase.CLIMB
                elif vs < p.descent_vs_threshold:
                    if state.altitude_agl < p.approach_alt:
                        new_phase = FlightPhase.APPROACH
                    else:
                        new_phase = FlightPhase.DESCENT
                else:
                    new_phase = FlightPhase.CRUISE

            logger.info(f"Sim resumed - phase: {new_phase.value} (ground={state.on_ground}, agl={state.altitude_agl:.0f}ft, vs={vs:.0f}, has_flown={state.has_flown})")
            self._set_phase(new_phase, state, force=True)
            return self._current_phase

        # ========== SMOOTH VERTICAL SPEED ==========
        vs = self._smooth_vs(state.vertical_speed)

        # ========== LOCATION CONTEXT ==========
        near_departure = self._distance_to(state.latitude, state.longitude,
                                           self._departure_lat, self._departure_lon) < 8000
        near_arrival = self._distance_to(state.latitude, state.longitude,
                                         self._arrival_lat, self._arrival_lon) < 8000
        aligned_departure = self._heading_aligned(state.heading, self._departure_heading)
        aligned_arrival = self._heading_aligned(state.heading, self._arrival_heading)

        # ========== FIRST UPDATE - INITIAL STATE ==========
        if self._first_update:
            self._first_update = False
            self._was_on_ground = state.on_ground
            self._phase_start_time = datetime.now()

            if state.on_ground:
                if state.ground_speed < p.taxi_min_speed:
                    if not state.engine_running:
                        self._current_phase = FlightPhase.PREFLIGHT
                    elif state.parking_brake:
                        self._current_phase = FlightPhase.PARKED
                    else:
                        self._current_phase = FlightPhase.ENGINE_START
                else:
                    # Moving on ground - assume taxi out if we haven't flown yet
                    self._current_phase = FlightPhase.TAXI_OUT
            else:
                # Starting in air
                self._flight_started = True
                self._was_airborne = True
                if state.altitude_agl < p.initial_climb_alt:
                    self._current_phase = FlightPhase.INITIAL_CLIMB
                elif vs > p.climb_vs_threshold:
                    self._current_phase = FlightPhase.CLIMB
                elif vs < p.descent_vs_threshold:
                    self._current_phase = FlightPhase.DESCENT if state.altitude_agl > p.approach_alt else FlightPhase.APPROACH
                else:
                    self._current_phase = FlightPhase.CRUISE

            logger.info(f"Initial phase: {self._current_phase.value} (ground={state.on_ground}, agl={state.altitude_agl:.0f}ft)")
            return self._current_phase

        # ========== GROUND PHASES ==========
        if state.on_ground:

            # Just touched down?
            if self._was_airborne and not self._was_on_ground:
                self._has_landed = True
                self._set_phase(FlightPhase.LANDING_ROLL, state, force=True)
                logger.info(f"Touchdown detected (spoilers={state.spoilers_percent:.0f}%)")

            # LANDING_ROLL -> TAXI_IN
            elif self._current_phase == FlightPhase.LANDING_ROLL:
                # Exit when slow OR spoilers retracted (per Universal Announcer logic)
                if state.ground_speed < p.taxi_max_speed:
                    self._set_phase(FlightPhase.TAXI_IN, state)
                elif state.spoilers_percent < 10 and state.ground_speed < 50:
                    # Spoilers retracted = exited runway
                    self._set_phase(FlightPhase.TAXI_IN, state)
                    logger.info("Spoilers retracted - taxi in")

            # TAXI_IN -> SHUTDOWN/PARKED
            elif self._current_phase == FlightPhase.TAXI_IN:
                if state.ground_speed < p.taxi_min_speed:
                    # Use in_parking_state if available, otherwise use parking_brake
                    if state.in_parking_state:
                        if state.engine_running:
                            self._set_phase(FlightPhase.SHUTDOWN, state)
                        else:
                            self._set_phase(FlightPhase.PARKED, state)
                    elif state.parking_brake:
                        self._set_phase(FlightPhase.SHUTDOWN, state)
                    elif not state.engine_running:
                        self._set_phase(FlightPhase.PARKED, state)

            # SHUTDOWN -> PARKED or back to TAXI_OUT (for new takeoff)
            elif self._current_phase == FlightPhase.SHUTDOWN:
                if not state.engine_running:
                    self._set_phase(FlightPhase.PARKED, state)
                # If engine running and beacon ON = ready for new flight
                elif state.engine_running and state.light_beacon and not state.parking_brake:
                    self._set_phase(FlightPhase.TAXI_OUT, state)
                    self._flight_started = False  # Reset for new flight
                    self._has_landed = False
                    logger.info("Beacon ON, parking brake released - ready for new flight")
                # If engine running and moving -> taxiing
                elif state.engine_running and state.ground_speed > p.taxi_min_speed:
                    self._set_phase(FlightPhase.TAXI_OUT, state)
                    self._flight_started = False
                    self._has_landed = False
                    logger.info("New flight started from shutdown")
                elif state.engine_running and not state.parking_brake:
                    self._set_phase(FlightPhase.TAXI_OUT, state)
                    self._flight_started = False
                    self._has_landed = False
                    logger.info("Parking brake released - ready for new flight")

            # PREFLIGHT / PARKED -> ENGINE_START
            elif self._current_phase in [FlightPhase.PREFLIGHT, FlightPhase.PARKED, FlightPhase.UNKNOWN]:
                if state.engine_running:
                    if state.ground_speed < p.taxi_min_speed:
                        self._set_phase(FlightPhase.ENGINE_START, state)
                    else:
                        self._set_phase(FlightPhase.TAXI_OUT, state)
                elif not state.engine_running and self._current_phase == FlightPhase.UNKNOWN:
                    # Use in_parking_state or beacon to determine PREFLIGHT vs PARKED
                    if state.in_parking_state or (not state.light_beacon and state.parking_brake):
                        self._set_phase(FlightPhase.PARKED, state)
                    else:
                        self._set_phase(FlightPhase.PREFLIGHT, state)

            # ENGINE_START -> TAXI_OUT or HOLDING
            elif self._current_phase == FlightPhase.ENGINE_START:
                # If near departure, aligned and stopped -> HOLDING (ready for takeoff)
                if near_departure and aligned_departure and state.ground_speed < p.taxi_min_speed:
                    self._set_phase(FlightPhase.HOLDING, state)
                    logger.info("Near runway aligned - ready for takeoff")
                # If high throttle -> immediate takeoff roll
                elif state.throttle_percent > 80:
                    self._set_phase(FlightPhase.TAKEOFF_ROLL, state, force=True)
                    self._flight_started = True
                    logger.info(f"Takeoff from engine start (high throttle): THR={state.throttle_percent:.0f}%")
                # If beacon ON and parking brake released -> ready to taxi
                elif state.light_beacon and not state.parking_brake:
                    self._set_phase(FlightPhase.TAXI_OUT, state)
                    logger.info("Beacon ON, parking brake released - taxi mode")
                # If parking brake released and not moving -> ready to taxi
                elif not state.parking_brake and state.ground_speed < p.taxi_min_speed:
                    self._set_phase(FlightPhase.TAXI_OUT, state)
                    logger.info("Parking brake released - taxi mode")
                # If moving -> taxiing
                elif state.ground_speed > p.taxi_min_speed:
                    self._set_phase(FlightPhase.TAXI_OUT, state)

            # TAXI_OUT -> HOLDING or TAKEOFF_ROLL
            elif self._current_phase == FlightPhase.TAXI_OUT:
                # Detect holding short (stopped near departure, aligned)
                if aligned_departure and state.ground_speed < p.taxi_min_speed and near_departure:
                    self._set_phase(FlightPhase.HOLDING, state)
                # Detect takeoff roll using THROTTLE + SPEED
                # Takeoff roll when: high throttle (>80%) OR high speed
                elif state.throttle_percent > 80 and state.ground_speed > p.taxi_min_speed:
                    self._set_phase(FlightPhase.TAKEOFF_ROLL, state, force=True)
                    self._flight_started = True
                    logger.info(f"Takeoff roll (high throttle): THR={state.throttle_percent:.0f}%, GS={state.ground_speed:.0f}")
                elif state.airspeed > 40 or state.ground_speed > p.takeoff_roll_speed:
                    self._set_phase(FlightPhase.TAKEOFF_ROLL, state, force=True)
                    self._flight_started = True
                    logger.info(f"Takeoff roll (high speed): IAS={state.airspeed:.0f}, GS={state.ground_speed:.0f}")
                # Also detect if accelerating on ground (airspeed > taxi speeds)
                elif state.airspeed > p.taxi_max_speed and state.ground_speed > p.taxi_max_speed:
                    self._set_phase(FlightPhase.TAKEOFF_ROLL, state, force=True)
                    self._flight_started = True
                    logger.info(f"Takeoff roll (acceleration): IAS={state.airspeed:.0f}")

            # HOLDING -> TAKEOFF_ROLL
            elif self._current_phase == FlightPhase.HOLDING:
                # Detect takeoff roll from holding position using throttle or speed
                if state.throttle_percent > 80:
                    self._set_phase(FlightPhase.TAKEOFF_ROLL, state, force=True)
                    self._flight_started = True
                    logger.info(f"Takeoff roll from holding (throttle): THR={state.throttle_percent:.0f}%")
                elif state.airspeed > 30 or state.ground_speed > p.taxi_max_speed:
                    self._set_phase(FlightPhase.TAKEOFF_ROLL, state, force=True)
                    self._flight_started = True
                    logger.info(f"Takeoff roll from holding (speed): IAS={state.airspeed:.0f}")

            # TAKEOFF_ROLL -> ROTATION
            elif self._current_phase == FlightPhase.TAKEOFF_ROLL:
                # Rotation when pitch up and airspeed near Vr
                if state.pitch > p.rotation_pitch and state.airspeed > (p.rotation_speed * 0.9):
                    self._set_phase(FlightPhase.ROTATION, state, force=True)
                    logger.info(f"Rotation: pitch={state.pitch:.1f}, IAS={state.airspeed:.0f}")

            self._was_on_ground = True
            self._was_airborne = False

        # ========== AIRBORNE PHASES ==========
        else:
            self._was_airborne = True

            # Just lifted off?
            if self._was_on_ground:
                self._flight_started = True
                self._set_phase(FlightPhase.INITIAL_CLIMB, state, force=True)
                logger.info("Liftoff detected")

            # ROTATION -> INITIAL_CLIMB
            elif self._current_phase == FlightPhase.ROTATION:
                self._set_phase(FlightPhase.INITIAL_CLIMB, state, force=True)

            # INITIAL_CLIMB -> CLIMB
            elif self._current_phase == FlightPhase.INITIAL_CLIMB:
                if state.altitude_agl > p.initial_climb_alt:
                    self._set_phase(FlightPhase.CLIMB, state)

            # CLIMB -> CRUISE or DESCENT
            elif self._current_phase == FlightPhase.CLIMB:
                if abs(vs) < p.level_vs_tolerance:
                    self._set_phase(FlightPhase.CRUISE, state)
                elif vs < p.descent_vs_threshold:
                    self._set_phase(FlightPhase.DESCENT, state)

            # CRUISE -> CLIMB or DESCENT
            elif self._current_phase == FlightPhase.CRUISE:
                if vs > p.climb_vs_threshold:
                    self._set_phase(FlightPhase.CLIMB, state)
                elif vs < p.descent_vs_threshold:
                    self._set_phase(FlightPhase.DESCENT, state)

            # DESCENT -> CRUISE or APPROACH
            elif self._current_phase == FlightPhase.DESCENT:
                if abs(vs) < p.level_vs_tolerance:
                    self._set_phase(FlightPhase.CRUISE, state)
                # Approach when: low altitude + gear down, OR landing lights ON + descending
                elif state.altitude_agl < p.approach_alt and state.gear_down:
                    self._set_phase(FlightPhase.APPROACH, state)
                    logger.info(f"Approach (gear down): AGL={state.altitude_agl:.0f}ft")
                elif state.light_landing and state.altitude_agl < 10000 and vs < -300:
                    # Landing lights ON below 10000ft = likely approach
                    self._set_phase(FlightPhase.APPROACH, state)
                    logger.info(f"Approach (landing lights): AGL={state.altitude_agl:.0f}ft")

            # APPROACH -> SHORT_FINAL or CLIMB (go-around)
            elif self._current_phase == FlightPhase.APPROACH:
                if state.altitude_agl < p.short_final_alt:
                    self._set_phase(FlightPhase.SHORT_FINAL, state)
                elif vs > p.climb_vs_threshold:
                    self._set_phase(FlightPhase.CLIMB, state)  # Go-around

            # SHORT_FINAL -> FLARE or CLIMB (go-around)
            elif self._current_phase == FlightPhase.SHORT_FINAL:
                if state.altitude_agl < p.flare_alt:
                    self._set_phase(FlightPhase.FLARE, state, force=True)
                elif vs > p.climb_vs_threshold:
                    self._set_phase(FlightPhase.CLIMB, state)  # Go-around

            # FLARE -> stays until touchdown or go-around
            elif self._current_phase == FlightPhase.FLARE:
                if vs > p.climb_vs_threshold:
                    self._set_phase(FlightPhase.CLIMB, state)  # Go-around

            self._was_on_ground = False

        return self._current_phase

    def reset(self) -> None:
        """Reset detector for new flight"""
        self._current_phase = FlightPhase.UNKNOWN
        self._previous_phase = FlightPhase.UNKNOWN
        self._phase_start_time = None
        self._transitions.clear()
        self._flight_started = False
        self._has_landed = False
        self._was_on_ground = True
        self._was_airborne = False
        self._first_update = True
        self._vs_buffer.clear()
        logger.info("Phase detector reset")

    def get_summary(self) -> Dict:
        """Get phase detection summary"""
        return {
            'current_phase': self._current_phase.value,
            'previous_phase': self._previous_phase.value,
            'flight_started': self._flight_started,
            'has_landed': self._has_landed,
            'phase_duration_s': self._phase_duration(),
            'transitions_count': len(self._transitions),
            'aircraft_profile': self._profile.name
        }


# Global instance
_phase_detector: Optional[FlightPhaseDetector] = None

def get_phase_detector() -> FlightPhaseDetector:
    """Get or create global phase detector"""
    global _phase_detector
    if _phase_detector is None:
        _phase_detector = FlightPhaseDetector()
    return _phase_detector
