# POC MAVLink to MSFS 2024 Bridge

## Prompt pour Claude Code

---

### PROJET : Bridge MAVLink ↔ SimConnect pour MSFS 2024

Tu vas créer un **Flight Controller virtuel** qui permet de piloter des aéronefs dans Microsoft Flight Simulator 2024 depuis QGroundControl (ou tout autre GCS MAVLink compatible).

Le concept est de créer un "ArduPilot virtuel" : un programme Python qui :
1. Reçoit des commandes MAVLink depuis QGroundControl (missions, modes de vol, commandes RC)
2. Implémente sa propre logique de contrôle (PIDs, navigation, modes de vol)
3. Envoie des commandes de pilotage à MSFS via SimConnect
4. Renvoie la télémétrie de MSFS vers QGroundControl au format MAVLink

---

## ARCHITECTURE GLOBALE

```
┌─────────────────────┐     UDP 14550      ┌──────────────────────────────────────┐
│   QGroundControl    │◄──────────────────►│         MAVLink Interface            │
│   (Ground Station)  │     MAVLink        │  • Receive commands/missions         │
└─────────────────────┘                    │  • Send telemetry (HEARTBEAT,        │
                                           │    ATTITUDE, GLOBAL_POSITION, etc.)  │
                                           └──────────────────┬───────────────────┘
                                                              │
                                                              ▼
                                           ┌──────────────────────────────────────┐
                                           │      Flight Controller Core          │
                                           │  ┌────────────────────────────────┐  │
                                           │  │  State Machine (Flight Modes)  │  │
                                           │  │  • STABILIZE, ALT_HOLD, LOITER │  │
                                           │  │  • GUIDED, AUTO, RTL, LAND     │  │
                                           │  └────────────────────────────────┘  │
                                           │  ┌────────────────────────────────┐  │
                                           │  │  Mission Controller            │  │
                                           │  │  • Waypoint navigation         │  │
                                           │  │  • Mission item execution      │  │
                                           │  └────────────────────────────────┘  │
                                           │  ┌────────────────────────────────┐  │
                                           │  │  Position Controller (Outer)   │  │
                                           │  │  • GPS → Velocity targets      │  │
                                           │  │  • Velocity → Attitude targets │  │
                                           │  └────────────────────────────────┘  │
                                           │  ┌────────────────────────────────┐  │
                                           │  │  Attitude Controller (Inner)   │  │
                                           │  │  • Roll/Pitch/Yaw PIDs         │  │
                                           │  │  • Rate controllers            │  │
                                           │  └────────────────────────────────┘  │
                                           └──────────────────┬───────────────────┘
                                                              │
                                                              ▼
                                           ┌──────────────────────────────────────┐
                                           │       SimConnect Interface           │
                                           │  • Read aircraft state (50-100Hz)    │
                                           │  • Write control commands            │
                                           │  • AILERON_SET, ELEVATOR_SET, etc.   │
                                           └──────────────────┬───────────────────┘
                                                              │
                                                              ▼
                                           ┌──────────────────────────────────────┐
                                           │         MSFS 2024                    │
                                           │   Jetson ONE / VTOL / Helicopter     │
                                           └──────────────────────────────────────┘
```

---

## STRUCTURE DES FICHIERS

```
mavlink_msfs_bridge/
├── main.py                     # Point d'entrée, boucle principale
├── config.py                   # Configuration (ports, gains PID, etc.)
│
├── mavlink_interface/
│   ├── __init__.py
│   ├── connection.py           # Connexion UDP MAVLink
│   ├── telemetry.py            # Envoi télémétrie vers QGC
│   ├── commands.py             # Réception commandes MAVLink
│   └── mission.py              # Gestion des missions (upload/download)
│
├── simconnect_interface/
│   ├── __init__.py
│   ├── connection.py           # Connexion SimConnect
│   ├── aircraft_state.py       # Lecture état avion (dataclass)
│   └── controls.py             # Envoi commandes de vol
│
├── flight_controller/
│   ├── __init__.py
│   ├── fc_core.py              # Coordinateur principal
│   ├── modes/
│   │   ├── __init__.py
│   │   ├── base_mode.py        # Classe abstraite mode de vol
│   │   ├── stabilize.py        # Mode STABILIZE
│   │   ├── alt_hold.py         # Mode ALT_HOLD
│   │   ├── loiter.py           # Mode LOITER (hover ou cercles)
│   │   ├── guided.py           # Mode GUIDED (go to point)
│   │   ├── auto.py             # Mode AUTO (mission)
│   │   ├── rtl.py              # Mode RTL (return to launch)
│   │   └── land.py             # Mode LAND
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── pid.py              # Classe PID générique
│   │   ├── position_controller.py   # Contrôle position GPS
│   │   ├── attitude_controller.py   # Contrôle attitude
│   │   └── rate_controller.py       # Contrôle taux de rotation
│   ├── navigation/
│   │   ├── __init__.py
│   │   ├── waypoint_nav.py     # Navigation entre waypoints
│   │   ├── geo_utils.py        # Calculs géographiques (distance, bearing)
│   │   └── trajectory.py       # Génération trajectoires (cercles, lignes)
│   └── failsafe/
│       ├── __init__.py
│       ├── geofence.py         # Limites géographiques
│       ├── battery.py          # Surveillance carburant/batterie
│       └── link_loss.py        # Perte de connexion GCS
│
├── aircraft_profiles/
│   ├── __init__.py
│   ├── base_profile.py         # Profil abstrait
│   ├── multicopter.py          # Jetson ONE, drones
│   ├── vtol.py                 # VTOLs
│   ├── helicopter.py           # Hélicoptères
│   └── fixed_wing.py           # Avions classiques
│
└── utils/
    ├── __init__.py
    ├── conversions.py          # Conversions unités (ft↔m, kts↔m/s, etc.)
    ├── filters.py              # Filtres (low-pass, complementary)
    └── logging_config.py       # Configuration logs
```

---

## SPÉCIFICATIONS TECHNIQUES DÉTAILLÉES

### 1. SIMCONNECT INTERFACE

#### Variables à lire (Aircraft State) - 50-100Hz

```python
@dataclass
class AircraftState:
    # Timestamp
    timestamp: float           # time.time()

    # Position (WGS84)
    latitude: float            # degrés décimaux
    longitude: float           # degrés décimaux
    altitude_msl: float        # mètres (converti depuis pieds)
    altitude_agl: float        # mètres (PLANE_ALT_ABOVE_GROUND)

    # Attitude (radians)
    roll: float                # PLANE_BANK_DEGREES → radians
    pitch: float               # PLANE_PITCH_DEGREES → radians
    yaw: float                 # PLANE_HEADING_DEGREES_TRUE → radians

    # Rates (rad/s)
    roll_rate: float           # ROTATION_VELOCITY_BODY_X
    pitch_rate: float          # ROTATION_VELOCITY_BODY_Y
    yaw_rate: float            # ROTATION_VELOCITY_BODY_Z

    # Vitesses
    airspeed: float            # m/s (AIRSPEED_INDICATED → converti)
    groundspeed: float         # m/s (GROUND_VELOCITY)
    vertical_speed: float      # m/s (VERTICAL_SPEED)
    velocity_north: float      # m/s (VELOCITY_WORLD_Z avec conversion)
    velocity_east: float       # m/s (VELOCITY_WORLD_X)
    velocity_down: float       # m/s (-VELOCITY_WORLD_Y)

    # Moteur/Énergie
    throttle_pct: float        # 0-100 (GENERAL_ENG_THROTTLE_LEVER_POSITION:1)
    fuel_pct: float            # 0-100 (FUEL_TOTAL_QUANTITY_WEIGHT ratio)
    engine_running: bool       # GENERAL_ENG_COMBUSTION:1

    # État
    on_ground: bool            # SIM_ON_GROUND
    parking_brake: bool        # BRAKE_PARKING_POSITION

    # GPS
    gps_fix: int               # 3 = 3D fix (simulé, toujours 3 dans MSFS)
    gps_satellites: int        # Simulé (12-16)
```

#### Variables SimConnect à requêter

```python
SIMCONNECT_VARIABLES = [
    # Position
    ("PLANE_LATITUDE", "degrees"),
    ("PLANE_LONGITUDE", "degrees"),
    ("PLANE_ALTITUDE", "feet"),
    ("PLANE_ALT_ABOVE_GROUND", "feet"),

    # Attitude
    ("PLANE_BANK_DEGREES", "degrees"),
    ("PLANE_PITCH_DEGREES", "degrees"),
    ("PLANE_HEADING_DEGREES_TRUE", "degrees"),

    # Rotation rates
    ("ROTATION_VELOCITY_BODY_X", "radians per second"),
    ("ROTATION_VELOCITY_BODY_Y", "radians per second"),
    ("ROTATION_VELOCITY_BODY_Z", "radians per second"),

    # Velocities
    ("AIRSPEED_INDICATED", "knots"),
    ("GROUND_VELOCITY", "knots"),
    ("VERTICAL_SPEED", "feet per minute"),
    ("VELOCITY_WORLD_X", "feet per second"),
    ("VELOCITY_WORLD_Y", "feet per second"),
    ("VELOCITY_WORLD_Z", "feet per second"),

    # Engine
    ("GENERAL_ENG_THROTTLE_LEVER_POSITION:1", "percent"),
    ("GENERAL_ENG_COMBUSTION:1", "bool"),
    ("FUEL_TOTAL_QUANTITY_WEIGHT", "pounds"),
    ("FUEL_TOTAL_CAPACITY", "gallons"),

    # State
    ("SIM_ON_GROUND", "bool"),
    ("BRAKE_PARKING_POSITION", "bool"),
]
```

#### Commandes à envoyer

```python
@dataclass
class ControlCommands:
    aileron: float      # -1.0 à +1.0 (gauche/droite)
    elevator: float     # -1.0 à +1.0 (cabrer/piquer)
    rudder: float       # -1.0 à +1.0 (gauche/droite)
    throttle: float     # 0.0 à 1.0
    collective: float   # 0.0 à 1.0 (pour hélicos/VTOLs)

# Envoi via SimConnect Events
def send_controls(cmd: ControlCommands):
    # Convertir -1/+1 vers -16383/+16383 pour SimConnect
    simconnect.send_event("AILERON_SET", int(cmd.aileron * 16383))
    simconnect.send_event("ELEVATOR_SET", int(cmd.elevator * 16383))
    simconnect.send_event("RUDDER_SET", int(cmd.rudder * 16383))
    simconnect.send_event("THROTTLE_SET", int(cmd.throttle * 16383))
```

---

### 2. MAVLINK INTERFACE

#### Messages à envoyer (Télémétrie) vers QGC

```python
# HEARTBEAT - 1Hz
def send_heartbeat():
    mavlink.send(mavutil.mavlink.MAVLink_heartbeat_message(
        type=mavutil.mavlink.MAV_TYPE_QUADROTOR,  # ou VTOL, HELICOPTER, FIXED_WING
        autopilot=mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
        base_mode=get_base_mode(),      # MAV_MODE_FLAG_*
        custom_mode=get_custom_mode(),  # Mode ArduPilot (STABILIZE=0, etc.)
        system_status=mavutil.mavlink.MAV_STATE_ACTIVE
    ))

# ATTITUDE - 50Hz
def send_attitude(state: AircraftState):
    mavlink.send(mavutil.mavlink.MAVLink_attitude_message(
        time_boot_ms=get_boot_time_ms(),
        roll=state.roll,           # radians
        pitch=state.pitch,         # radians
        yaw=state.yaw,             # radians
        rollspeed=state.roll_rate,
        pitchspeed=state.pitch_rate,
        yawspeed=state.yaw_rate
    ))

# GLOBAL_POSITION_INT - 10Hz
def send_global_position(state: AircraftState):
    mavlink.send(mavutil.mavlink.MAVLink_global_position_int_message(
        time_boot_ms=get_boot_time_ms(),
        lat=int(state.latitude * 1e7),    # degrés * 10^7
        lon=int(state.longitude * 1e7),
        alt=int(state.altitude_msl * 1000),  # mm
        relative_alt=int(state.altitude_agl * 1000),
        vx=int(state.velocity_north * 100),  # cm/s
        vy=int(state.velocity_east * 100),
        vz=int(-state.velocity_down * 100),  # NED vers NED
        hdg=int(math.degrees(state.yaw) * 100)  # centidegrés
    ))

# GPS_RAW_INT - 5Hz
def send_gps_raw(state: AircraftState):
    mavlink.send(mavutil.mavlink.MAVLink_gps_raw_int_message(
        time_usec=int(time.time() * 1e6),
        fix_type=3,  # 3D fix
        lat=int(state.latitude * 1e7),
        lon=int(state.longitude * 1e7),
        alt=int(state.altitude_msl * 1000),
        eph=100,  # HDOP * 100 (simulé)
        epv=100,  # VDOP * 100
        vel=int(state.groundspeed * 100),  # cm/s
        cog=int(math.degrees(state.yaw) * 100),  # centidegrés
        satellites_visible=14
    ))

# VFR_HUD - 10Hz
def send_vfr_hud(state: AircraftState):
    mavlink.send(mavutil.mavlink.MAVLink_vfr_hud_message(
        airspeed=state.airspeed,         # m/s
        groundspeed=state.groundspeed,   # m/s
        heading=int(math.degrees(state.yaw)) % 360,
        throttle=int(state.throttle_pct),
        alt=state.altitude_msl,
        climb=state.vertical_speed
    ))

# SYS_STATUS - 1Hz
def send_sys_status(state: AircraftState):
    mavlink.send(mavutil.mavlink.MAVLink_sys_status_message(
        onboard_control_sensors_present=0,
        onboard_control_sensors_enabled=0,
        onboard_control_sensors_health=0,
        load=500,  # CPU load (simulé)
        voltage_battery=int(state.fuel_pct * 126),  # ~12.6V simulé
        current_battery=-1,
        battery_remaining=int(state.fuel_pct),
        drop_rate_comm=0,
        errors_comm=0,
        errors_count1=0,
        errors_count2=0,
        errors_count3=0,
        errors_count4=0
    ))

# RC_CHANNELS - 5Hz (simulé)
def send_rc_channels():
    mavlink.send(mavutil.mavlink.MAVLink_rc_channels_message(
        time_boot_ms=get_boot_time_ms(),
        chancount=8,
        chan1_raw=1500,  # Aileron center
        chan2_raw=1500,  # Elevator center
        chan3_raw=1500,  # Throttle mid
        chan4_raw=1500,  # Rudder center
        chan5_raw=1500,  # Mode switch
        chan6_raw=1500,
        chan7_raw=1500,
        chan8_raw=1500,
        # ... chan9-18 = 65535 (not used)
        rssi=255  # Signal strength max
    ))
```

#### Messages à recevoir depuis QGC

```python
# Commandes à traiter
MAVLINK_COMMANDS = {
    # Changement de mode
    "SET_MODE": handle_set_mode,

    # Commandes RC (joystick QGC)
    "RC_CHANNELS_OVERRIDE": handle_rc_override,
    "MANUAL_CONTROL": handle_manual_control,

    # Navigation
    "SET_POSITION_TARGET_GLOBAL_INT": handle_position_target,
    "SET_POSITION_TARGET_LOCAL_NED": handle_position_target_local,

    # Mission
    "MISSION_COUNT": handle_mission_count,
    "MISSION_ITEM_INT": handle_mission_item,
    "MISSION_REQUEST_LIST": handle_mission_request_list,
    "MISSION_REQUEST_INT": handle_mission_request,
    "MISSION_ACK": handle_mission_ack,
    "MISSION_SET_CURRENT": handle_mission_set_current,

    # Commandes
    "COMMAND_LONG": handle_command_long,
    "COMMAND_INT": handle_command_int,

    # Paramètres (optionnel)
    "PARAM_REQUEST_LIST": handle_param_request_list,
    "PARAM_REQUEST_READ": handle_param_request_read,
    "PARAM_SET": handle_param_set,
}

# Exemple: handle_set_mode
def handle_set_mode(msg):
    base_mode = msg.base_mode
    custom_mode = msg.custom_mode

    # Mapping custom_mode ArduCopter
    COPTER_MODES = {
        0: "STABILIZE",
        2: "ALT_HOLD",
        3: "AUTO",
        4: "GUIDED",
        5: "LOITER",
        6: "RTL",
        9: "LAND",
    }

    new_mode = COPTER_MODES.get(custom_mode, "STABILIZE")
    flight_controller.set_mode(new_mode)
```

---

### 3. FLIGHT CONTROLLER

#### Classe PID

```python
class PID:
    def __init__(self, kp: float, ki: float, kd: float,
                 output_min: float = -1.0, output_max: float = 1.0,
                 integral_max: float = 0.5):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.integral_max = integral_max

        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = None

    def update(self, error: float, dt: float) -> float:
        # Proportional
        p = self.kp * error

        # Integral with anti-windup
        self.integral += error * dt
        self.integral = max(-self.integral_max, min(self.integral_max, self.integral))
        i = self.ki * self.integral

        # Derivative
        if self.prev_time is not None:
            d = self.kd * (error - self.prev_error) / dt
        else:
            d = 0.0

        self.prev_error = error

        # Output with limits
        output = p + i + d
        return max(self.output_min, min(self.output_max, output))

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
```

#### Position Controller

```python
class PositionController:
    """Contrôle de position GPS → Commandes d'attitude"""

    def __init__(self, config: dict):
        # PID Position → Vitesse
        self.pos_north_pid = PID(kp=1.0, ki=0.1, kd=0.5)
        self.pos_east_pid = PID(kp=1.0, ki=0.1, kd=0.5)
        self.pos_down_pid = PID(kp=2.0, ki=0.2, kd=0.8)

        # PID Vitesse → Attitude
        self.vel_north_pid = PID(kp=0.5, ki=0.05, kd=0.1, output_max=0.5)  # max 30° pitch
        self.vel_east_pid = PID(kp=0.5, ki=0.05, kd=0.1, output_max=0.5)   # max 30° roll

        # Limites
        self.max_velocity_xy = 10.0  # m/s
        self.max_velocity_z = 5.0    # m/s
        self.max_tilt = math.radians(35)  # 35 degrés max

    def update(self, current: AircraftState, target_lat: float, target_lon: float,
               target_alt: float, dt: float) -> Tuple[float, float, float]:
        """
        Retourne (target_roll, target_pitch, throttle_adjustment)
        """
        # Calcul erreur position en mètres (NED frame)
        pos_error_north, pos_error_east = geo_utils.gps_to_ned(
            current.latitude, current.longitude,
            target_lat, target_lon
        )
        pos_error_down = current.altitude_msl - target_alt

        # Position → Vitesse cible
        vel_target_north = self.pos_north_pid.update(pos_error_north, dt)
        vel_target_east = self.pos_east_pid.update(pos_error_east, dt)
        vel_target_down = self.pos_down_pid.update(pos_error_down, dt)

        # Limiter vitesses
        vel_target_north = max(-self.max_velocity_xy, min(self.max_velocity_xy, vel_target_north))
        vel_target_east = max(-self.max_velocity_xy, min(self.max_velocity_xy, vel_target_east))
        vel_target_down = max(-self.max_velocity_z, min(self.max_velocity_z, vel_target_down))

        # Erreur vitesse
        vel_error_north = vel_target_north - current.velocity_north
        vel_error_east = vel_target_east - current.velocity_east

        # Vitesse → Attitude cible (rotation dans le frame body)
        yaw = current.yaw
        cos_yaw = math.cos(yaw)
        sin_yaw = math.sin(yaw)

        # Rotation NED → Body
        vel_error_forward = vel_error_north * cos_yaw + vel_error_east * sin_yaw
        vel_error_right = -vel_error_north * sin_yaw + vel_error_east * cos_yaw

        # PID pour attitude
        target_pitch = -self.vel_north_pid.update(vel_error_forward, dt)  # pitch nose down pour avancer
        target_roll = self.vel_east_pid.update(vel_error_right, dt)

        # Limiter inclinaison
        target_roll = max(-self.max_tilt, min(self.max_tilt, target_roll))
        target_pitch = max(-self.max_tilt, min(self.max_tilt, target_pitch))

        # Throttle pour altitude
        throttle_adj = -self.pos_down_pid.update(pos_error_down, dt)

        return target_roll, target_pitch, throttle_adj
```

#### Attitude Controller

```python
class AttitudeController:
    """Contrôle d'attitude → Commandes surfaces/moteurs"""

    def __init__(self, config: dict):
        # PID Attitude
        self.roll_pid = PID(kp=4.0, ki=0.5, kd=0.3)
        self.pitch_pid = PID(kp=4.0, ki=0.5, kd=0.3)
        self.yaw_pid = PID(kp=2.0, ki=0.1, kd=0.2)

        # PID Rate (inner loop, plus rapide)
        self.roll_rate_pid = PID(kp=0.5, ki=0.1, kd=0.01)
        self.pitch_rate_pid = PID(kp=0.5, ki=0.1, kd=0.01)
        self.yaw_rate_pid = PID(kp=0.3, ki=0.05, kd=0.01)

    def update(self, current: AircraftState, target_roll: float, target_pitch: float,
               target_yaw_rate: float, dt: float) -> ControlCommands:
        """
        Retourne les commandes de contrôle (-1 à +1)
        """
        # Erreur attitude
        roll_error = target_roll - current.roll
        pitch_error = target_pitch - current.pitch

        # Attitude → Rate cible
        target_roll_rate = self.roll_pid.update(roll_error, dt)
        target_pitch_rate = self.pitch_pid.update(pitch_error, dt)

        # Erreur rate
        roll_rate_error = target_roll_rate - current.roll_rate
        pitch_rate_error = target_pitch_rate - current.pitch_rate
        yaw_rate_error = target_yaw_rate - current.yaw_rate

        # Rate → Commandes
        aileron = self.roll_rate_pid.update(roll_rate_error, dt)
        elevator = self.pitch_rate_pid.update(pitch_rate_error, dt)
        rudder = self.yaw_rate_pid.update(yaw_rate_error, dt)

        return ControlCommands(
            aileron=aileron,
            elevator=elevator,
            rudder=rudder,
            throttle=0.0,  # géré séparément
            collective=0.0
        )
```

#### Mode GUIDED (exemple)

```python
class GuidedMode(BaseFlightMode):
    """Mode GUIDED - Aller vers un point GPS commandé"""

    def __init__(self, fc_core):
        super().__init__(fc_core)
        self.target_lat = None
        self.target_lon = None
        self.target_alt = None
        self.target_yaw = None
        self.position_controller = PositionController(fc_core.config)
        self.attitude_controller = AttitudeController(fc_core.config)

    def set_target(self, lat: float, lon: float, alt: float, yaw: float = None):
        """Appelé lors de réception SET_POSITION_TARGET_GLOBAL_INT"""
        self.target_lat = lat
        self.target_lon = lon
        self.target_alt = alt
        self.target_yaw = yaw

    def update(self, state: AircraftState, dt: float) -> ControlCommands:
        if self.target_lat is None:
            # Pas de cible, maintenir position actuelle
            return self._hold_position(state, dt)

        # Position controller
        target_roll, target_pitch, throttle_adj = self.position_controller.update(
            state, self.target_lat, self.target_lon, self.target_alt, dt
        )

        # Yaw control
        if self.target_yaw is not None:
            yaw_error = self._normalize_angle(self.target_yaw - state.yaw)
            target_yaw_rate = yaw_error * 1.0  # Simple P controller pour yaw
        else:
            # Yaw vers direction de déplacement
            target_yaw_rate = 0.0

        # Attitude controller
        commands = self.attitude_controller.update(
            state, target_roll, target_pitch, target_yaw_rate, dt
        )

        # Throttle
        base_throttle = 0.5  # hover throttle
        commands.throttle = base_throttle + throttle_adj
        commands.throttle = max(0.0, min(1.0, commands.throttle))

        return commands
```

#### Mode AUTO (Mission)

```python
class AutoMode(BaseFlightMode):
    """Mode AUTO - Exécution de mission"""

    def __init__(self, fc_core):
        super().__init__(fc_core)
        self.mission_items = []  # Liste des waypoints
        self.current_wp_index = 0
        self.wp_reached_radius = 10.0  # mètres

    def load_mission(self, items: List[MissionItem]):
        self.mission_items = items
        self.current_wp_index = 0

    def update(self, state: AircraftState, dt: float) -> ControlCommands:
        if not self.mission_items:
            return self._loiter(state, dt)

        current_wp = self.mission_items[self.current_wp_index]

        # Vérifier si WP atteint
        distance = geo_utils.distance_between(
            state.latitude, state.longitude,
            current_wp.lat, current_wp.lon
        )

        if distance < self.wp_reached_radius:
            # WP atteint, passer au suivant
            self._advance_waypoint()
            if self.current_wp_index >= len(self.mission_items):
                # Mission terminée
                return self._loiter(state, dt)
            current_wp = self.mission_items[self.current_wp_index]

        # Naviguer vers WP actuel
        return self._navigate_to(state, current_wp, dt)

    def _navigate_to(self, state: AircraftState, wp: MissionItem, dt: float):
        # Utilise le même code que GUIDED
        # ...
```

---

### 4. CONFIGURATION

```python
# config.py

CONFIG = {
    # Connexions
    "mavlink": {
        "connection_string": "udpin:0.0.0.0:14550",
        "system_id": 1,
        "component_id": 1,
    },

    # Télémétrie rates (Hz)
    "telemetry_rates": {
        "heartbeat": 1,
        "attitude": 50,
        "global_position": 10,
        "gps_raw": 5,
        "vfr_hud": 10,
        "sys_status": 1,
        "rc_channels": 5,
    },

    # Type d'appareil
    "vehicle_type": "copter",  # "copter", "vtol", "helicopter", "plane"

    # PIDs Position (outer loop)
    "position_pid": {
        "xy": {"kp": 1.0, "ki": 0.1, "kd": 0.5},
        "z": {"kp": 2.0, "ki": 0.2, "kd": 0.8},
    },

    # PIDs Velocity
    "velocity_pid": {
        "xy": {"kp": 0.5, "ki": 0.05, "kd": 0.1},
    },

    # PIDs Attitude (middle loop)
    "attitude_pid": {
        "roll": {"kp": 4.0, "ki": 0.5, "kd": 0.3},
        "pitch": {"kp": 4.0, "ki": 0.5, "kd": 0.3},
        "yaw": {"kp": 2.0, "ki": 0.1, "kd": 0.2},
    },

    # PIDs Rate (inner loop)
    "rate_pid": {
        "roll": {"kp": 0.5, "ki": 0.1, "kd": 0.01},
        "pitch": {"kp": 0.5, "ki": 0.1, "kd": 0.01},
        "yaw": {"kp": 0.3, "ki": 0.05, "kd": 0.01},
    },

    # Limites
    "limits": {
        "max_tilt_deg": 35,
        "max_velocity_xy": 10.0,  # m/s
        "max_velocity_z": 5.0,    # m/s
        "max_yaw_rate": 60,       # deg/s
    },

    # Navigation
    "navigation": {
        "wp_reached_radius": 10.0,  # mètres
        "loiter_radius": 50.0,      # mètres (pour avions)
    },

    # Failsafe
    "failsafe": {
        "gcs_timeout": 5.0,        # secondes sans message GCS
        "low_fuel_pct": 20,        # % fuel pour warning
        "critical_fuel_pct": 10,   # % fuel pour RTL auto
    },

    # Home position (définie au démarrage)
    "home": {
        "lat": None,
        "lon": None,
        "alt": None,
    },
}
```

---

### 5. BOUCLE PRINCIPALE

```python
# main.py

import time
import asyncio
from config import CONFIG
from mavlink_interface import MAVLinkConnection
from simconnect_interface import SimConnectInterface
from flight_controller import FlightControllerCore

async def main():
    # Initialisation
    mavlink = MAVLinkConnection(CONFIG["mavlink"])
    simconnect = SimConnectInterface()
    fc = FlightControllerCore(CONFIG)

    # Connexions
    await mavlink.connect()
    simconnect.connect()

    # Définir HOME
    initial_state = simconnect.get_state()
    CONFIG["home"]["lat"] = initial_state.latitude
    CONFIG["home"]["lon"] = initial_state.longitude
    CONFIG["home"]["alt"] = initial_state.altitude_msl

    print(f"HOME set: {CONFIG['home']}")

    # Timers pour télémétrie
    telemetry_timers = {
        "heartbeat": 0,
        "attitude": 0,
        "global_position": 0,
        "gps_raw": 0,
        "vfr_hud": 0,
        "sys_status": 0,
        "rc_channels": 0,
    }

    # Boucle principale - 100Hz
    loop_rate = 100  # Hz
    loop_period = 1.0 / loop_rate

    last_time = time.time()

    try:
        while True:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time

            # 1. Lire état MSFS
            state = simconnect.get_state()

            # 2. Recevoir messages MAVLink (non-bloquant)
            while True:
                msg = mavlink.recv_match(blocking=False)
                if msg is None:
                    break
                fc.process_mavlink_message(msg)

            # 3. Mise à jour Flight Controller
            commands = fc.update(state, dt)

            # 4. Envoyer commandes à MSFS
            simconnect.send_controls(commands)

            # 5. Envoyer télémétrie MAVLink
            for telem_type, last_sent in telemetry_timers.items():
                interval = 1.0 / CONFIG["telemetry_rates"][telem_type]
                if current_time - last_sent >= interval:
                    mavlink.send_telemetry(telem_type, state, fc)
                    telemetry_timers[telem_type] = current_time

            # 6. Maintenir le loop rate
            elapsed = time.time() - current_time
            sleep_time = loop_period - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        simconnect.disconnect()
        mavlink.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## UTILITAIRES GÉO

```python
# utils/geo_utils.py

import math

EARTH_RADIUS = 6371000  # mètres

def distance_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en mètres entre deux points GPS (Haversine)"""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return EARTH_RADIUS * c

def bearing_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Bearing en radians de point 1 vers point 2"""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)

    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)

    return math.atan2(x, y)

def gps_to_ned(lat_current: float, lon_current: float, lat_target: float, lon_target: float) -> Tuple[float, float]:
    """Convertit différence GPS en coordonnées NED (North, East) en mètres"""
    # Approximation pour petites distances
    lat_rad = math.radians(lat_current)

    meters_per_deg_lat = 111132.92 - 559.82 * math.cos(2 * lat_rad) + 1.175 * math.cos(4 * lat_rad)
    meters_per_deg_lon = 111412.84 * math.cos(lat_rad) - 93.5 * math.cos(3 * lat_rad)

    north = (lat_target - lat_current) * meters_per_deg_lat
    east = (lon_target - lon_current) * meters_per_deg_lon

    return north, east

def ned_to_gps(lat_origin: float, lon_origin: float, north: float, east: float) -> Tuple[float, float]:
    """Convertit coordonnées NED en GPS"""
    lat_rad = math.radians(lat_origin)

    meters_per_deg_lat = 111132.92 - 559.82 * math.cos(2 * lat_rad) + 1.175 * math.cos(4 * lat_rad)
    meters_per_deg_lon = 111412.84 * math.cos(lat_rad) - 93.5 * math.cos(3 * lat_rad)

    lat = lat_origin + north / meters_per_deg_lat
    lon = lon_origin + east / meters_per_deg_lon

    return lat, lon
```

---

## CONVERSIONS D'UNITÉS

```python
# utils/conversions.py

def feet_to_meters(feet: float) -> float:
    return feet * 0.3048

def meters_to_feet(meters: float) -> float:
    return meters / 0.3048

def knots_to_ms(knots: float) -> float:
    return knots * 0.514444

def ms_to_knots(ms: float) -> float:
    return ms / 0.514444

def fpm_to_ms(fpm: float) -> float:
    """Feet per minute to meters per second"""
    return fpm * 0.00508

def ms_to_fpm(ms: float) -> float:
    return ms / 0.00508

def degrees_to_radians(deg: float) -> float:
    return deg * 0.017453292519943295

def radians_to_degrees(rad: float) -> float:
    return rad * 57.29577951308232
```

---

## DÉPENDANCES

```
# requirements.txt
pymavlink>=2.4.40
SimConnect>=0.4.26
numpy>=1.24.0
```

---

## PHASES DE DÉVELOPPEMENT

### Phase 1 : Base (MVP)
1. Connexion SimConnect - lecture état avion
2. Connexion MAVLink UDP - envoi HEARTBEAT
3. Télémétrie basique (ATTITUDE, GLOBAL_POSITION)
4. Vérifier que QGC reconnaît le véhicule

### Phase 2 : Contrôle basique
1. Réception RC_CHANNELS_OVERRIDE
2. Mode STABILIZE (passthrough joystick QGC)
3. PID Attitude basique
4. Test avec Jetson ONE

### Phase 3 : Modes de vol
1. Mode ALT_HOLD
2. Mode LOITER
3. Mode GUIDED (go to point)
4. Tuning PIDs

### Phase 4 : Mission
1. Upload/download mission
2. Mode AUTO
3. Navigation waypoints
4. Mode RTL

### Phase 5 : Polish
1. Failsafes
2. Paramètres configurables via MAVLink
3. Support multi-véhicules (copter, VTOL, plane)
4. Interface de configuration

---

## NOTES IMPORTANTES

1. **Tester d'abord avec le Jetson ONE** - C'est le plus proche d'un drone
2. **Commencer par la télémétrie** - S'assurer que QGC voit bien l'appareil
3. **PIDs à tuner** - Les valeurs par défaut ne seront pas parfaites
4. **Rate limiters** - Ajouter des filtres pour éviter les oscillations
5. **Logs détaillés** - Essentiels pour le debug

---

## COMMANDE POUR DÉMARRER

```
Crée le projet "mavlink_msfs_bridge" selon l'architecture décrite ci-dessus.
Commence par la Phase 1 (connexions et télémétrie basique).
Utilise Python 3.10+, pymavlink et SimConnect.
Le véhicule cible initial est le Jetson ONE (multicopter).
```
