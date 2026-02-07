"""
Adaptive SimConnect Polling for V2 - OPTIMIZED VERSION
Background thread polling with thread-safe cache
NO BLOCKING CALLS from the GUI thread
"""

import logging
import time
import math
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from threading import Thread, Event, Lock, RLock
from copy import copy

logger = logging.getLogger("MissionGenerator.SimConnect")

# Try to import SimConnect
try:
    from SimConnect import SimConnect, AircraftRequests
    SIMCONNECT_AVAILABLE = True
except ImportError:
    SIMCONNECT_AVAILABLE = False
    logger.warning("SimConnect not available")


class FlightPhase(Enum):
    """Flight phases for adaptive polling"""
    PARKED = "parked"
    TAXI = "taxi"
    TAKEOFF = "takeoff"
    CLIMB = "climb"
    CRUISE = "cruise"
    DESCENT = "descent"
    APPROACH = "approach"
    LANDING = "landing"
    UNKNOWN = "unknown"


@dataclass
class PollRateConfig:
    """Polling rate configuration per flight phase"""
    poll_interval_ms: int
    critical_vars_ms: int
    secondary_vars_ms: int


# Polling rates by flight phase (milliseconds)
PHASE_POLL_RATES: Dict[FlightPhase, PollRateConfig] = {
    FlightPhase.PARKED: PollRateConfig(2000, 1000, 5000),
    FlightPhase.TAXI: PollRateConfig(500, 300, 2000),
    FlightPhase.TAKEOFF: PollRateConfig(100, 50, 300),
    FlightPhase.CLIMB: PollRateConfig(500, 300, 1500),
    FlightPhase.CRUISE: PollRateConfig(1000, 500, 3000),
    FlightPhase.DESCENT: PollRateConfig(500, 300, 1500),
    FlightPhase.APPROACH: PollRateConfig(200, 100, 500),
    FlightPhase.LANDING: PollRateConfig(50, 30, 150),
    FlightPhase.UNKNOWN: PollRateConfig(1000, 500, 2000)
}

# ALL variables needed by main_v2.py - will be polled in background
ALL_FLIGHT_VARIABLES = [
    # Critical - position and movement
    "PLANE_ALTITUDE",
    "PLANE_ALT_ABOVE_GROUND",
    "AIRSPEED_INDICATED",
    "AIRSPEED_TRUE",
    "VERTICAL_SPEED",
    "SIM_ON_GROUND",
    "PLANE_LATITUDE",
    "PLANE_LONGITUDE",
    "PLANE_HEADING_DEGREES_TRUE",
    "GROUND_VELOCITY",

    # Aircraft state
    "PLANE_BANK_DEGREES",
    "PLANE_PITCH_DEGREES",
    "BRAKE_PARKING_POSITION",
    "GENERAL_ENG_COMBUSTION:1",
    "GEAR_HANDLE_POSITION",
    "FLAPS_HANDLE_PERCENT",
    "GENERAL_ENG_THROTTLE_LEVER_POSITION:1",
    "SPOILERS_HANDLE_POSITION",

    # Lights
    "LIGHT_BEACON",
    "LIGHT_LANDING",
    "LIGHT_TAXI",

    # Simulation state
    "PLANE_IN_PARKING_STATE",
    "SIMULATION_RATE",
    "ABSOLUTE_TIME",

    # Warnings
    "STALL_WARNING",
    "OVERSPEED_WARNING",

    # Performance metrics
    "G_FORCE",
    "PLANE_TOUCHDOWN_NORMAL_VELOCITY",
    "GENERAL_ENG_PCT_MAX_RPM:1",
    "GENERAL_ENG_OIL_TEMPERATURE:1",

    # Fuel
    "ENG_FUEL_FLOW_GPH:1",
    "ENG_FUEL_FLOW_GPH:2",
    "FUEL_TOTAL_QUANTITY_WEIGHT",
    "FUEL_WEIGHT_PER_GALLON",
    "FUEL_TOTAL_CAPACITY",
    "FUEL_TOTAL_QUANTITY",

    # Weather
    "DENSITY_ALTITUDE",
    "STRUCTURAL_ICE_PCT",
    "PITOT_ICE_PCT",

    # Autopilot
    "AUTOPILOT_MASTER",
    "AUTOPILOT_APPROACH_HOLD",
    "AUTOPILOT_GLIDESLOPE_ACTIVE",
    "AUTOPILOT_ALTITUDE_LOCK_VAR",

    # Transponder/Avionics
    "TRANSPONDER_STATE",
    "AVIONICS_MASTER_SWITCH",
    "ELECTRICAL_MASTER_BATTERY",
    "CANOPY_OPEN",
    "GENERAL_ENG_MIXTURE_LEVER_POSITION:1",

    # === NAVIGATION DATA ===
    # GPS/Flight Plan
    "GPS_WP_DISTANCE",
    "GPS_WP_BEARING",
    "GPS_WP_ETA",
    "GPS_ETA",
    "GPS_ETE",
    "GPS_FLIGHT_PLAN_WP_COUNT",
    "GPS_FLIGHT_PLAN_WP_INDEX",
    "GPS_FLIGHTPLAN_TOTAL_DISTANCE",
    "GPS_GROUND_SPEED",

    # Autopilot selections
    "AUTOPILOT_HEADING_LOCK",
    "AUTOPILOT_HEADING_LOCK_DIR",
    "AUTOPILOT_ALTITUDE_LOCK",
    "AUTOPILOT_ALTITUDE_LOCK_VAR",
    "AUTOPILOT_AIRSPEED_HOLD",
    "AUTOPILOT_AIRSPEED_HOLD_VAR",
    "AUTOPILOT_VERTICAL_HOLD",
    "AUTOPILOT_VERTICAL_HOLD_VAR",
    "AUTOPILOT_NAV1_LOCK",
    "AUTOPILOT_FLIGHT_DIRECTOR_ACTIVE",

    # NAV radios
    "NAV_ACTIVE_FREQUENCY:1",
    "NAV_DME:1",
    "NAV_OBS:1",
    "NAV_CDI:1",
    "NAV_HAS_LOCALIZER:1",
    "NAV_HAS_GLIDE_SLOPE:1",

    # COM radios
    "COM_ACTIVE_FREQUENCY:1",
    "COM_ACTIVE_FREQUENCY:2",
]

# Payload stations - polled less frequently
PAYLOAD_VARIABLES = [f"PAYLOAD_STATION_WEIGHT:{i}" for i in range(1, 13)]

# Static variables - NOW polled with main variables for reliability
# These don't change often but we need them immediately at startup
STATIC_VARIABLES = [
    "TITLE",
    "ENGINE_TYPE",
    "NUMBER_OF_ENGINES",
]

# Add static variables to main list so they're available immediately
ALL_FLIGHT_VARIABLES.extend(STATIC_VARIABLES)


@dataclass
class SimDataSnapshot:
    """
    Thread-safe snapshot of all SimConnect data.
    This is what the GUI thread reads - NO BLOCKING.
    """
    # Core flight data
    altitude: float = 0.0
    altitude_agl: float = 0.0
    airspeed: float = 0.0
    airspeed_true: float = 0.0
    vertical_speed: float = 0.0
    on_ground: bool = True
    latitude: float = 0.0
    longitude: float = 0.0
    heading: float = 0.0
    ground_speed: float = 0.0

    # Aircraft state
    bank_angle: float = 0.0
    pitch: float = 0.0
    parking_brake: bool = False
    engine_running: bool = False
    gear_down: bool = True
    flaps_percent: float = 0.0
    throttle_percent: float = 0.0
    spoilers_percent: float = 0.0

    # Lights
    light_beacon: bool = False
    light_landing: bool = False
    light_taxi: bool = False

    # Simulation
    in_parking_state: bool = False
    simulation_rate: float = 1.0
    absolute_time: float = 0.0
    sim_running: bool = False

    # Warnings
    stall_warning: bool = False
    overspeed_warning: bool = False

    # Performance
    g_force: float = 1.0
    touchdown_velocity: float = 0.0
    engine_rpm_percent: float = 0.0
    engine_oil_temp: float = 0.0

    # Fuel
    fuel_flow_gph_1: float = 0.0
    fuel_flow_gph_2: float = 0.0
    fuel_total_weight: float = 0.0
    fuel_weight_per_gal: float = 6.0
    fuel_capacity_gal: float = 0.0
    fuel_quantity_gal: float = 0.0

    # Weather
    density_altitude: float = 0.0
    structural_ice_pct: float = 0.0
    pitot_ice_pct: float = 0.0

    # Autopilot
    autopilot_master: bool = False
    autopilot_approach: bool = False
    autopilot_glideslope: bool = False
    autopilot_altitude: float = 0.0

    # Avionics
    transponder_state: int = 0
    avionics_master: bool = False
    battery_master: bool = False
    canopy_open: bool = False
    mixture_percent: float = 0.0

    # Payload
    payload_weights: List[float] = field(default_factory=lambda: [0.0] * 12)
    estimated_passengers: int = 0

    # Aircraft info (static)
    title: str = "Unknown"
    engine_type: int = 0
    num_engines: int = 1

    # === NAVIGATION DATA ===
    # GPS/Flight Plan
    gps_wp_distance_nm: float = 0.0      # Distance to next waypoint (nm)
    gps_wp_bearing: float = 0.0          # Bearing to waypoint (degrees)
    gps_wp_eta_seconds: float = 0.0      # ETA to waypoint (seconds)
    gps_dest_eta_seconds: float = 0.0    # ETA to destination (seconds)
    gps_dest_ete_seconds: float = 0.0    # Time remaining to destination (seconds)
    gps_wp_count: int = 0                # Number of waypoints in flight plan
    gps_wp_index: int = 0                # Current waypoint index
    gps_total_distance_nm: float = 0.0   # Total flight plan distance (nm)

    # Autopilot selections
    ap_hdg_lock: bool = False
    ap_hdg_selected: float = 0.0         # Selected heading (degrees)
    ap_alt_lock: bool = False
    ap_alt_selected: float = 0.0         # Selected altitude (feet)
    ap_spd_lock: bool = False
    ap_spd_selected: float = 0.0         # Selected speed (knots)
    ap_vs_lock: bool = False
    ap_vs_selected: float = 0.0          # Selected VS (fpm)
    ap_nav_lock: bool = False
    ap_fd_active: bool = False

    # NAV radio
    nav1_frequency: float = 0.0          # NAV1 frequency (MHz)
    nav1_dme_nm: float = 0.0             # DME distance (nm)
    nav1_obs: float = 0.0                # OBS setting (degrees)
    nav1_cdi: float = 0.0                # CDI deviation
    nav1_has_loc: bool = False
    nav1_has_gs: bool = False

    # COM radio
    com1_frequency: float = 0.0          # COM1 frequency (MHz)
    com2_frequency: float = 0.0          # COM2 frequency (MHz)

    # Timestamp
    last_update: float = 0.0

    def get_effective_airspeed(self) -> float:
        """Get airspeed with fallback to true airspeed"""
        if self.airspeed > 0:
            return self.airspeed
        return self.airspeed_true


class AdaptiveSimConnect:
    """
    Optimized SimConnect wrapper with background polling.

    KEY DESIGN:
    - All SimConnect calls happen in a BACKGROUND THREAD
    - GUI thread reads from a thread-safe SNAPSHOT (never blocks)
    - Polling rate adapts to flight phase
    """

    def __init__(self):
        self._sim: Optional[SimConnect] = None
        self._requests: Optional[AircraftRequests] = None
        self._connected = False
        self._current_phase = FlightPhase.UNKNOWN

        # Thread-safe snapshot - this is what GUI reads
        self._snapshot = SimDataSnapshot()
        self._snapshot_lock = RLock()

        # Raw cache for individual variable access
        self._raw_cache: Dict[str, Any] = {}
        self._raw_cache_lock = Lock()

        # Background polling
        self._polling = False
        self._stop_event = Event()
        self._poll_thread: Optional[Thread] = None

        # Callbacks
        self._data_callbacks: List[Callable[[SimDataSnapshot], None]] = []

        # Stats
        self._poll_count = 0
        self._last_poll_time = 0.0
        self._avg_poll_duration_ms = 0.0

        # Sim running detection
        self._last_absolute_time = 0.0
        self._last_altitude = 0.0
        self._last_vs = 0.0
        self._last_ias = 0.0

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def polling(self) -> bool:
        return self._polling

    @property
    def current_phase(self) -> FlightPhase:
        return self._current_phase

    @property
    def poll_rate(self) -> PollRateConfig:
        return PHASE_POLL_RATES[self._current_phase]

    def get_snapshot(self) -> SimDataSnapshot:
        """
        Get current data snapshot - THREAD SAFE, NON-BLOCKING.
        This is the MAIN method the GUI should use.
        """
        with self._snapshot_lock:
            # Return a copy to prevent race conditions
            return copy(self._snapshot)

    def connect(self) -> bool:
        """Connect to SimConnect"""
        if not SIMCONNECT_AVAILABLE:
            logger.error("SimConnect library not available")
            return False

        try:
            self._sim = SimConnect()
            # _time=0 means no automatic polling by AircraftRequests
            self._requests = AircraftRequests(self._sim, _time=0)
            self._connected = True
            logger.info("SimConnect connected")
            return True
        except Exception as e:
            logger.error(f"SimConnect connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from SimConnect"""
        self.stop_polling()

        if self._sim:
            try:
                self._sim.exit()
            except:
                pass

        self._sim = None
        self._requests = None
        self._connected = False
        logger.info("SimConnect disconnected")

    def start_polling(self) -> None:
        """Start background polling thread"""
        if self._polling:
            return

        if not self._connected:
            if not self.connect():
                return

        self._polling = True
        self._stop_event.clear()

        self._poll_thread = Thread(target=self._poll_loop, daemon=True, name="SimConnectPoller")
        self._poll_thread.start()
        logger.info("SimConnect background polling started")

    def stop_polling(self) -> None:
        """Stop background polling"""
        if not self._polling:
            return

        self._stop_event.set()
        if self._poll_thread:
            self._poll_thread.join(timeout=2.0)

        self._polling = False
        logger.info("SimConnect polling stopped")

    def _poll_loop(self) -> None:
        """
        Background polling loop - runs in separate thread.
        ALL SimConnect calls happen here.
        """
        last_secondary_poll = 0.0
        last_payload_poll = 0.0
        last_static_poll = 0.0

        logger.info("Poll loop started")

        while not self._stop_event.is_set():
            try:
                poll_start = time.time()
                now = poll_start
                poll_rate = self.poll_rate

                # ============================================
                # POLL ALL FLIGHT VARIABLES (fast)
                # ============================================
                raw_data = self._fetch_variables(ALL_FLIGHT_VARIABLES)

                # ============================================
                # POLL PAYLOAD (less frequently)
                # ============================================
                if now - last_payload_poll > 5.0:  # Every 5 seconds
                    payload_data = self._fetch_variables(PAYLOAD_VARIABLES)
                    raw_data.update(payload_data)
                    last_payload_poll = now

                # ============================================
                # POLL STATIC (rarely)
                # ============================================
                if now - last_static_poll > 30.0:  # Every 30 seconds
                    static_data = self._fetch_variables(STATIC_VARIABLES)
                    raw_data.update(static_data)
                    last_static_poll = now

                # ============================================
                # UPDATE SNAPSHOT (thread-safe)
                # ============================================
                self._update_snapshot(raw_data)

                # ============================================
                # DETECT FLIGHT PHASE
                # ============================================
                self._detect_phase()

                # ============================================
                # NOTIFY CALLBACKS
                # ============================================
                snapshot = self.get_snapshot()
                for callback in self._data_callbacks:
                    try:
                        callback(snapshot)
                    except Exception as e:
                        logger.error(f"Data callback error: {e}")

                # Stats
                poll_duration = (time.time() - poll_start) * 1000
                self._avg_poll_duration_ms = (self._avg_poll_duration_ms * 0.9) + (poll_duration * 0.1)
                self._poll_count += 1
                self._last_poll_time = now

                # Sleep until next poll
                sleep_ms = max(10, poll_rate.poll_interval_ms - poll_duration)
                self._stop_event.wait(sleep_ms / 1000.0)

            except Exception as e:
                logger.error(f"Poll loop error: {e}")
                self._stop_event.wait(1.0)

        logger.info("Poll loop ended")

    def _fetch_variables(self, variables: List[str]) -> Dict[str, Any]:
        """
        Fetch multiple variables from SimConnect.
        Called ONLY from background thread.
        """
        if not self._requests:
            return {}

        result = {}
        for var in variables:
            try:
                value = self._requests.get(var)
                result[var] = value

                # Also update raw cache
                with self._raw_cache_lock:
                    self._raw_cache[var] = value
            except Exception as e:
                # Don't spam logs for missing variables
                pass

        return result

    def _update_snapshot(self, raw_data: Dict[str, Any]) -> None:
        """
        Update the thread-safe snapshot from raw data.
        Includes unit conversions and derived values.
        """
        with self._snapshot_lock:
            snap = self._snapshot

            # Helper to get value with default
            def get(key: str, default: Any = None) -> Any:
                return raw_data.get(key, default)

            # Core flight data
            snap.altitude = get("PLANE_ALTITUDE") or 0.0
            snap.altitude_agl = get("PLANE_ALT_ABOVE_GROUND") or 0.0
            snap.airspeed = get("AIRSPEED_INDICATED") or 0.0
            snap.airspeed_true = get("AIRSPEED_TRUE") or 0.0
            snap.on_ground = bool(get("SIM_ON_GROUND"))
            snap.latitude = get("PLANE_LATITUDE") or 0.0
            snap.longitude = get("PLANE_LONGITUDE") or 0.0

            # Vertical speed - convert from ft/s to ft/min if needed
            vs = get("VERTICAL_SPEED") or 0.0
            if abs(vs) < 200:  # Likely ft/s
                vs = vs * 60
            snap.vertical_speed = vs

            # Heading - convert from radians if needed
            hdg = get("PLANE_HEADING_DEGREES_TRUE") or 0.0
            if abs(hdg) <= math.pi * 2:
                hdg = math.degrees(hdg) % 360
            snap.heading = hdg

            # Ground speed - convert from ft/s to knots
            gs = get("GROUND_VELOCITY") or 0.0
            if gs > 0 and gs < 1000:  # Likely ft/s
                gs = gs * 0.592484
            snap.ground_speed = gs

            # Bank angle - convert from radians if needed
            bank = get("PLANE_BANK_DEGREES") or 0.0
            if abs(bank) <= math.pi:
                bank = math.degrees(bank)
            snap.bank_angle = bank

            # Pitch - convert from radians if needed
            pitch = get("PLANE_PITCH_DEGREES") or 0.0
            if abs(pitch) < 1.5:
                pitch = math.degrees(pitch)
            snap.pitch = pitch

            # Aircraft state
            snap.parking_brake = bool(get("BRAKE_PARKING_POSITION"))
            snap.engine_running = bool(get("GENERAL_ENG_COMBUSTION:1"))
            snap.gear_down = bool(get("GEAR_HANDLE_POSITION")) if get("GEAR_HANDLE_POSITION") is not None else True
            snap.flaps_percent = get("FLAPS_HANDLE_PERCENT") or 0.0
            snap.throttle_percent = get("GENERAL_ENG_THROTTLE_LEVER_POSITION:1") or 0.0
            snap.spoilers_percent = get("SPOILERS_HANDLE_POSITION") or 0.0

            # Lights
            snap.light_beacon = bool(get("LIGHT_BEACON"))
            snap.light_landing = bool(get("LIGHT_LANDING"))
            snap.light_taxi = bool(get("LIGHT_TAXI"))

            # Simulation state
            snap.in_parking_state = bool(get("PLANE_IN_PARKING_STATE"))
            snap.simulation_rate = get("SIMULATION_RATE") or 1.0
            snap.absolute_time = get("ABSOLUTE_TIME") or 0.0

            # Detect if sim is running (not paused/in menu)
            snap.sim_running = self._detect_sim_running(snap)

            # Warnings
            snap.stall_warning = bool(get("STALL_WARNING"))
            snap.overspeed_warning = bool(get("OVERSPEED_WARNING"))

            # Performance
            snap.g_force = get("G_FORCE") or 1.0
            snap.touchdown_velocity = get("PLANE_TOUCHDOWN_NORMAL_VELOCITY") or 0.0
            snap.engine_rpm_percent = get("GENERAL_ENG_PCT_MAX_RPM:1") or 0.0
            snap.engine_oil_temp = get("GENERAL_ENG_OIL_TEMPERATURE:1") or 0.0

            # Fuel
            snap.fuel_flow_gph_1 = get("ENG_FUEL_FLOW_GPH:1") or 0.0
            snap.fuel_flow_gph_2 = get("ENG_FUEL_FLOW_GPH:2") or 0.0
            snap.fuel_total_weight = get("FUEL_TOTAL_QUANTITY_WEIGHT") or 0.0
            snap.fuel_weight_per_gal = get("FUEL_WEIGHT_PER_GALLON") or 6.0
            snap.fuel_capacity_gal = get("FUEL_TOTAL_CAPACITY") or 0.0
            snap.fuel_quantity_gal = get("FUEL_TOTAL_QUANTITY") or 0.0

            # Weather
            snap.density_altitude = get("DENSITY_ALTITUDE") or 0.0
            snap.structural_ice_pct = get("STRUCTURAL_ICE_PCT") or 0.0
            snap.pitot_ice_pct = get("PITOT_ICE_PCT") or 0.0

            # Autopilot
            snap.autopilot_master = bool(get("AUTOPILOT_MASTER"))
            snap.autopilot_approach = bool(get("AUTOPILOT_APPROACH_HOLD"))
            snap.autopilot_glideslope = bool(get("AUTOPILOT_GLIDESLOPE_ACTIVE"))
            snap.autopilot_altitude = get("AUTOPILOT_ALTITUDE_LOCK_VAR") or 0.0

            # Avionics
            snap.transponder_state = int(get("TRANSPONDER_STATE") or 0)
            snap.avionics_master = bool(get("AVIONICS_MASTER_SWITCH"))
            snap.battery_master = bool(get("ELECTRICAL_MASTER_BATTERY"))
            snap.canopy_open = bool(get("CANOPY_OPEN"))
            snap.mixture_percent = get("GENERAL_ENG_MIXTURE_LEVER_POSITION:1") or 0.0

            # Payload stations
            payload = []
            occupied_seats = 0
            for i in range(1, 13):
                weight = get(f"PAYLOAD_STATION_WEIGHT:{i}") or 0.0
                payload.append(weight)
                if weight > 50:
                    occupied_seats += 1
            snap.payload_weights = payload

            # Estimate passengers (minus crew in stations 1 & 2)
            crew_count = 0
            if payload[0] > 50:
                crew_count += 1
            if payload[1] > 50:
                crew_count += 1
            snap.estimated_passengers = max(0, occupied_seats - crew_count)

            # Static data
            title = get("TITLE")
            if title:
                if isinstance(title, bytes):
                    snap.title = title.decode('utf-8', errors='ignore').strip('\x00')
                else:
                    snap.title = str(title).strip('\x00')
            snap.engine_type = int(get("ENGINE_TYPE") or 0)
            snap.num_engines = int(get("NUMBER_OF_ENGINES") or 1)

            # === NAVIGATION DATA ===
            # GPS/Flight Plan
            gps_wp_dist_m = get("GPS_WP_DISTANCE") or 0.0
            snap.gps_wp_distance_nm = gps_wp_dist_m / 1852.0  # meters to nm

            gps_wp_brg = get("GPS_WP_BEARING") or 0.0
            snap.gps_wp_bearing = math.degrees(gps_wp_brg) % 360 if abs(gps_wp_brg) < 10 else gps_wp_brg

            snap.gps_wp_eta_seconds = get("GPS_WP_ETA") or 0.0
            snap.gps_dest_eta_seconds = get("GPS_ETA") or 0.0
            snap.gps_dest_ete_seconds = get("GPS_ETE") or 0.0
            snap.gps_wp_count = int(get("GPS_FLIGHT_PLAN_WP_COUNT") or 0)
            snap.gps_wp_index = int(get("GPS_FLIGHT_PLAN_WP_INDEX") or 0)

            gps_total_m = get("GPS_FLIGHTPLAN_TOTAL_DISTANCE") or 0.0
            snap.gps_total_distance_nm = gps_total_m / 1852.0

            # Autopilot selections
            snap.ap_hdg_lock = bool(get("AUTOPILOT_HEADING_LOCK"))
            snap.ap_hdg_selected = get("AUTOPILOT_HEADING_LOCK_DIR") or 0.0
            snap.ap_alt_lock = bool(get("AUTOPILOT_ALTITUDE_LOCK"))
            snap.ap_alt_selected = get("AUTOPILOT_ALTITUDE_LOCK_VAR") or 0.0
            snap.ap_spd_lock = bool(get("AUTOPILOT_AIRSPEED_HOLD"))
            snap.ap_spd_selected = get("AUTOPILOT_AIRSPEED_HOLD_VAR") or 0.0
            snap.ap_vs_lock = bool(get("AUTOPILOT_VERTICAL_HOLD"))
            snap.ap_vs_selected = get("AUTOPILOT_VERTICAL_HOLD_VAR") or 0.0
            snap.ap_nav_lock = bool(get("AUTOPILOT_NAV1_LOCK"))
            snap.ap_fd_active = bool(get("AUTOPILOT_FLIGHT_DIRECTOR_ACTIVE"))

            # NAV radio
            snap.nav1_frequency = get("NAV_ACTIVE_FREQUENCY:1") or 0.0
            snap.nav1_dme_nm = get("NAV_DME:1") or 0.0
            snap.nav1_obs = get("NAV_OBS:1") or 0.0
            snap.nav1_cdi = get("NAV_CDI:1") or 0.0
            snap.nav1_has_loc = bool(get("NAV_HAS_LOCALIZER:1"))
            snap.nav1_has_gs = bool(get("NAV_HAS_GLIDE_SLOPE:1"))

            # COM radio
            snap.com1_frequency = get("COM_ACTIVE_FREQUENCY:1") or 0.0
            snap.com2_frequency = get("COM_ACTIVE_FREQUENCY:2") or 0.0

            # Update timestamp
            snap.last_update = time.time()

    def _detect_sim_running(self, snap: SimDataSnapshot) -> bool:
        """Detect if simulation is running (not paused/in menu)"""
        # Method 1: Check if absolute time is advancing
        time_delta = snap.absolute_time - self._last_absolute_time
        self._last_absolute_time = snap.absolute_time
        time_advancing = time_delta > 0.05

        # Method 2: Check if values are changing
        values_changed = (
            abs(snap.altitude - self._last_altitude) > 0.1 or
            abs(snap.vertical_speed - self._last_vs) > 0.1 or
            abs(snap.airspeed - self._last_ias) > 0.01
        )
        self._last_altitude = snap.altitude
        self._last_vs = snap.vertical_speed
        self._last_ias = snap.airspeed

        # Method 3: Parked on ground = not paused
        is_parked = snap.on_ground and snap.parking_brake and snap.ground_speed < 2

        # Valid data check
        has_valid_data = snap.latitude != 0.0
        rate_ok = snap.simulation_rate > 0

        return has_valid_data and rate_ok and (time_advancing or values_changed or is_parked)

    def _detect_phase(self) -> None:
        """Detect current flight phase"""
        snap = self._snapshot
        old_phase = self._current_phase

        if snap.on_ground:
            if not snap.engine_running or snap.parking_brake:
                new_phase = FlightPhase.PARKED
            elif snap.ground_speed < 5:
                new_phase = FlightPhase.PARKED
            elif snap.ground_speed < 30:
                new_phase = FlightPhase.TAXI
            else:
                new_phase = FlightPhase.TAKEOFF
        else:
            vs = snap.vertical_speed
            agl = snap.altitude_agl

            if agl < 100 and vs < -300:
                new_phase = FlightPhase.LANDING
            elif agl < 1500 and vs < -200:
                new_phase = FlightPhase.APPROACH
            elif agl < 500 and vs > 200:
                new_phase = FlightPhase.TAKEOFF
            elif vs > 500:
                new_phase = FlightPhase.CLIMB
            elif vs < -500:
                new_phase = FlightPhase.DESCENT
            else:
                new_phase = FlightPhase.CRUISE

        self._current_phase = new_phase

        if new_phase != old_phase:
            logger.debug(f"Phase: {old_phase.value} -> {new_phase.value}")

    def register_data_callback(self, callback: Callable[[SimDataSnapshot], None]) -> None:
        """Register callback for data updates (called from poll thread)"""
        self._data_callbacks.append(callback)

    # ========================================
    # COMPATIBILITY METHODS (for existing code)
    # ========================================

    def get(self, variable: str, use_cache: bool = True) -> Optional[Any]:
        """
        Get a variable value from cache.
        NEVER BLOCKS - returns cached value or None.
        For backward compatibility with existing code.
        """
        if use_cache:
            with self._raw_cache_lock:
                return self._raw_cache.get(variable)

        # If not using cache and polling, still return cache (non-blocking)
        if self._polling:
            with self._raw_cache_lock:
                return self._raw_cache.get(variable)

        # Only do direct fetch if not polling (legacy mode)
        if self._requests:
            try:
                return self._requests.get(variable)
            except:
                return None
        return None

    def get_data(self, variable: str) -> Optional[Any]:
        """Alias for get() - backward compatibility"""
        return self.get(variable)

    def get_polling_rate(self) -> int:
        """Get current polling rate in ms"""
        return self.poll_rate.poll_interval_ms

    def get_stats(self) -> Dict:
        """Get polling statistics"""
        return {
            'connected': self._connected,
            'polling': self._polling,
            'phase': self._current_phase.value,
            'poll_count': self._poll_count,
            'poll_rate_ms': self.poll_rate.poll_interval_ms,
            'avg_poll_ms': self._avg_poll_duration_ms,
            'cached_vars': len(self._raw_cache)
        }


# Global instance
_adaptive_simconnect: Optional[AdaptiveSimConnect] = None

def get_adaptive_simconnect() -> AdaptiveSimConnect:
    """Get or create global adaptive simconnect instance"""
    global _adaptive_simconnect
    if _adaptive_simconnect is None:
        _adaptive_simconnect = AdaptiveSimConnect()
    return _adaptive_simconnect
