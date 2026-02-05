"""
Mission Generator V2 for Microsoft Flight Simulator 2024
Enhanced with:
- AI Copilot with Voice (STT/TTS)
- Career Mode with Pilot Progression
- Fuel Management & Maintenance
- Flight Recording & Replay
- Performance Optimization
"""

import json
import random
import math
import threading
import logging
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import Dict, Optional, List

import customtkinter as ctk

# ============================================================================
# APPLICATION ROOT DIRECTORY (handles PyInstaller)
# ============================================================================

def get_app_dir() -> Path:
    """Get directory for user files (config, savegame) - next to exe or script"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable (PyInstaller)
        return Path(sys.executable).parent
    else:
        # Running as Python script
        return Path(__file__).parent

def get_data_dir() -> Path:
    """Get directory for bundled data files (airports, sounds) - _internal folder when frozen"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - use _MEIPASS for bundled files
        return Path(sys._MEIPASS)
    else:
        # Running as Python script - same as APP_DIR
        return Path(__file__).parent

APP_DIR = get_app_dir()
DATA_DIR = get_data_dir()

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logs_dir = APP_DIR / "logs"
logs_dir.mkdir(exist_ok=True)

log_filename = logs_dir / f"mission_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MissionGenerator.V2")
logger.info("=== MSFS 2024 Mission Generator V2 - Starting ===")

# ============================================================================
# V2 MODULE IMPORTS
# ============================================================================

# Optimization modules
try:
    from optimization import get_cache, PerformanceMonitor, get_performance_monitor
    from optimization.simconnect_opt import AdaptiveSimConnect, get_adaptive_simconnect
    from optimization.airport_index import get_airport_index
    OPTIMIZATION_AVAILABLE = True
    logger.info("V2 Optimization modules loaded")
except ImportError as e:
    OPTIMIZATION_AVAILABLE = False
    logger.warning(f"Optimization modules not available: {e}")

# Career modules
try:
    from career import get_pilot, load_pilot, get_company_manager, get_logbook, get_progression
    from career.pilot_profile import License
    CAREER_AVAILABLE = True
    logger.info("V2 Career modules loaded")
except ImportError as e:
    CAREER_AVAILABLE = False
    logger.warning(f"Career modules not available: {e}")

# Systems modules
try:
    from systems import (
        get_fuel_manager, get_maintenance, get_failure_manager,
        get_passenger_manager, get_challenge_manager, get_checkride_manager,
        get_pattern_trainer, PatternLeg
    )
    from systems.weather_sim import get_weather_system
    SYSTEMS_AVAILABLE = True
    logger.info("V2 Systems modules loaded")
except ImportError as e:
    SYSTEMS_AVAILABLE = False
    logger.warning(f"Systems modules not available: {e}")

# Copilot modules
try:
    from copilot import (
        get_phase_detector, get_callout_manager, get_error_detector,
        get_checklist_manager, get_atc_simulator, get_copilot_llm,
        get_voice_system, get_debrief_manager
    )
    from copilot.phases import FlightPhase, FlightState
    COPILOT_AVAILABLE = True
    logger.info("V2 Copilot modules loaded")
except ImportError as e:
    COPILOT_AVAILABLE = False
    logger.warning(f"Copilot modules not available: {e}")

# Utils modules
try:
    from utils import get_flight_recorder, DistanceCalculator
    UTILS_AVAILABLE = True
    logger.info("V2 Utils modules loaded")
except ImportError as e:
    UTILS_AVAILABLE = False
    logger.warning(f"Utils modules not available: {e}")

# Aviation API
try:
    from aviation_api import prepare_mission_data, get_weather_info, calculate_optimal_runway, calculate_distance_nm
    AVIATION_API_AVAILABLE = True
    logger.info("V2 Aviation API loaded")
except ImportError as e:
    AVIATION_API_AVAILABLE = False
    logger.warning(f"Aviation API not available: {e}")

# OpenAIP for real-world navaids and procedures
try:
    from openaip import get_openaip_client, OpenAIPClient
    OPENAIP_AVAILABLE = True
    logger.info("OpenAIP integration loaded")
except ImportError as e:
    OPENAIP_AVAILABLE = False
    logger.warning(f"OpenAIP not available: {e}")

# Audio (pygame)
pygame_available = False
try:
    import pygame
    pygame.mixer.init()
    pygame_available = True
    logger.info("Pygame mixer initialized")
except Exception as e:
    logger.warning(f"Pygame not available: {e}")

# ============================================================================
# CONFIGURATION
# ============================================================================

V2_DIR = APP_DIR  # Use APP_DIR which handles PyInstaller

# User files (can be modified, saved next to exe)
CONFIG_FILE = APP_DIR / "config.json"
SAVE_FILE = APP_DIR / "savegame.json"
FLIGHTPLANS_DIR = APP_DIR / "flightplans"

# Data files (bundled with app, in _internal when frozen)
AIRPORTS_FILE = DATA_DIR / "airports.json"
NAVAIDS_FILE = DATA_DIR / "navaids.json"
SOUNDS_DIR = DATA_DIR / "sounds"

FLIGHTPLANS_DIR.mkdir(exist_ok=True)

# Log directories for debugging
logger.info(f"Application directory (user files): {APP_DIR}")
logger.info(f"Data directory (bundled files): {DATA_DIR}")
logger.info(f"Config file path: {CONFIG_FILE}")

# Default update interval (will be adaptive in V2)
UPDATE_INTERVAL = 1000

# ============================================================================
# PILOT HOURLY RATES (realistic)
# ============================================================================

PILOT_HOURLY_RATES = {
    "light_piston": 55,
    "twin_piston": 75,
    "single_turboprop": 95,
    "turboprop": 120,
    "light_jet": 150,
    "jet": 200,
    "heavy_jet": 280,
    "helicopter": 85,
}

# Per diem allowances
PER_DIEM_SHORT = 35
PER_DIEM_MEDIUM = 65
PER_DIEM_LONG = 120

# Bonuses
BONUS_NIGHT_FLIGHT = 0.25
BONUS_WEEKEND = 0.15
BONUS_BAD_WEATHER = 0.20
BONUS_SOFT_LANDING = 50
BONUS_GOOD_LANDING = 25
BONUS_CONSTRAINTS_RESPECTED = 30

# Penalties
PENALTY_HARD_LANDING_MEDIUM = -50
PENALTY_HARD_LANDING_SEVERE = -150
PENALTY_CONSTRAINT_VIOLATION = -10
PENALTY_OVERSPEED = -25

# Aircraft profiles
AIRCRAFT_PROFILES = {
    "light_piston": {"type_vol": "VFR", "max_alt": 12000, "description": "Light single piston"},
    "twin_piston": {"type_vol": "VFR/IFR", "max_alt": 20000, "description": "Twin piston"},
    "single_turboprop": {"type_vol": "IFR", "max_alt": 28000, "description": "Single turboprop"},
    "turboprop": {"type_vol": "IFR", "max_alt": 31000, "description": "Twin turboprop"},
    "light_jet": {"type_vol": "IFR", "max_alt": 45000, "description": "Light jet"},
    "jet": {"type_vol": "IFR", "max_alt": 41000, "description": "Commercial jet"},
    "heavy_jet": {"type_vol": "IFR", "max_alt": 43000, "description": "Heavy jet"},
    "helicopter": {"type_vol": "VFR", "max_alt": 10000, "description": "Helicopter"},
}

# ============================================================================
# CAREER PANEL COLORS
# ============================================================================

COLORS = {
    'accent': '#4A90D9',      # Blue - titles
    'positive': '#00FF00',    # Green - success
    'positive_alt': '#00AA00',
    'negative': '#FF4444',    # Red - error
    'warning': '#FFAA00',     # Orange - warning
    'text': '#AAAAAA',        # Gray - normal text
    'text_dim': '#888888',    # Dark gray
    'bg_dark': '#1a1a2e',     # Custom background
    'bg_panel': '#2d2d44',    # Panel background
}

LICENSE_COLORS = {
    'STUDENT': '#888888',
    'PPL': '#4A90D9',
    'CPL': '#FFAA00',
    'ATPL': '#00FF00',
}

REPUTATION_COLORS = {
    'BLACKLISTED': '#FF0000',
    'POOR': '#FF4444',
    'NEUTRAL': '#888888',
    'GOOD': '#4A90D9',
    'EXCELLENT': '#00AA00',
    'ELITE': '#FFD700'
}

CATEGORY_DISPLAY_NAMES = {
    'light_piston': 'Monomoteur',
    'twin_piston': 'Bimoteur',
    'single_turboprop': 'Turboprop Solo',
    'turboprop': 'Turboprop',
    'light_jet': 'Jet Leger',
    'jet': 'Jet',
    'heavy_jet': 'Gros Porteur',
    'helicopter': 'Helicoptere',
}

# ============================================================================
# CONFIGURATION & SAVE MANAGEMENT
# ============================================================================

def load_config() -> dict:
    """Load configuration - creates default config file if it doesn't exist"""
    default_config = {
        "pln_destination_folder": str(FLIGHTPLANS_DIR.absolute()),
        "groq_api_key": "",
        "openaip_api_key": "",
        "auto_copy_pln": False,
        "copilot_enabled": True,
        "voice_enabled": True,
        "voice_language": "fr-FR",
        "career_mode": True,
        "performance_mode": "balanced",
        "fuel_management": True,
        "maintenance_enabled": True,
        "passenger_comfort": True,
        "ptt_joystick_id": 1,
        "ptt_button_id": 18,
        "ptt_enabled": True,
        "mission_distance_min": 50,
        "mission_distance_max": 500
    }

    if not CONFIG_FILE.exists():
        # Create default config file
        logger.info(f"Creating default config at: {CONFIG_FILE}")
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            logger.info("Default config created - please add your API keys")
        except Exception as e:
            logger.error(f"Could not create config file: {e}")
        return default_config

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Add any missing keys from default
            updated = False
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
                    updated = True
            # Save if we added new keys
            if updated:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
            return config
    except Exception as e:
        logger.error(f"Config load error: {e}, using defaults")
        return default_config


def save_config(config: dict):
    """Save configuration"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info("Configuration saved")
    except Exception as e:
        logger.error(f"Config save error: {e}")


def load_save() -> dict:
    """Load save game"""
    try:
        with open(SAVE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Save loaded: {data.get('pilot', {}).get('bank_balance', 100):.2f} EUR")
            return data
    except:
        logger.info("New save created")
        return {
            "pilot": {
                "name": "Pilote",
                "bank_balance": 100.00,
                "total_hours": 0,
                "missions_completed": 0
            }
        }


def save_game(data: dict):
    """Save game state"""
    try:
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Save error: {e}")


# ============================================================================
# AUDIO
# ============================================================================

def play_sound(sound_file: str):
    """Play a sound file"""
    if not pygame_available:
        return
    sound_path = SOUNDS_DIR / sound_file
    if sound_path.exists():
        try:
            pygame.mixer.music.load(str(sound_path))
            pygame.mixer.music.play()
        except Exception as e:
            logger.error(f"Audio error: {e}")


def play_penalty_sound():
    play_sound("penalty.wav")


def play_success_sound():
    play_sound("success.wav")


def play_crash_sound():
    play_sound("crash.wav")


def play_mission_sound():
    play_sound("mission.wav")


# ============================================================================
# NAVAIDS
# ============================================================================

def load_navaids() -> dict:
    """Load navaids database"""
    try:
        with open(NAVAIDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Navaids loaded: {len(data.get('vors', []))} VORs, {len(data.get('intersections', []))} intersections")
            return data
    except Exception as e:
        logger.warning(f"Navaids not available: {e}")
        return {"vors": [], "intersections": [], "airways": []}


def load_airports(filepath: str) -> list:
    """Load airports from JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            airports = data.get('airports', [])
            logger.info(f"{len(airports)} airports loaded")
            return airports
    except:
        logger.error("Airport loading error")
        return []


# ============================================================================
# FLIGHT PLAN GENERATION
# ============================================================================

def format_coordinate(value: float, is_lat: bool) -> str:
    """Format coordinate for PLN file"""
    if is_lat:
        direction = "N" if value >= 0 else "S"
    else:
        direction = "E" if value >= 0 else "W"
    return f"{direction}{abs(value):.6f}"


def parse_runway_ident(runway_ident: str) -> tuple:
    """Parse runway identifier"""
    import re
    if not runway_ident:
        return (1, "NONE")

    match = re.match(r'(\d+)([LRC])?', str(runway_ident).upper())
    if match:
        number = int(match.group(1))
        suffix = match.group(2)
        designator_map = {'L': 'LEFT', 'R': 'RIGHT', 'C': 'CENTER', None: 'NONE'}
        return (number, designator_map.get(suffix, 'NONE'))

    return (1, "NONE")


def calculate_optimal_altitude(distance: float, max_alt: int) -> int:
    """Calculate optimal cruise altitude"""
    if distance < 50:
        base_alt = 5000
    elif distance < 100:
        base_alt = 8000
    elif distance < 200:
        base_alt = 12000
    elif distance < 350:
        base_alt = 18000
    elif distance < 500:
        base_alt = 24000
    else:
        base_alt = 32000

    return min(base_alt, max_alt)


def calculate_waypoint_from_bearing(lat: float, lon: float, bearing: float, distance_nm: float) -> dict:
    """
    Calculate a waypoint at given bearing and distance from a position

    Args:
        lat, lon: Origin coordinates
        bearing: Bearing in degrees (true)
        distance_nm: Distance in nautical miles

    Returns:
        Dict with lat, lon
    """
    bearing_rad = math.radians(bearing)
    lat_rad = math.radians(lat)

    # Earth radius in NM
    R = 3440.065
    d = distance_nm / R

    new_lat = math.asin(math.sin(lat_rad) * math.cos(d) +
                        math.cos(lat_rad) * math.sin(d) * math.cos(bearing_rad))
    new_lon = math.radians(lon) + math.atan2(
        math.sin(bearing_rad) * math.sin(d) * math.cos(lat_rad),
        math.cos(d) - math.sin(lat_rad) * math.sin(new_lat)
    )

    return {
        'lat': math.degrees(new_lat),
        'lon': math.degrees(new_lon)
    }


def generate_approach_waypoint(arr_lat: float, arr_lon: float, runway_heading: float, distance_nm: float) -> dict:
    """Generate a waypoint on the extended runway centerline for approach"""
    approach_bearing = (runway_heading + 180) % 360
    return calculate_waypoint_from_bearing(arr_lat, arr_lon, approach_bearing, distance_nm)


def generate_departure_waypoints(dep_lat: float, dep_lon: float, runway_heading: float,
                                  first_enroute_lat: float = None, first_enroute_lon: float = None) -> list:
    """
    Generate departure procedure waypoints (SID-like)

    NOTE: In most cases, MSFS handles departure automatically based on runway selection.
    We only need departure waypoints for complex procedures.
    For now, return empty list - let MSFS handle departure naturally.
    """
    # MSFS handles departure from runway automatically
    # Adding waypoints near the runway causes routing issues (loops, turns back)
    # The first waypoint after departure should be the first enroute waypoint
    return []


def generate_flightplan_pln(departure: dict, arrival: dict, waypoints: list = None, aircraft_info: dict = None, config: dict = None) -> str:
    """Generate MSFS flight plan file with proper departure and approach procedures"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mission_{departure['icao']}_{arrival['icao']}_{timestamp}.pln"
    filepath = FLIGHTPLANS_DIR / filename

    # Extract runways
    dep_runway = departure.get('runway')
    arr_runway = arrival.get('runway')

    dep_rwy_num, dep_rwy_des = parse_runway_ident(dep_runway.get('ident') if dep_runway else None)
    arr_rwy_num, arr_rwy_des = parse_runway_ident(arr_runway.get('ident') if arr_runway else None)

    # Get runway headings from runway numbers (e.g., "06" -> 060°, "21" -> 210°)
    try:
        dep_runway_heading = int(dep_rwy_num) * 10 if dep_rwy_num else 0
    except (ValueError, TypeError):
        dep_runway_heading = 0

    try:
        arr_runway_heading = int(arr_rwy_num) * 10 if arr_rwy_num else 0
    except (ValueError, TypeError):
        arr_runway_heading = 0

    # Distance and altitude
    distance = calculate_distance_nm(departure['lat'], departure['lon'], arrival['lat'], arrival['lon'])
    category = aircraft_info.get("category", "light_piston") if aircraft_info else "light_piston"
    profile = AIRCRAFT_PROFILES.get(category, AIRCRAFT_PROFILES["light_piston"])
    cruise_alt = calculate_optimal_altitude(distance, profile["max_alt"])

    # === BUILD COMPLETE ROUTE ===
    departure_waypoints = []
    enroute_waypoints = []
    approach_waypoints = []

    # Check if same airport (pattern flight) or very short distance
    is_pattern_flight = departure['icao'] == arrival['icao'] or distance < 5

    if not is_pattern_flight and distance >= 5:
        # === 1. DEPARTURE PROCEDURE ===
        if dep_runway_heading > 0:
            # Calculate bearing to arrival to determine turn direction
            bearing_to_arrival = math.degrees(math.atan2(
                math.sin(math.radians(arrival['lon'] - departure['lon'])) * math.cos(math.radians(arrival['lat'])),
                math.cos(math.radians(departure['lat'])) * math.sin(math.radians(arrival['lat'])) -
                math.sin(math.radians(departure['lat'])) * math.cos(math.radians(arrival['lat'])) *
                math.cos(math.radians(arrival['lon'] - departure['lon']))
            )) % 360

            departure_waypoints = generate_departure_waypoints(
                departure['lat'], departure['lon'],
                dep_runway_heading,
                first_enroute_lat=arrival['lat'],
                first_enroute_lon=arrival['lon']
            )
            logger.info(f"Added departure procedure: CLMB, DEPT (RWY {dep_rwy_num}, heading {dep_runway_heading}°)")

        # === 2. ENROUTE WAYPOINTS ===
        # Try OpenAIP for real-world navaids
        if OPENAIP_AVAILABLE and distance >= 10:
            try:
                openaip_key = config.get('openaip_api_key', '') if config else ''
                openaip = get_openaip_client(api_key=openaip_key)
                enroute_waypoints = openaip.build_flight_route(
                    dep_lat=departure['lat'],
                    dep_lon=departure['lon'],
                    arr_lat=arrival['lat'],
                    arr_lon=arrival['lon'],
                    arr_runway_heading=arr_runway_heading,
                    cruise_alt=cruise_alt
                )
                if enroute_waypoints:
                    logger.info(f"OpenAIP route generated with {len(enroute_waypoints)} real waypoints")
            except Exception as e:
                logger.warning(f"OpenAIP route generation failed: {e}")
                enroute_waypoints = []

        # Fallback: generate synthetic enroute waypoints
        if not enroute_waypoints:
            logger.info("Using synthetic waypoint generation")
            max_offset = min(0.1, distance * 0.0008)
            num_wpts = min(5, max(1, int(distance / 100)))

            for i in range(1, num_wpts + 1):
                ratio = i / (num_wpts + 1)
                lat = departure['lat'] + (arrival['lat'] - departure['lat']) * ratio
                lon = departure['lon'] + (arrival['lon'] - departure['lon']) * ratio
                lat += random.uniform(-max_offset, max_offset)
                lon += random.uniform(-max_offset, max_offset)

                position = i / (num_wpts + 1)
                if position < 0.3:
                    alt = int(cruise_alt * 0.6)
                elif position > 0.7:
                    alt = int(cruise_alt * 0.5)
                else:
                    alt = cruise_alt

                enroute_waypoints.append({
                    "id": f"WPT{i:02d}",
                    "lat": lat,
                    "lon": lon,
                    "alt": alt
                })

        # === 3. APPROACH PROCEDURE ===
        # For MSFS 2024, we do NOT add synthetic approach waypoints
        # MSFS will use its built-in navdata for STAR and approach procedures
        # The user can select a STAR via the EFB "Add Arrival" option
        # Adding synthetic IAF/FAF waypoints interferes with MSFS procedure routing
        logger.info("No synthetic approach waypoints added - MSFS will use its navdata procedures")

    # === COMBINE ALL WAYPOINTS ===
    all_waypoints = departure_waypoints + enroute_waypoints + approach_waypoints

    # Build XML
    dep_coord = f"{format_coordinate(departure['lat'], True)},{format_coordinate(departure['lon'], False)},+000000.00"
    arr_coord = f"{format_coordinate(arrival['lat'], True)},{format_coordinate(arrival['lon'], False)},+000000.00"

    flight_type = "IFR" if cruise_alt >= 10000 else "VFR"

    waypoints_xml = ""
    for i, wpt in enumerate(all_waypoints):
        wpt_id = wpt.get('id', f"WPT{i+1:02d}")[:5].upper()
        wpt_lat = wpt.get('lat', 0)
        wpt_lon = wpt.get('lon', 0)
        wpt_alt = wpt.get('alt', 5000)
        wpt_coord = f"{format_coordinate(wpt_lat, True)},{format_coordinate(wpt_lon, False)},+{wpt_alt:06.2f}"

        waypoints_xml += f'''
        <ATCWaypoint id="{wpt_id}">
            <ATCWaypointType>User</ATCWaypointType>
            <WorldPosition>{wpt_coord}</WorldPosition>
            <SpeedMaxFP>-1</SpeedMaxFP>
        </ATCWaypoint>'''

    # MSFS 2024 PLN format with proper DepartureDetails, ArrivalDetails and ApproachDetails
    # This allows MSFS to properly route via its built-in navdata SID/STAR procedures
    # Reference: https://docs.flightsimulator.com/msfs2024/html/5_Content_Configuration/Mission_XML_Files/EFB_Flight_Plan_XML_Properties.htm

    # MSFS 2024 PLN Format:
    # - FPType must be IFR for procedures to work
    # - DepartureDetails specifies runway (SID is optional, MSFS will use navdata)
    # - ArrivalDetails specifies runway (STAR is optional, MSFS will use navdata)
    # - ApproachDetails specifies approach type - CRITICAL for proper routing
    # - NO arrival ATCWaypoint - MSFS uses ArrivalDetails to route to runway, not airport center

    # Determine approach type based on cruise altitude
    approach_type = "RNAV" if cruise_alt >= 3000 else "VISUAL"

    pln_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<SimBase.Document Type="AceXML" version="1,0">
    <Descr>AceXML Document</Descr>
    <FlightPlan.FlightPlan>
        <Title>{departure['icao']} to {arrival['icao']}</Title>
        <FPType>IFR</FPType>
        <RouteType>LowAlt</RouteType>
        <CruisingAlt>{cruise_alt}.000</CruisingAlt>
        <DepartureID>{departure['icao']}</DepartureID>
        <DepartureLLA>{dep_coord}</DepartureLLA>
        <DestinationID>{arrival['icao']}</DestinationID>
        <DestinationLLA>{arr_coord}</DestinationLLA>
        <Descr>{departure['name']} to {arrival['name']}</Descr>
        <DepartureName>{departure['name']}</DepartureName>
        <DestinationName>{arrival['name']}</DestinationName>
        <AppVersion>
            <AppVersionMajor>12</AppVersionMajor>
            <AppVersionBuild>282174</AppVersionBuild>
        </AppVersion>
        <DepartureDetails>
            <RunwayNumberFP>{dep_rwy_num}</RunwayNumberFP>
            <RunwayDesignatorFP>{dep_rwy_des}</RunwayDesignatorFP>
        </DepartureDetails>
        <ArrivalDetails>
            <RunwayNumberFP>{arr_rwy_num}</RunwayNumberFP>
            <RunwayDesignatorFP>{arr_rwy_des}</RunwayDesignatorFP>
        </ArrivalDetails>
        <ApproachDetails>
            <ApproachTypeFP>{approach_type}</ApproachTypeFP>
            <RunwayNumberFP>{arr_rwy_num}</RunwayNumberFP>
            <RunwayDesignatorFP>{arr_rwy_des}</RunwayDesignatorFP>
        </ApproachDetails>
        <ATCWaypoint id="{departure['icao']}">
            <ATCWaypointType>Airport</ATCWaypointType>
            <ICAO>
                <ICAOIdent>{departure['icao']}</ICAOIdent>
            </ICAO>
        </ATCWaypoint>{waypoints_xml}
    </FlightPlan.FlightPlan>
</SimBase.Document>'''

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(pln_content)
        logger.info(f"Flight plan generated: {filepath}")
        return str(filepath)
    except Exception as e:
        logger.error(f"PLN generation error: {e}")
        return None


# ============================================================================
# CONSTRAINTS
# ============================================================================

CONSTRAINTS = [
    {"name": "Max bank", "value": 35, "unit": "°", "type": "bank", "difficulty": "easy"},
    {"name": "Max bank", "value": 30, "unit": "°", "type": "bank", "difficulty": "normal"},
    {"name": "Max bank", "value": 25, "unit": "°", "type": "bank", "difficulty": "hard"},
    {"name": "Min altitude", "value": 1000, "unit": "ft", "type": "altitude_min", "difficulty": "easy"},
    {"name": "Min altitude", "value": 1500, "unit": "ft", "type": "altitude_min", "difficulty": "normal"},
    {"name": "Max altitude", "value": 10000, "unit": "ft", "type": "altitude_max", "difficulty": "easy"},
    {"name": "Max speed", "value": 280, "unit": "kts", "type": "speed_max", "difficulty": "easy"},
    {"name": "Max speed", "value": 250, "unit": "kts", "type": "speed_max", "difficulty": "normal"},
    {"name": "Max VS", "value": 1000, "unit": "fpm", "type": "vs_max", "difficulty": "easy"},
    {"name": "Max VS", "value": 700, "unit": "fpm", "type": "vs_max", "difficulty": "normal"},
]


def get_random_constraint() -> dict:
    weights = [3 if c['difficulty'] == 'easy' else 2 if c['difficulty'] == 'normal' else 1 for c in CONSTRAINTS]
    return random.choices(CONSTRAINTS, weights=weights, k=1)[0]


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class MissionGeneratorV2(ctk.CTk):
    """Main V2 Application"""

    def __init__(self):
        super().__init__()

        self.title("MSFS 2024 - Mission Generator V2")

        # Fullscreen 95% centered
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        self.win_width = int(self.screen_width * 0.95)
        self.win_height = int(self.screen_height * 0.95)
        x = (self.screen_width - self.win_width) // 2
        y = (self.screen_height - self.win_height) // 2
        self.geometry(f"{self.win_width}x{self.win_height}+{x}+{y}")
        self.resizable(True, True)
        self.minsize(1200, 800)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Configuration
        self.config = load_config()
        self.save_data = load_save()

        # State
        self.score = self.save_data.get('pilot', {}).get('bank_balance', 100.00)
        self.missions_completed = self.save_data.get('pilot', {}).get('missions_completed', 0)
        self.total_hours = self.save_data.get('pilot', {}).get('total_hours', 0)

        self.airports = load_airports(str(AIRPORTS_FILE))
        self.current_mission = None
        self.current_constraint = None
        self.current_flightplan = None
        self.mission_active = False
        self.was_on_ground = True
        self.penalty_cooldown = 0
        self.update_count = 0

        # Mission progress
        self.departure_lat = None
        self.departure_lon = None
        self.arrival_lat = None
        self.arrival_lon = None
        self.total_distance = 0
        self.mission_started = False
        self.mission_progress = 0.0

        # Payment tracking
        self.takeoff_time = None
        self.landing_time = None
        self.flight_time_hours = 0
        self.constraint_violations = 0
        self.max_vs_landing = 0
        self.had_overspeed = False
        self.is_night_flight = False
        self.is_weekend = False
        self.is_bad_weather = False

        # SimConnect
        self.sim_connected = False
        self.sim = None

        # Aircraft info
        self.aircraft_info = {
            "title": "Unknown",
            "type": "UNKNOWN",
            "model": "UNKNOWN",
            "engine_type": 0,
            "num_engines": 1,
            "cruise_speed": 120,
            "cruise_alt": 5000,
            "category": "light_piston"
        }

        # V2 Systems
        self._init_v2_systems()

        # Build UI
        self._build_ui()

        # Connect SimConnect
        self._connect_simconnect_async()

        # Start update loop
        self.after(UPDATE_INTERVAL, self._update_loop)

        # Window close handler
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _init_v2_systems(self):
        """Initialize V2 systems"""

        # Performance monitor
        if OPTIMIZATION_AVAILABLE:
            self.perf_monitor = get_performance_monitor()
            mode = self.config.get('performance_mode', 'balanced')
            self.perf_monitor.set_mode(mode)
            logger.info(f"Performance mode: {mode}")

        # Career system
        if CAREER_AVAILABLE:
            # Load pilot from save data (or create new if no save)
            self.pilot = load_pilot(self.save_data)
            # Sync total_hours with pilot profile
            self.total_hours = self.pilot.total_hours
            logger.info(f"Pilot loaded: {self.pilot.name}, License: {self.pilot.license.value}, Hours: {self.pilot.total_hours:.1f}h")
            self.companies = get_company_manager()
            self.logbook = get_logbook()
            self.progression = get_progression()
            logger.info("Career system initialized")

        # Game systems
        if SYSTEMS_AVAILABLE:
            self.fuel_manager = get_fuel_manager()
            self.maintenance = get_maintenance()
            self.failures = get_failure_manager()
            self.passengers = get_passenger_manager()
            self.challenges = get_challenge_manager()
            self.checkride = get_checkride_manager()
            logger.info("Game systems initialized")

        # Copilot
        if COPILOT_AVAILABLE:
            self.phase_detector = get_phase_detector()
            self.callouts = get_callout_manager()
            self.error_detector = get_error_detector()
            self.checklists = get_checklist_manager()
            self.atc = get_atc_simulator()
            self.copilot_llm = get_copilot_llm()
            self.voice = get_voice_system()
            self.debrief = get_debrief_manager()

            # Configure copilot
            if self.config.get('copilot_enabled', True):
                groq_key = self.config.get('groq_api_key', '')
                if groq_key:
                    self.copilot_llm.set_api_key(groq_key)
                    # Also pass API key to voice system for STT (Whisper)
                    self.voice.set_groq_api_key(groq_key)

                # Start voice system
                if self.config.get('voice_enabled', True):
                    self.voice.start()

            # Register phase change callback
            self.phase_detector.register_callback(self._on_phase_change)

            # Register callout callback to speak callouts
            self.callouts.register_callback(self._on_callout)

            # Register checklist callback to speak items
            self.checklists.register_callback(self._on_checklist_event)

            # Register STT callback to process voice commands
            self.voice.register_stt_callback(self._on_voice_command)

            logger.info("Copilot system initialized")

        # Joystick PTT (Push-to-Talk)
        self._init_joystick_ptt()

        # Flight recorder
        if UTILS_AVAILABLE:
            self.flight_recorder = get_flight_recorder()
            logger.info("Flight recorder initialized")

    def _build_ui(self):
        """Build the user interface with split layout"""

        # Main container with 2 columns (35% Career / 65% Mission)
        self.main_container = ctk.CTkFrame(self, corner_radius=0)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.main_container.grid_columnconfigure(0, weight=35)
        self.main_container.grid_columnconfigure(1, weight=65)
        self.main_container.grid_rowconfigure(0, weight=1)

        # === LEFT PANEL: CAREER ===
        self._build_career_panel()

        # === RIGHT PANEL: MISSION ===
        self.mission_panel = ctk.CTkFrame(self.main_container, corner_radius=10)
        self.mission_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)

        # Scrollable content for mission panel
        self.main_frame = ctk.CTkScrollableFrame(self.mission_panel, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # === HEADER ===
        self.header_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.header_frame.pack(fill="x", pady=(0, 10))

        self.score_label = ctk.CTkLabel(
            self.header_frame,
            text=f"BANK ACCOUNT: {self.score:.2f} EUR",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#00FF00" if self.score >= 0 else "#FF4444"
        )
        self.score_label.pack(pady=(10, 5))

        self.stats_label = ctk.CTkLabel(
            self.header_frame,
            text=f"Missions: {self.missions_completed} | Hours: {self.total_hours:.1f}h",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        self.stats_label.pack(pady=(0, 10))

        # === STATUS ===
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="Connecting to simulator...",
            font=ctk.CTkFont(size=13),
            text_color="#FFA500"
        )
        self.status_label.pack(pady=(0, 10))

        # === COPILOT STATUS ===
        if COPILOT_AVAILABLE:
            self.copilot_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color="#1a2a1a")
            self.copilot_frame.pack(fill="x", pady=(0, 10))

            self.copilot_title = ctk.CTkLabel(
                self.copilot_frame, text="AI COPILOT",
                font=ctk.CTkFont(size=12, weight="bold"), text_color="#00AA00"
            )
            self.copilot_title.pack(pady=(8, 3))

            self.copilot_status = ctk.CTkLabel(
                self.copilot_frame, text="Ready | Phase: PARKED",
                font=ctk.CTkFont(size=11), text_color="#88AA88"
            )
            self.copilot_status.pack(pady=(0, 5))

            # Copilot input field
            self.copilot_input_frame = ctk.CTkFrame(self.copilot_frame, fg_color="transparent")
            self.copilot_input_frame.pack(fill="x", padx=10, pady=(0, 5))

            self.copilot_entry = ctk.CTkEntry(
                self.copilot_input_frame,
                placeholder_text="Posez une question au copilote...",
                height=32
            )
            self.copilot_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
            self.copilot_entry.bind("<Return>", lambda e: self._ask_copilot())

            self.copilot_ask_btn = ctk.CTkButton(
                self.copilot_input_frame, text="Ask",
                width=60, height=32,
                fg_color="#2E7D32", hover_color="#1B5E20",
                command=self._ask_copilot
            )
            self.copilot_ask_btn.pack(side="left", padx=(0, 5))

            # Mic button for voice input
            self.copilot_mic_btn = ctk.CTkButton(
                self.copilot_input_frame, text="🎤 Mic",
                width=70, height=32,
                fg_color="#1565C0", hover_color="#0D47A1",
                command=self._listen_and_ask_copilot
            )
            self.copilot_mic_btn.pack(side="left")

            # Copilot response area
            self.copilot_response = ctk.CTkLabel(
                self.copilot_frame, text="",
                font=ctk.CTkFont(size=11), text_color="#AAFFAA",
                wraplength=350, justify="left"
            )
            self.copilot_response.pack(pady=(0, 5), padx=10)

            # Microphone indicator
            self.mic_frame = ctk.CTkFrame(self.copilot_frame, fg_color="transparent")
            self.mic_frame.pack(fill="x", padx=10, pady=(0, 8))

            self.mic_icon = ctk.CTkLabel(
                self.mic_frame, text="🎤",
                font=ctk.CTkFont(size=14)
            )
            self.mic_icon.pack(side="left", padx=(0, 5))

            # Microphone dropdown
            self.mic_devices = []  # List of (index, name)
            self.mic_dropdown = ctk.CTkComboBox(
                self.mic_frame,
                values=["Detecting..."],
                width=200,
                height=24,
                font=ctk.CTkFont(size=10),
                command=self._on_mic_selected
            )
            self.mic_dropdown.pack(side="left", padx=(0, 10))

            # Test button to check mic level
            self.mic_test_btn = ctk.CTkButton(
                self.mic_frame,
                text="Test",
                width=50,
                height=24,
                font=ctk.CTkFont(size=10),
                fg_color="#444444",
                hover_color="#555555",
                command=self._test_microphone
            )
            self.mic_test_btn.pack(side="left", padx=(0, 5))

            # Simple level indicator (static, updated on test)
            self.mic_level_label = ctk.CTkLabel(
                self.mic_frame,
                text="",
                font=ctk.CTkFont(size=10),
                text_color="#888888"
            )
            self.mic_level_label.pack(side="left")

            # Checklist controls
            self.checklist_frame = ctk.CTkFrame(self.copilot_frame, fg_color="transparent")
            self.checklist_frame.pack(fill="x", padx=10, pady=(0, 8))

            self.checklist_label = ctk.CTkLabel(
                self.checklist_frame, text="Checklist:",
                font=ctk.CTkFont(size=11), text_color="#AAFFAA"
            )
            self.checklist_label.pack(side="left", padx=(0, 5))

            self.checklist_dropdown = ctk.CTkComboBox(
                self.checklist_frame,
                values=["Before Start", "Before Takeoff", "Approach", "Before Landing", "After Landing", "Shutdown"],
                width=130,
                height=24,
                font=ctk.CTkFont(size=10)
            )
            self.checklist_dropdown.pack(side="left", padx=(0, 5))
            self.checklist_dropdown.set("Before Takeoff")

            self.checklist_start_btn = ctk.CTkButton(
                self.checklist_frame,
                text="Start",
                width=45,
                height=24,
                font=ctk.CTkFont(size=10),
                fg_color="#2E5731",
                hover_color="#3E7D42",
                command=self._on_checklist_start
            )
            self.checklist_start_btn.pack(side="left", padx=(0, 3))

            self.checklist_check_btn = ctk.CTkButton(
                self.checklist_frame,
                text="Check",
                width=45,
                height=24,
                font=ctk.CTkFont(size=10),
                fg_color="#444444",
                hover_color="#555555",
                command=self.check_checklist_item
            )
            self.checklist_check_btn.pack(side="left", padx=(0, 3))

            self.checklist_skip_btn = ctk.CTkButton(
                self.checklist_frame,
                text="Skip",
                width=40,
                height=24,
                font=ctk.CTkFont(size=10),
                fg_color="#444444",
                hover_color="#555555",
                command=self.skip_checklist_item
            )
            self.checklist_skip_btn.pack(side="left", padx=(0, 3))

            # Auto-check button - runs checklist automatically using SimConnect data
            self.checklist_auto_btn = ctk.CTkButton(
                self.checklist_frame,
                text="Auto",
                width=40,
                height=24,
                font=ctk.CTkFont(size=10),
                fg_color="#1E4A5F",
                hover_color="#2E6A8F",
                command=self._run_auto_checklist
            )
            self.checklist_auto_btn.pack(side="left")

            # Initialize mic list
            self.after(500, self._init_microphones)

        # === MISSION BUTTON ===
        self.generate_btn = ctk.CTkButton(
            self.main_frame,
            text="GENERATE MISSION",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            fg_color="#1E5631",
            hover_color="#2E7D32",
            command=self._generate_mission
        )
        self.generate_btn.pack(pady=8, padx=40, fill="x")

        # === MISSION INFO ===
        self.mission_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.mission_frame.pack(pady=8, padx=15, fill="x")

        self.mission_title = ctk.CTkLabel(
            self.mission_frame, text="MISSION",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#4A90D9"
        )
        self.mission_title.pack(pady=(8, 3))

        self.mission_text = ctk.CTkLabel(
            self.mission_frame,
            text="Press 'GENERATE MISSION' to start",
            font=ctk.CTkFont(size=13), wraplength=700
        )
        self.mission_text.pack(pady=(0, 8), padx=10)

        # === MISSION DISTANCE SETTINGS ===
        self.distance_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.distance_frame.pack(pady=8, padx=15, fill="x")

        self.distance_title = ctk.CTkLabel(
            self.distance_frame, text="DISTANCE MISSION (nm)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#4A90D9"
        )
        self.distance_title.pack(pady=(8, 5))

        # Min distance row
        self.dist_min_row = ctk.CTkFrame(self.distance_frame, fg_color="transparent")
        self.dist_min_row.pack(fill="x", padx=10, pady=(0, 4))

        self.dist_min_label = ctk.CTkLabel(
            self.dist_min_row, text="Min:",
            font=ctk.CTkFont(size=11), width=35
        )
        self.dist_min_label.pack(side="left", padx=(0, 5))

        self.dist_min_var = ctk.IntVar(value=self.config.get('mission_distance_min', 50))
        self.dist_min_slider = ctk.CTkSlider(
            self.dist_min_row, from_=10, to=1000, number_of_steps=99,
            variable=self.dist_min_var, command=self._on_dist_min_changed
        )
        self.dist_min_slider.pack(side="left", fill="x", expand=True, padx=5)

        self.dist_min_value = ctk.CTkLabel(
            self.dist_min_row, text=f"{self.dist_min_var.get()} nm",
            font=ctk.CTkFont(size=11, weight="bold"), width=70
        )
        self.dist_min_value.pack(side="left")

        # Max distance row
        self.dist_max_row = ctk.CTkFrame(self.distance_frame, fg_color="transparent")
        self.dist_max_row.pack(fill="x", padx=10, pady=(0, 8))

        self.dist_max_label = ctk.CTkLabel(
            self.dist_max_row, text="Max:",
            font=ctk.CTkFont(size=11), width=35
        )
        self.dist_max_label.pack(side="left", padx=(0, 5))

        self.dist_max_var = ctk.IntVar(value=self.config.get('mission_distance_max', 500))
        self.dist_max_slider = ctk.CTkSlider(
            self.dist_max_row, from_=20, to=3000, number_of_steps=149,
            variable=self.dist_max_var, command=self._on_dist_max_changed
        )
        self.dist_max_slider.pack(side="left", fill="x", expand=True, padx=5)

        self.dist_max_value = ctk.CTkLabel(
            self.dist_max_row, text=f"{self.dist_max_var.get()} nm",
            font=ctk.CTkFont(size=11, weight="bold"), width=70
        )
        self.dist_max_value.pack(side="left")

        # Info label showing effective range after aircraft constraints
        self.dist_info_label = ctk.CTkLabel(
            self.distance_frame,
            text="(sera ajuste selon les capacites de l'avion detecte)",
            font=ctk.CTkFont(size=10), text_color="#666666"
        )
        self.dist_info_label.pack(pady=(0, 8))

        # === PROGRESS BAR ===
        self.progress_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color="#1a1a2e")
        self.progress_frame.pack(pady=8, padx=15, fill="x")

        self.progress_title = ctk.CTkLabel(
            self.progress_frame, text="MISSION PROGRESS",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#4A90D9"
        )
        self.progress_title.pack(pady=(8, 3))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame, width=500, height=20,
            corner_radius=10, fg_color="#2d2d44", progress_color="#00AA00"
        )
        self.progress_bar.pack(pady=(5, 5), padx=20)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="0% - Awaiting mission",
            font=ctk.CTkFont(size=12), text_color="#AAAAAA"
        )
        self.progress_label.pack(pady=(0, 8))

        # === CONSTRAINT ===
        self.constraint_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color="#4A1010")
        self.constraint_frame.pack(pady=8, padx=15, fill="x")

        self.constraint_title = ctk.CTkLabel(
            self.constraint_frame, text="CONSTRAINT",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#FF4444"
        )
        self.constraint_title.pack(pady=(8, 3))

        self.constraint_text = ctk.CTkLabel(
            self.constraint_frame, text="No active constraint",
            font=ctk.CTkFont(size=13), text_color="#FF6666"
        )
        self.constraint_text.pack(pady=(0, 8))

        # === AIRCRAFT DATA ===
        self.data_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.data_frame.pack(pady=8, padx=15, fill="x")

        self.data_title = ctk.CTkLabel(
            self.data_frame, text="AIRCRAFT DATA",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888"
        )
        self.data_title.pack(pady=(8, 3))

        self.aircraft_label = ctk.CTkLabel(
            self.data_frame, text="Aircraft: Waiting for connection...",
            font=ctk.CTkFont(size=11), text_color="#4A90D9"
        )
        self.aircraft_label.pack(pady=(0, 3))

        self.data_text = ctk.CTkLabel(
            self.data_frame, text="Alt: -- | Bank: -- | VS: -- | Speed: --",
            font=ctk.CTkFont(size=12), text_color="#AAAAAA"
        )
        self.data_text.pack(pady=(0, 3))

        self.debug_text = ctk.CTkLabel(
            self.data_frame, text="",
            font=ctk.CTkFont(size=10), text_color="#666666"
        )
        self.debug_text.pack(pady=(0, 8))

        # === V2 SYSTEMS PANEL ===
        if SYSTEMS_AVAILABLE or CAREER_AVAILABLE:
            self.systems_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
            self.systems_frame.pack(pady=8, padx=15, fill="x")

            self.systems_title = ctk.CTkLabel(
                self.systems_frame, text="V2 SYSTEMS",
                font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888"
            )
            self.systems_title.pack(pady=(8, 3))

            self.systems_text = ctk.CTkLabel(
                self.systems_frame,
                text="Fuel: -- | Wear: -- | Passengers: --",
                font=ctk.CTkFont(size=11), text_color="#AAAAAA"
            )
            self.systems_text.pack(pady=(0, 8))

        # === PLN FOLDER ===
        self.pln_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.pln_frame.pack(pady=8, padx=15, fill="x")

        self.pln_title = ctk.CTkLabel(
            self.pln_frame, text="FLIGHT PLAN FOLDER (.PLN)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888"
        )
        self.pln_title.pack(pady=(8, 5))

        self.pln_path_frame = ctk.CTkFrame(self.pln_frame, fg_color="transparent")
        self.pln_path_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.pln_path_entry = ctk.CTkEntry(
            self.pln_path_frame, placeholder_text="PLN folder path...",
            font=ctk.CTkFont(size=11), height=30
        )
        self.pln_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.pln_path_entry.insert(0, self.config.get('pln_destination_folder', ''))

        self.pln_browse_btn = ctk.CTkButton(
            self.pln_path_frame, text="Browse",
            font=ctk.CTkFont(size=11), width=80, height=30,
            command=self._browse_pln_folder
        )
        self.pln_browse_btn.pack(side="left", padx=(0, 5))

        self.pln_open_btn = ctk.CTkButton(
            self.pln_path_frame, text="Open",
            font=ctk.CTkFont(size=11), width=60, height=30,
            fg_color="#2B4B6F", command=self._open_pln_folder
        )
        self.pln_open_btn.pack(side="left")

        self.auto_copy_var = ctk.BooleanVar(value=self.config.get('auto_copy_pln', False))
        self.auto_copy_check = ctk.CTkCheckBox(
            self.pln_frame, text="Auto-copy PLN to this folder",
            variable=self.auto_copy_var, font=ctk.CTkFont(size=11),
            command=self._on_auto_copy_changed
        )
        self.auto_copy_check.pack(pady=(0, 8))

        # === GROQ API ===
        self.groq_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.groq_frame.pack(pady=8, padx=15, fill="x")

        self.groq_title = ctk.CTkLabel(
            self.groq_frame, text="GROQ API (AI Routes & Copilot)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888"
        )
        self.groq_title.pack(pady=(8, 5))

        self.groq_entry = ctk.CTkEntry(
            self.groq_frame, placeholder_text="Groq API Key (optional)...",
            font=ctk.CTkFont(size=11), height=30, show="*"
        )
        self.groq_entry.pack(fill="x", padx=10, pady=(0, 4))
        if self.config.get('groq_api_key'):
            self.groq_entry.insert(0, self.config['groq_api_key'])

        # OpenAIP API Key (for real navaids in flight plans)
        self.openaip_label = ctk.CTkLabel(
            self.groq_frame, text="OpenAIP (Real Navaids)",
            font=ctk.CTkFont(size=10), text_color="#666666"
        )
        self.openaip_label.pack(pady=(4, 2))

        self.openaip_entry = ctk.CTkEntry(
            self.groq_frame, placeholder_text="OpenAIP API Key (free at openaip.net)...",
            font=ctk.CTkFont(size=11), height=28, show="*"
        )
        self.openaip_entry.pack(fill="x", padx=10, pady=(0, 8))
        if self.config.get('openaip_api_key'):
            self.openaip_entry.insert(0, self.config['openaip_api_key'])

        # === V2 OPTIONS ===
        self.options_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.options_frame.pack(pady=8, padx=15, fill="x")

        self.options_title = ctk.CTkLabel(
            self.options_frame, text="V2 OPTIONS",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888"
        )
        self.options_title.pack(pady=(8, 5))

        self.options_inner = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.options_inner.pack(fill="x", padx=10, pady=(0, 8))

        self.copilot_var = ctk.BooleanVar(value=self.config.get('copilot_enabled', True))
        self.copilot_check = ctk.CTkCheckBox(
            self.options_inner, text="AI Copilot", variable=self.copilot_var,
            font=ctk.CTkFont(size=11)
        )
        self.copilot_check.pack(side="left", padx=10)

        self.voice_var = ctk.BooleanVar(value=self.config.get('voice_enabled', True))
        self.voice_check = ctk.CTkCheckBox(
            self.options_inner, text="Voice", variable=self.voice_var,
            font=ctk.CTkFont(size=11)
        )
        self.voice_check.pack(side="left", padx=10)

        self.career_var = ctk.BooleanVar(value=self.config.get('career_mode', True))
        self.career_check = ctk.CTkCheckBox(
            self.options_inner, text="Career Mode", variable=self.career_var,
            font=ctk.CTkFont(size=11)
        )
        self.career_check.pack(side="left", padx=10)

        self.fuel_var = ctk.BooleanVar(value=self.config.get('fuel_management', True))
        self.fuel_check = ctk.CTkCheckBox(
            self.options_inner, text="Fuel Mgmt", variable=self.fuel_var,
            font=ctk.CTkFont(size=11)
        )
        self.fuel_check.pack(side="left", padx=10)

        # === V2 OPTIONS ROW 2 ===
        self.options_inner2 = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.options_inner2.pack(fill="x", padx=10, pady=(0, 8))

        self.relaxed_var = ctk.BooleanVar(value=self.config.get('relaxed_mode', False))
        self.relaxed_check = ctk.CTkCheckBox(
            self.options_inner2, text="Relaxed Mode", variable=self.relaxed_var,
            font=ctk.CTkFont(size=11), command=self._on_relaxed_mode_changed
        )
        self.relaxed_check.pack(side="left", padx=10)

        self.failures_var = ctk.BooleanVar(value=self.config.get('failures', {}).get('enabled', False))
        self.failures_check = ctk.CTkCheckBox(
            self.options_inner2, text="Failures", variable=self.failures_var,
            font=ctk.CTkFont(size=11)
        )
        self.failures_check.pack(side="left", padx=10)

        self.constraints_var = ctk.BooleanVar(value=self.config.get('constraints', {}).get('enabled', True))
        self.constraints_check = ctk.CTkCheckBox(
            self.options_inner2, text="Constraints", variable=self.constraints_var,
            font=ctk.CTkFont(size=11)
        )
        self.constraints_check.pack(side="left", padx=10)

        # === CHALLENGE BUTTON ===
        self.challenge_btn = ctk.CTkButton(
            self.options_inner2, text="Landing Challenge",
            font=ctk.CTkFont(size=10), height=24, width=110,
            fg_color="#6B4B2B", hover_color="#7B5B3B",
            command=self._start_landing_challenge
        )
        self.challenge_btn.pack(side="left", padx=10)

        # === PATTERN TRAINING BUTTON ===
        self.pattern_btn = ctk.CTkButton(
            self.options_inner2, text="Tour de Piste",
            font=ctk.CTkFont(size=10), height=24, width=100,
            fg_color="#2B6B4B", hover_color="#3B7B5B",
            command=self._start_pattern_training
        )
        self.pattern_btn.pack(side="left", padx=10)

        # Pattern training state
        self.pattern_trainer = None
        self.pattern_training_active = False

        # === BOTTOM BUTTONS ===
        self.bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.bottom_frame.pack(pady=(10, 0), fill="x")

        self.reset_btn = ctk.CTkButton(
            self.bottom_frame, text="Reset Score",
            font=ctk.CTkFont(size=11), height=28,
            fg_color="#555555", hover_color="#666666",
            command=self._reset_score
        )
        self.reset_btn.pack(side="right", padx=5)

        self.save_config_btn = ctk.CTkButton(
            self.bottom_frame, text="Save Config",
            font=ctk.CTkFont(size=11), height=28,
            fg_color="#4B6F2B", hover_color="#5B7F3B",
            command=self._save_config
        )
        self.save_config_btn.pack(side="right", padx=5)

        if COPILOT_AVAILABLE:
            self.speak_btn = ctk.CTkButton(
                self.bottom_frame, text="Test Voice",
                font=ctk.CTkFont(size=11), height=28,
                fg_color="#2B4B6F", hover_color="#3B5B7F",
                command=self._test_voice
            )
            self.speak_btn.pack(side="left", padx=5)

            # PTT Configuration button
            self.ptt_btn = ctk.CTkButton(
                self.bottom_frame, text="Config PTT",
                font=ctk.CTkFont(size=11), height=28,
                fg_color="#6B4B2B", hover_color="#7B5B3B",
                command=self._configure_ptt_button
            )
            self.ptt_btn.pack(side="left", padx=5)

    def _build_career_panel(self):
        """Build the Career Panel (left side, 35%)"""
        self.career_panel = ctk.CTkFrame(self.main_container, corner_radius=10, fg_color=COLORS['bg_dark'])
        self.career_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)

        # Career Title
        career_title = ctk.CTkLabel(
            self.career_panel, text="CARRIERE PILOTE",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=COLORS['accent']
        )
        career_title.pack(pady=(15, 10))

        # Scrollable content
        self.career_scroll = ctk.CTkScrollableFrame(self.career_panel, fg_color="transparent")
        self.career_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 1. License Tree Widget
        self._build_license_tree_widget()

        # 2. Company Widget
        self._build_company_widget()

        # 3. Aircraft Categories Widget
        self._build_aircraft_categories_widget()

        # 4. Stats Widget
        self._build_stats_widget()

    def _build_license_tree_widget(self):
        """License progression tree: STUDENT -> PPL -> CPL -> ATPL"""
        license_frame = ctk.CTkFrame(self.career_scroll, corner_radius=10, fg_color=COLORS['bg_panel'])
        license_frame.pack(fill="x", pady=(0, 10))

        title = ctk.CTkLabel(
            license_frame, text="PROGRESSION LICENCE",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS['accent']
        )
        title.pack(pady=(10, 5))

        # Get current license and progress
        current_license = "STUDENT"
        progress_data = {}
        if CAREER_AVAILABLE and hasattr(self, 'pilot') and self.pilot:
            current_license = self.pilot.license.value.upper()
            progress_data = self.pilot.get_next_license_progress()

        licenses = ['STUDENT', 'PPL', 'CPL', 'ATPL']
        license_hours = {'STUDENT': 0, 'PPL': 40, 'CPL': 200, 'ATPL': 1500}

        self.license_nodes = {}
        self.license_progress_bars = {}

        for i, lic in enumerate(licenses):
            lic_idx = licenses.index(lic)
            current_idx = licenses.index(current_license) if current_license in licenses else 0

            if lic_idx < current_idx:
                node_color = LICENSE_COLORS[lic]
                text_color = node_color
                is_active = False
            elif lic_idx == current_idx:
                node_color = LICENSE_COLORS[lic]
                text_color = "#FFFFFF"
                is_active = True
            else:
                node_color = "#444444"
                text_color = "#666666"
                is_active = False

            # License node
            node_frame = ctk.CTkFrame(license_frame, fg_color="transparent")
            node_frame.pack(pady=3)

            node_size = 50 if is_active else 40
            node = ctk.CTkButton(
                node_frame, text=lic,
                width=node_size, height=node_size,
                corner_radius=node_size // 2,
                fg_color=node_color if is_active else "transparent",
                border_color=node_color,
                border_width=2,
                text_color=text_color,
                font=ctk.CTkFont(size=10 if not is_active else 12, weight="bold"),
                hover=False
            )
            node.pack()
            self.license_nodes[lic] = node

            # Progress bar between licenses
            if i < len(licenses) - 1:
                next_lic = licenses[i + 1]
                next_hours = license_hours[next_lic]

                progress_pct = 0
                if CAREER_AVAILABLE and hasattr(self, 'pilot') and self.pilot:
                    if lic_idx < current_idx:
                        progress_pct = 1.0
                    elif lic_idx == current_idx and progress_data:
                        progress_pct = progress_data.get('hours_progress', 0) / 100

                bar_frame = ctk.CTkFrame(license_frame, fg_color="transparent")
                bar_frame.pack(pady=2)

                connector = ctk.CTkLabel(bar_frame, text="|", text_color="#444444")
                connector.pack()

                progress_bar = ctk.CTkProgressBar(
                    bar_frame, width=80, height=10,
                    corner_radius=5, fg_color="#333333",
                    progress_color=LICENSE_COLORS.get(next_lic, "#4A90D9")
                )
                progress_bar.set(progress_pct)
                progress_bar.pack(pady=2)
                self.license_progress_bars[lic] = progress_bar

                # Hours label
                pilot_hours = self.pilot.total_hours if CAREER_AVAILABLE and hasattr(self, 'pilot') and self.pilot else 0
                if lic_idx == current_idx:
                    hours_text = f"{pilot_hours:.0f}h / {next_hours}h"
                elif lic_idx < current_idx:
                    hours_text = f"{next_hours}h"
                else:
                    hours_text = f"0h / {next_hours}h"

                hours_label = ctk.CTkLabel(bar_frame, text=hours_text, font=ctk.CTkFont(size=9), text_color="#888888")
                hours_label.pack()

                connector2 = ctk.CTkLabel(bar_frame, text="|", text_color="#444444")
                connector2.pack()

        ctk.CTkLabel(license_frame, text="", height=5).pack()

    def _build_company_widget(self):
        """Company with reputation"""
        company_frame = ctk.CTkFrame(self.career_scroll, corner_radius=10, fg_color=COLORS['bg_panel'])
        company_frame.pack(fill="x", pady=(0, 10))

        title = ctk.CTkLabel(
            company_frame, text="COMPAGNIE ACTUELLE",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS['accent']
        )
        title.pack(pady=(10, 5))

        # Get company info
        company_name = "Freelance"
        reputation = 50
        rep_level = "NEUTRAL"
        multiplier = 1.0

        if CAREER_AVAILABLE and hasattr(self, 'companies') and self.companies:
            current_company = self.companies.select_random_company()
            if current_company:
                company_name = current_company.name
                reputation = current_company.reputation
                rep_level = current_company.reputation_level.value.upper()
                multiplier = current_company.pay_multiplier
                self.current_company = current_company
            else:
                self.current_company = None
        else:
            self.current_company = None

        # Company name
        self.company_name_label = ctk.CTkLabel(
            company_frame, text=company_name,
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#FFFFFF"
        )
        self.company_name_label.pack(pady=(5, 3))

        # Reputation bar
        bar_frame = ctk.CTkFrame(company_frame, fg_color="transparent")
        bar_frame.pack(fill="x", padx=20, pady=5)

        self.reputation_bar = ctk.CTkProgressBar(
            bar_frame, height=15, corner_radius=7,
            fg_color="#333333",
            progress_color=REPUTATION_COLORS.get(rep_level, "#888888")
        )
        self.reputation_bar.set(reputation / 100)
        self.reputation_bar.pack(fill="x")

        # Reputation level text
        self.reputation_label = ctk.CTkLabel(
            company_frame, text=f"{rep_level} ({reputation:.0f}/100)",
            font=ctk.CTkFont(size=11), text_color=REPUTATION_COLORS.get(rep_level, "#888888")
        )
        self.reputation_label.pack(pady=(2, 5))

        # Pay multiplier
        mult_color = COLORS['positive'] if multiplier >= 1.0 else COLORS['negative']
        self.multiplier_label = ctk.CTkLabel(
            company_frame, text=f"Multiplicateur: x{multiplier:.2f}",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=mult_color
        )
        self.multiplier_label.pack(pady=(0, 10))

    def _build_aircraft_categories_widget(self):
        """4x2 grid of aircraft categories"""
        categories_frame = ctk.CTkFrame(self.career_scroll, corner_radius=10, fg_color=COLORS['bg_panel'])
        categories_frame.pack(fill="x", pady=(0, 10))

        title = ctk.CTkLabel(
            categories_frame, text="CATEGORIES AVIONS",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS['accent']
        )
        title.pack(pady=(10, 5))

        # Get available categories
        available = ['light_piston']
        if CAREER_AVAILABLE and hasattr(self, 'pilot') and self.pilot:
            available = self.pilot.get_available_categories()

        current_category = self.aircraft_info.get('category', 'light_piston')

        categories = [
            'light_piston', 'twin_piston', 'single_turboprop', 'turboprop',
            'light_jet', 'jet', 'heavy_jet', 'helicopter'
        ]

        grid_frame = ctk.CTkFrame(categories_frame, fg_color="transparent")
        grid_frame.pack(padx=10, pady=(5, 10))

        self.category_badges = {}
        for i, cat in enumerate(categories):
            row = i // 4
            col = i % 4

            is_unlocked = cat in available
            is_current = cat == current_category

            if is_current and is_unlocked:
                bg_color = COLORS['positive_alt']
                border_color = COLORS['positive']
                text_color = "#FFFFFF"
            elif is_unlocked:
                bg_color = "#3a3a4a"
                border_color = "#555555"
                text_color = "#CCCCCC"
            else:
                bg_color = "#1a1a1a"
                border_color = "#333333"
                text_color = "#555555"

            display_name = CATEGORY_DISPLAY_NAMES.get(cat, cat)

            badge = ctk.CTkButton(
                grid_frame, text=display_name if is_unlocked else "🔒",
                width=70, height=35,
                corner_radius=5,
                fg_color=bg_color,
                border_color=border_color,
                border_width=2,
                text_color=text_color,
                font=ctk.CTkFont(size=9),
                hover=False
            )
            badge.grid(row=row, column=col, padx=3, pady=3)
            self.category_badges[cat] = badge

    def _build_stats_widget(self):
        """Pilot statistics widget"""
        stats_frame = ctk.CTkFrame(self.career_scroll, corner_radius=10, fg_color=COLORS['bg_panel'])
        stats_frame.pack(fill="x", pady=(0, 10))

        title = ctk.CTkLabel(
            stats_frame, text="STATISTIQUES",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS['accent']
        )
        title.pack(pady=(10, 5))

        # Get stats
        total_hours = self.total_hours
        total_landings = 0
        perfect_landings = 0
        total_distance = 0
        hours_by_cat = {}

        if CAREER_AVAILABLE and hasattr(self, 'pilot') and self.pilot:
            total_hours = self.pilot.total_hours
            total_landings = self.pilot.total_landings
            perfect_landings = self.pilot.perfect_landings
            total_distance = self.pilot.total_distance_nm
            hours_by_cat = self.pilot.hours_by_category

        # Total hours (big, green)
        self.total_hours_label = ctk.CTkLabel(
            stats_frame, text=f"{total_hours:.1f}h",
            font=ctk.CTkFont(size=32, weight="bold"), text_color=COLORS['positive']
        )
        self.total_hours_label.pack(pady=(5, 0))

        ctk.CTkLabel(
            stats_frame, text="Heures de vol totales",
            font=ctk.CTkFont(size=10), text_color=COLORS['text_dim']
        ).pack(pady=(0, 10))

        # Per-category hours bars
        bars_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        bars_frame.pack(fill="x", padx=15, pady=(0, 10))

        categories = ['light_piston', 'twin_piston', 'turboprop', 'jet']
        max_hours = max(hours_by_cat.values()) if hours_by_cat and max(hours_by_cat.values()) > 0 else 1

        self.category_hour_bars = {}
        for cat in categories:
            cat_hours = hours_by_cat.get(cat, 0)
            display_name = CATEGORY_DISPLAY_NAMES.get(cat, cat)[:12]

            row_frame = ctk.CTkFrame(bars_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row_frame, text=display_name, width=80,
                font=ctk.CTkFont(size=9), text_color=COLORS['text_dim'], anchor="w"
            ).pack(side="left")

            bar = ctk.CTkProgressBar(
                row_frame, height=8, width=100,
                corner_radius=4, fg_color="#333333",
                progress_color=COLORS['accent']
            )
            bar.set(cat_hours / max_hours if max_hours > 0 else 0)
            bar.pack(side="left", padx=5)
            self.category_hour_bars[cat] = bar

            ctk.CTkLabel(
                row_frame, text=f"{cat_hours:.0f}h",
                font=ctk.CTkFont(size=9), text_color=COLORS['text']
            ).pack(side="left")

        # Other stats row
        other_stats = ctk.CTkFrame(stats_frame, fg_color="transparent")
        other_stats.pack(fill="x", padx=15, pady=(5, 10))

        # Landings
        land_frame = ctk.CTkFrame(other_stats, fg_color="transparent")
        land_frame.pack(side="left", expand=True)
        self.landings_label = ctk.CTkLabel(
            land_frame, text=f"{total_landings}",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#FFFFFF"
        )
        self.landings_label.pack()
        ctk.CTkLabel(land_frame, text="Atterrissages", font=ctk.CTkFont(size=9), text_color=COLORS['text_dim']).pack()

        # Perfect landings
        perfect_frame = ctk.CTkFrame(other_stats, fg_color="transparent")
        perfect_frame.pack(side="left", expand=True)
        self.perfect_label = ctk.CTkLabel(
            perfect_frame, text=f"{perfect_landings}",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=COLORS['positive']
        )
        self.perfect_label.pack()
        ctk.CTkLabel(perfect_frame, text="Parfaits", font=ctk.CTkFont(size=9), text_color=COLORS['text_dim']).pack()

        # Distance
        dist_frame = ctk.CTkFrame(other_stats, fg_color="transparent")
        dist_frame.pack(side="left", expand=True)
        self.distance_label = ctk.CTkLabel(
            dist_frame, text=f"{total_distance:.0f}",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=COLORS['accent']
        )
        self.distance_label.pack()
        ctk.CTkLabel(dist_frame, text="nm parcourus", font=ctk.CTkFont(size=9), text_color=COLORS['text_dim']).pack()

        # Bank balance
        bank_frame = ctk.CTkFrame(stats_frame, fg_color="#1a1a2e", corner_radius=8)
        bank_frame.pack(fill="x", padx=15, pady=(0, 10))

        bank_color = COLORS['positive'] if self.score >= 0 else COLORS['negative']
        self.bank_label = ctk.CTkLabel(
            bank_frame, text=f"{self.score:.2f} EUR",
            font=ctk.CTkFont(size=20, weight="bold"), text_color=bank_color
        )
        self.bank_label.pack(pady=(8, 2))
        ctk.CTkLabel(
            bank_frame, text="Compte en banque",
            font=ctk.CTkFont(size=10), text_color=COLORS['text_dim']
        ).pack(pady=(0, 8))

    def _refresh_career_panel(self):
        """Update career panel with current data"""
        if not CAREER_AVAILABLE or not hasattr(self, 'pilot') or not self.pilot:
            return

        try:
            # Update total hours
            self.total_hours_label.configure(text=f"{self.pilot.total_hours:.1f}h")

            # Update landings
            self.landings_label.configure(text=f"{self.pilot.total_landings}")
            self.perfect_label.configure(text=f"{self.pilot.perfect_landings}")
            self.distance_label.configure(text=f"{self.pilot.total_distance_nm:.0f}")

            # Update bank balance
            bank_color = COLORS['positive'] if self.score >= 0 else COLORS['negative']
            self.bank_label.configure(text=f"{self.score:.2f} EUR", text_color=bank_color)
            self.score_label.configure(text=f"BANK ACCOUNT: {self.score:.2f} EUR", text_color=bank_color)

            # Update license progress
            progress_data = self.pilot.get_next_license_progress()
            current_license = self.pilot.license.value.upper()

            licenses = ['STUDENT', 'PPL', 'CPL', 'ATPL']
            for lic in licenses:
                lic_idx = licenses.index(lic)
                current_idx = licenses.index(current_license) if current_license in licenses else 0

                if lic_idx < current_idx:
                    node_color = LICENSE_COLORS[lic]
                    self.license_nodes[lic].configure(fg_color="transparent", border_color=node_color)
                elif lic_idx == current_idx:
                    node_color = LICENSE_COLORS[lic]
                    self.license_nodes[lic].configure(fg_color=node_color, border_color=node_color)
                else:
                    self.license_nodes[lic].configure(fg_color="transparent", border_color="#444444")

            # Update progress bars
            license_hours = {'STUDENT': 0, 'PPL': 40, 'CPL': 200, 'ATPL': 1500}
            for i, lic in enumerate(licenses[:-1]):
                lic_idx = licenses.index(lic)
                current_idx = licenses.index(current_license) if current_license in licenses else 0

                if lic in self.license_progress_bars:
                    if lic_idx < current_idx:
                        self.license_progress_bars[lic].set(1.0)
                    elif lic_idx == current_idx and progress_data:
                        self.license_progress_bars[lic].set(progress_data.get('hours_progress', 0) / 100)
                    else:
                        self.license_progress_bars[lic].set(0)

            # Update company widget
            if self.current_company:
                self.company_name_label.configure(text=self.current_company.name)
                reputation = self.current_company.reputation
                rep_level = self.current_company.reputation_level.value.upper()
                multiplier = self.current_company.pay_multiplier

                self.reputation_bar.set(reputation / 100)
                self.reputation_bar.configure(progress_color=REPUTATION_COLORS.get(rep_level, "#888888"))
                self.reputation_label.configure(
                    text=f"{rep_level} ({reputation:.0f}/100)",
                    text_color=REPUTATION_COLORS.get(rep_level, "#888888")
                )
                mult_color = COLORS['positive'] if multiplier >= 1.0 else COLORS['negative']
                self.multiplier_label.configure(text=f"Multiplicateur: x{multiplier:.2f}", text_color=mult_color)

            # Update aircraft categories
            available = self.pilot.get_available_categories()
            current_category = self.aircraft_info.get('category', 'light_piston')

            for cat, badge in self.category_badges.items():
                is_unlocked = cat in available
                is_current = cat == current_category

                if is_current and is_unlocked:
                    badge.configure(fg_color=COLORS['positive_alt'], border_color=COLORS['positive'], text_color="#FFFFFF")
                elif is_unlocked:
                    badge.configure(fg_color="#3a3a4a", border_color="#555555", text_color="#CCCCCC")
                    badge.configure(text=CATEGORY_DISPLAY_NAMES.get(cat, cat))
                else:
                    badge.configure(fg_color="#1a1a1a", border_color="#333333", text_color="#555555")
                    badge.configure(text="🔒")

            # Update category hours bars
            hours_by_cat = self.pilot.hours_by_category
            max_hours = max(hours_by_cat.values()) if hours_by_cat and max(hours_by_cat.values()) > 0 else 1

            for cat, bar in self.category_hour_bars.items():
                cat_hours = hours_by_cat.get(cat, 0)
                bar.set(cat_hours / max_hours if max_hours > 0 else 0)

        except Exception as e:
            logger.error(f"Error refreshing career panel: {e}")

    def _show_upgrade_notification(self, old_license: str, new_license: str):
        """Show license upgrade notification popup"""
        try:
            popup = ctk.CTkToplevel(self)
            popup.title("LICENSE OBTAINED!")
            popup.geometry("400x200")
            popup.resizable(False, False)
            popup.attributes('-topmost', True)

            popup.update_idletasks()
            x = (popup.winfo_screenwidth() - 400) // 2
            y = (popup.winfo_screenheight() - 200) // 2
            popup.geometry(f"400x200+{x}+{y}")

            ctk.CTkLabel(
                popup, text="CONGRATULATIONS!",
                font=ctk.CTkFont(size=24, weight="bold"),
                text_color=COLORS['positive']
            ).pack(pady=(20, 10))

            ctk.CTkLabel(
                popup, text=f"You obtained the {new_license} license!",
                font=ctk.CTkFont(size=16),
                text_color="#FFFFFF"
            ).pack(pady=5)

            ctk.CTkLabel(
                popup, text=f"{old_license} → {new_license}",
                font=ctk.CTkFont(size=14),
                text_color=LICENSE_COLORS.get(new_license.upper(), COLORS['accent'])
            ).pack(pady=5)

            ctk.CTkButton(
                popup, text="OK",
                width=100, height=35,
                fg_color=COLORS['positive_alt'],
                command=popup.destroy
            ).pack(pady=15)

            play_success_sound()

        except Exception as e:
            logger.error(f"Error showing upgrade notification: {e}")

    def _browse_pln_folder(self):
        folder = filedialog.askdirectory(title="Select PLN destination folder")
        if folder:
            self.pln_path_entry.delete(0, 'end')
            self.pln_path_entry.insert(0, folder)
            self.config['pln_destination_folder'] = folder
            save_config(self.config)

    def _open_pln_folder(self):
        import subprocess
        folder = self.pln_path_entry.get() or str(FLIGHTPLANS_DIR.absolute())
        if os.path.exists(folder):
            subprocess.Popen(f'explorer "{folder}"')
        else:
            subprocess.Popen(f'explorer "{FLIGHTPLANS_DIR.absolute()}"')

    def _on_auto_copy_changed(self):
        self.config['auto_copy_pln'] = self.auto_copy_var.get()
        save_config(self.config)

    def _on_relaxed_mode_changed(self):
        """Toggle relaxed mode - disables failures and constraints"""
        relaxed = self.relaxed_var.get()
        self.config['relaxed_mode'] = relaxed

        if relaxed:
            # Disable failures and constraints
            self.failures_var.set(False)
            self.constraints_var.set(False)
            self.failures_check.configure(state="disabled")
            self.constraints_check.configure(state="disabled")
            logger.info("Relaxed mode enabled - failures and constraints disabled")
        else:
            # Re-enable controls
            self.failures_check.configure(state="normal")
            self.constraints_check.configure(state="normal")
            logger.info("Relaxed mode disabled")

        save_config(self.config)

    def _start_landing_challenge(self):
        """Start a landing challenge mission"""
        if not self.sim_connected:
            self.status_label.configure(text="Connect to MSFS first!", text_color="#FF6600")
            return

        # Show challenge selection dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Landing Challenge")
        dialog.geometry("400x350")
        dialog.transient(self)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 350) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            dialog, text="Select Landing Challenge",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=15)

        # Challenge types
        challenges_list = [
            ("BUTTER - Smoothest landing", "butter"),
            ("SHORT FIELD - Land in minimum distance", "short_field"),
            ("CROSSWIND - Strong crosswind landing", "crosswind"),
            ("NIGHT - Night landing", "night"),
            ("LOW VISIBILITY - CAT III ILS", "low_vis"),
        ]

        selected_challenge = ctk.StringVar(value="butter")

        for text, value in challenges_list:
            ctk.CTkRadioButton(
                dialog, text=text, variable=selected_challenge, value=value,
                font=ctk.CTkFont(size=12)
            ).pack(anchor="w", padx=30, pady=5)

        def start_challenge():
            challenge_type = selected_challenge.get()
            dialog.destroy()
            self._launch_challenge(challenge_type)

        ctk.CTkButton(
            dialog, text="Start Challenge",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#6B4B2B", hover_color="#7B5B3B",
            command=start_challenge
        ).pack(pady=20)

        ctk.CTkButton(
            dialog, text="Cancel",
            font=ctk.CTkFont(size=11),
            fg_color="#555555", hover_color="#666666",
            command=dialog.destroy
        ).pack()

    def _launch_challenge(self, challenge_type: str):
        """Launch a specific landing challenge"""
        from systems.challenges import ChallengeType, get_challenge_manager

        # Map string to enum
        type_map = {
            "butter": ChallengeType.BUTTER,
            "short_field": ChallengeType.SHORT_FIELD,
            "crosswind": ChallengeType.CROSSWIND,
            "night": ChallengeType.NIGHT,
            "low_vis": ChallengeType.LOW_VISIBILITY,
        }

        challenge_enum = type_map.get(challenge_type, ChallengeType.BUTTER)

        # Get current position as target airport
        if self.aircraft_info.get('latitude') and self.aircraft_info.get('longitude'):
            # Start challenge
            self.challenges.start_challenge(
                challenge_type=challenge_enum,
                airport_icao=self.current_mission.get('arrival', {}).get('icao', 'LFPG') if self.current_mission else "LFPG",
                runway_heading=self.aircraft_info.get('heading', 0)
            )

            self.status_label.configure(
                text=f"Challenge {challenge_type.upper()} started!", text_color="#FFD700"
            )

            if COPILOT_AVAILABLE and self.voice:
                self.voice.speak(f"Challenge {challenge_type} lance. Bonne chance!")

            logger.info(f"Landing challenge started: {challenge_type}")
        else:
            self.status_label.configure(text="Load a flight first!", text_color="#FF6600")

    def _on_dist_min_changed(self, value):
        """Callback when min distance slider changes"""
        val = int(value)
        # Ensure min doesn't exceed max
        if val >= self.dist_max_var.get():
            val = self.dist_max_var.get() - 10
            self.dist_min_var.set(val)
        self.dist_min_value.configure(text=f"{val} nm")

    def _on_dist_max_changed(self, value):
        """Callback when max distance slider changes"""
        val = int(value)
        # Ensure max doesn't go below min
        if val <= self.dist_min_var.get():
            val = self.dist_min_var.get() + 10
            self.dist_max_var.set(val)
        self.dist_max_value.configure(text=f"{val} nm")

    def _save_config(self):
        self.config['pln_destination_folder'] = self.pln_path_entry.get()
        self.config['groq_api_key'] = self.groq_entry.get()
        self.config['openaip_api_key'] = self.openaip_entry.get()
        self.config['auto_copy_pln'] = self.auto_copy_var.get()
        self.config['copilot_enabled'] = self.copilot_var.get()
        self.config['voice_enabled'] = self.voice_var.get()
        self.config['career_mode'] = self.career_var.get()
        self.config['fuel_management'] = self.fuel_var.get()

        # Distance settings
        self.config['mission_distance_min'] = self.dist_min_var.get()
        self.config['mission_distance_max'] = self.dist_max_var.get()

        # V2 Enhanced options
        self.config['relaxed_mode'] = self.relaxed_var.get()
        if 'failures' not in self.config:
            self.config['failures'] = {}
        self.config['failures']['enabled'] = self.failures_var.get()
        if 'constraints' not in self.config:
            self.config['constraints'] = {}
        self.config['constraints']['enabled'] = self.constraints_var.get()

        save_config(self.config)

        # Update copilot API key
        if COPILOT_AVAILABLE and self.groq_entry.get():
            self.copilot_llm.set_api_key(self.groq_entry.get())
            # Also update voice system for STT
            if hasattr(self, 'voice') and self.voice:
                self.voice.set_groq_api_key(self.groq_entry.get())

        self.save_config_btn.configure(text="Saved!", fg_color="#2E7D32")
        self.after(2000, lambda: self.save_config_btn.configure(text="Save Config", fg_color="#4B6F2B"))

    def _test_voice(self):
        """Test TTS voice"""
        if COPILOT_AVAILABLE and self.voice:
            self.voice.speak("Test de synthese vocale. Le copilote est pret.")

    def _start_pattern_training(self):
        """Start pattern training mode"""
        if not self.sim_connected:
            self.status_label.configure(text="Connect to MSFS first!", text_color="#FF6600")
            return

        if self.pattern_training_active:
            # Stop current training
            self._stop_pattern_training()
            return

        # Show configuration dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Tour de Piste - Configuration")
        dialog.geometry("400x350")
        dialog.transient(self)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        # Title
        ctk.CTkLabel(
            dialog, text="Training Tour de Piste",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=15)

        # Get current position from sim
        current_lat = self._safe_get("PLANE_LATITUDE") or 0
        current_lon = self._safe_get("PLANE_LONGITUDE") or 0
        current_heading = self._safe_get("PLANE_HEADING_DEGREES_TRUE") or 0
        current_alt = self._safe_get("PLANE_ALTITUDE") or 0

        # Try to find nearest airport
        nearest_icao = "LFPG"
        nearest_name = "Unknown"
        if self.airports:
            min_dist = float('inf')
            for airport in self.airports:
                dist = self._haversine(current_lat, current_lon,
                                       airport.get('lat', 0), airport.get('lon', 0))
                if dist < min_dist:
                    min_dist = dist
                    nearest_icao = airport.get('icao', 'LFPG')
                    nearest_name = airport.get('name', 'Unknown')

        # Airport selection
        airport_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        airport_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(airport_frame, text="Aeroport:", width=100, anchor="w").pack(side="left")
        airport_entry = ctk.CTkEntry(airport_frame, width=100)
        airport_entry.insert(0, nearest_icao)
        airport_entry.pack(side="left", padx=5)
        ctk.CTkLabel(airport_frame, text=nearest_name[:25], font=ctk.CTkFont(size=10)).pack(side="left", padx=5)

        # Runway selection
        runway_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        runway_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(runway_frame, text="Piste:", width=100, anchor="w").pack(side="left")
        runway_entry = ctk.CTkEntry(runway_frame, width=60)
        # Estimate runway from heading
        rwy_num = int(((current_heading + 5) % 360) / 10)
        if rwy_num == 0:
            rwy_num = 36
        runway_entry.insert(0, f"{rwy_num:02d}")
        runway_entry.pack(side="left", padx=5)
        ctk.CTkLabel(runway_frame, text=f"(cap actuel: {current_heading:.0f})",
                    font=ctk.CTkFont(size=10)).pack(side="left", padx=5)

        # Pattern altitude
        alt_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        alt_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(alt_frame, text="Altitude pattern:", width=100, anchor="w").pack(side="left")
        alt_entry = ctk.CTkEntry(alt_frame, width=60)
        alt_entry.insert(0, "1000")
        alt_entry.pack(side="left", padx=5)
        ctk.CTkLabel(alt_frame, text="ft AGL", font=ctk.CTkFont(size=10)).pack(side="left", padx=5)

        # Pattern direction
        dir_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        dir_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(dir_frame, text="Direction:", width=100, anchor="w").pack(side="left")
        direction_var = ctk.StringVar(value="left")
        ctk.CTkRadioButton(dir_frame, text="Gauche", variable=direction_var, value="left").pack(side="left", padx=10)
        ctk.CTkRadioButton(dir_frame, text="Droite", variable=direction_var, value="right").pack(side="left", padx=10)

        # V-speeds
        vspeeds_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        vspeeds_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(vspeeds_frame, text="Vr:", width=50, anchor="w").pack(side="left")
        vr_entry = ctk.CTkEntry(vspeeds_frame, width=50)
        vr_entry.insert(0, "55")
        vr_entry.pack(side="left", padx=5)

        ctk.CTkLabel(vspeeds_frame, text="Vref:", width=50, anchor="w").pack(side="left", padx=10)
        vref_entry = ctk.CTkEntry(vspeeds_frame, width=50)
        vref_entry.insert(0, "65")
        vref_entry.pack(side="left", padx=5)

        # Info label
        ctk.CTkLabel(
            dialog,
            text="Positionnez-vous sur la piste avant de demarrer.\nLe copilote annoncera chaque segment du tour de piste.",
            font=ctk.CTkFont(size=10),
            text_color="#AAAAAA"
        ).pack(pady=15)

        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        def start_training():
            icao = airport_entry.get().upper()
            runway = runway_entry.get()
            try:
                pattern_alt = int(alt_entry.get())
            except:
                pattern_alt = 1000
            try:
                vr = float(vr_entry.get())
                vref = float(vref_entry.get())
            except:
                vr = 55
                vref = 65

            direction = direction_var.get()

            # Find airport coordinates
            airport_lat = current_lat
            airport_lon = current_lon
            airport_elev = current_alt
            for airport in self.airports:
                if airport.get('icao') == icao:
                    airport_lat = airport.get('lat', current_lat)
                    airport_lon = airport.get('lon', current_lon)
                    airport_elev = airport.get('elevation', 0) or 0
                    break

            # Calculate runway heading from runway number
            try:
                rwy_heading = int(runway.replace('L', '').replace('R', '').replace('C', '')) * 10
            except:
                rwy_heading = current_heading

            dialog.destroy()
            self._launch_pattern_training(
                icao, runway, airport_lat, airport_lon,
                rwy_heading, airport_elev, pattern_alt, direction, vr, vref
            )

        ctk.CTkButton(
            btn_frame, text="Demarrer", width=120,
            fg_color="#2B6B4B", hover_color="#3B7B5B",
            command=start_training
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame, text="Annuler", width=120,
            fg_color="#555555", hover_color="#666666",
            command=dialog.destroy
        ).pack(side="right", padx=10)

    def _launch_pattern_training(self, icao: str, runway: str,
                                  airport_lat: float, airport_lon: float,
                                  runway_heading: float, airport_elev: float,
                                  pattern_alt: int, direction: str,
                                  vr: float, vref: float):
        """Launch the pattern training session"""
        if not SYSTEMS_AVAILABLE:
            self.status_label.configure(text="Systems module not available!", text_color="#FF6600")
            return

        # Initialize pattern trainer
        self.pattern_trainer = get_pattern_trainer()
        self.pattern_trainer.set_vspeeds(vr, vref)

        # Set callbacks
        self.pattern_trainer.set_callbacks(
            on_leg_change=self._on_pattern_leg_change,
            on_pattern_complete=self._on_pattern_complete,
            on_session_end=self._on_pattern_session_end
        )

        # Start session
        self.pattern_trainer.start_session(
            airport_icao=icao,
            runway=runway,
            airport_lat=airport_lat,
            airport_lon=airport_lon,
            runway_heading=runway_heading,
            airport_elevation=airport_elev,
            pattern_altitude_agl=pattern_alt,
            pattern_direction=direction
        )

        self.pattern_training_active = True

        # Update button
        self.pattern_btn.configure(text="Stop Training", fg_color="#8B0000", hover_color="#A00000")

        # Update status
        self.status_label.configure(
            text=f"Pattern Training: {icao} RWY {runway} - {direction.upper()} pattern @ {pattern_alt}ft",
            text_color="#00FF7F"
        )

        if COPILOT_AVAILABLE and self.voice:
            self.voice.speak(f"Entrainement tour de piste demarre. Aeroport {icao}, piste {runway}. "
                           f"Altitude de circuit {pattern_alt} pieds. Circuit main {direction}.")

        logger.info(f"Pattern training started: {icao} RWY {runway}")

    def _stop_pattern_training(self):
        """Stop pattern training and show results"""
        if not self.pattern_trainer:
            return

        session = self.pattern_trainer.stop_session()
        self.pattern_training_active = False

        # Update button
        self.pattern_btn.configure(text="Tour de Piste", fg_color="#2B6B4B", hover_color="#3B7B5B")

        if session and session.total_patterns > 0:
            # Show results dialog
            self._show_pattern_results(session)
        else:
            self.status_label.configure(text="Pattern training ended - no patterns completed", text_color="#FFD700")

        logger.info("Pattern training stopped")

    def _on_pattern_leg_change(self, old_leg, new_leg):
        """Callback when pattern leg changes"""
        if not self.pattern_trainer:
            return

        # Skip announcements when in menu
        if self._is_in_menu():
            return

        # Get callout for new leg
        callout = self.pattern_trainer.get_leg_callout()

        if callout and COPILOT_AVAILABLE and self.voice:
            self.voice.speak(callout)

        # Update status with current leg
        if self.pattern_trainer.session:
            patterns_done = len(self.pattern_trainer.session.patterns)
            self.status_label.configure(
                text=f"Pattern #{patterns_done + 1} - {new_leg.value.replace('_', ' ').title()}",
                text_color="#00FF7F"
            )

    def _on_pattern_complete(self, pattern):
        """Callback when a pattern is completed"""
        if not pattern:
            return

        # Skip announcements when in menu
        if self._is_in_menu():
            return

        # Announce pattern score
        feedback_parts = []

        if pattern.landing:
            landing = pattern.landing
            if landing.touchdown_score >= 90:
                feedback_parts.append("Excellent atterrissage!")
            elif landing.touchdown_score >= 70:
                feedback_parts.append("Bon atterrissage")
            else:
                feedback_parts.append(f"Atterrissage a ameliorer, {landing.touchdown_rate:.0f} pieds par minute")

        if pattern.takeoff:
            takeoff = pattern.takeoff
            if takeoff.total_score >= 80:
                feedback_parts.append("Decollage parfait")
            elif takeoff.total_score < 60:
                for fb in takeoff.feedback[:1]:  # Only first feedback
                    feedback_parts.append(fb)

        feedback_parts.append(f"Score du tour: {pattern.total_score}, note {pattern.grade}")

        if COPILOT_AVAILABLE and self.voice:
            self.voice.speak(". ".join(feedback_parts))

        logger.info(f"Pattern #{pattern.pattern_number} completed: {pattern.total_score} ({pattern.grade})")

    def _on_pattern_session_end(self, session):
        """Callback when session ends"""
        logger.info(f"Pattern session ended: {session.total_patterns} patterns")

    def _show_pattern_results(self, session):
        """Show pattern training results dialog"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Resultats Tour de Piste")
        dialog.geometry("450x500")
        dialog.transient(self)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        # Title
        ctk.CTkLabel(
            dialog, text="Resultats de la Session",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=15)

        # Session info
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            info_frame,
            text=f"Aeroport: {session.airport_icao} - Piste {session.runway}",
            font=ctk.CTkFont(size=12)
        ).pack(pady=5)

        ctk.CTkLabel(
            info_frame,
            text=f"Tours completes: {session.total_patterns}",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=5)

        ctk.CTkLabel(
            info_frame,
            text=f"Touch & Go: {session.total_touch_and_go} | Full Stop: {session.total_full_stop}",
            font=ctk.CTkFont(size=11)
        ).pack(pady=5)

        # Scores frame
        scores_frame = ctk.CTkFrame(dialog)
        scores_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            scores_frame, text="Atterrissages",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(pady=5)

        scores_grid = ctk.CTkFrame(scores_frame, fg_color="transparent")
        scores_grid.pack(fill="x", padx=10, pady=5)

        # Landing scores
        ctk.CTkLabel(scores_grid, text="Meilleur:", width=80, anchor="e").grid(row=0, column=0, padx=5, pady=2)
        ctk.CTkLabel(scores_grid, text=f"{session.best_landing_score}",
                    font=ctk.CTkFont(weight="bold"), text_color="#00FF7F").grid(row=0, column=1, padx=5, pady=2)

        ctk.CTkLabel(scores_grid, text="Pire:", width=80, anchor="e").grid(row=1, column=0, padx=5, pady=2)
        ctk.CTkLabel(scores_grid, text=f"{session.worst_landing_score}",
                    font=ctk.CTkFont(weight="bold"), text_color="#FF6347").grid(row=1, column=1, padx=5, pady=2)

        ctk.CTkLabel(scores_grid, text="Moyenne:", width=80, anchor="e").grid(row=2, column=0, padx=5, pady=2)
        avg_color = "#00FF7F" if session.average_landing_score >= 70 else "#FFD700" if session.average_landing_score >= 50 else "#FF6347"
        ctk.CTkLabel(scores_grid, text=f"{session.average_landing_score:.0f}",
                    font=ctk.CTkFont(weight="bold"), text_color=avg_color).grid(row=2, column=1, padx=5, pady=2)

        # Takeoff scores
        ctk.CTkLabel(
            scores_frame, text="Decollages",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(pady=(10, 5))

        takeoff_grid = ctk.CTkFrame(scores_frame, fg_color="transparent")
        takeoff_grid.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(takeoff_grid, text="Meilleur:", width=80, anchor="e").grid(row=0, column=0, padx=5, pady=2)
        ctk.CTkLabel(takeoff_grid, text=f"{session.best_takeoff_score}",
                    font=ctk.CTkFont(weight="bold"), text_color="#00FF7F").grid(row=0, column=1, padx=5, pady=2)

        ctk.CTkLabel(takeoff_grid, text="Moyenne:", width=80, anchor="e").grid(row=1, column=0, padx=5, pady=2)
        avg_to_color = "#00FF7F" if session.average_takeoff_score >= 70 else "#FFD700" if session.average_takeoff_score >= 50 else "#FF6347"
        ctk.CTkLabel(takeoff_grid, text=f"{session.average_takeoff_score:.0f}",
                    font=ctk.CTkFont(weight="bold"), text_color=avg_to_color).grid(row=1, column=1, padx=5, pady=2)

        # Pattern details
        if session.patterns:
            details_frame = ctk.CTkScrollableFrame(dialog, height=150)
            details_frame.pack(fill="both", expand=True, padx=20, pady=10)

            ctk.CTkLabel(
                details_frame, text="Details par tour:",
                font=ctk.CTkFont(size=12, weight="bold")
            ).pack(anchor="w", pady=5)

            for pattern in session.patterns:
                landing_str = f"Ldg: {pattern.landing.total_score}" if pattern.landing else "Ldg: -"
                takeoff_str = f"T/O: {pattern.takeoff.total_score}" if pattern.takeoff else "T/O: -"
                pattern_type = pattern.landing.landing_type if pattern.landing else "?"

                ctk.CTkLabel(
                    details_frame,
                    text=f"Tour #{pattern.pattern_number}: {pattern.grade} ({pattern.total_score}) - {takeoff_str}, {landing_str} [{pattern_type}]",
                    font=ctk.CTkFont(size=10)
                ).pack(anchor="w", pady=1)

        # Close button
        ctk.CTkButton(
            dialog, text="Fermer", width=120,
            command=dialog.destroy
        ).pack(pady=15)

        # Voice summary
        if COPILOT_AVAILABLE and self.voice:
            self.voice.speak(
                f"Session terminee. {session.total_patterns} tours completes. "
                f"Moyenne atterrissages: {session.average_landing_score:.0f}. "
                f"Moyenne decollages: {session.average_takeoff_score:.0f}."
            )

    # =========================================================================
    # JOYSTICK PTT (Push-to-Talk)
    # =========================================================================

    def _init_joystick_ptt(self):
        """Initialize joystick for Push-to-Talk"""
        self.joysticks = []
        self.ptt_joystick_id = self.config.get('ptt_joystick_id', None)
        self.ptt_button_id = self.config.get('ptt_button_id', None)
        self.ptt_button_pressed = False
        self.ptt_enabled = self.config.get('ptt_enabled', False)
        self._joystick_thread = None
        self._joystick_running = False
        self._joystick_button_states = {}  # {(js_id, btn_id): state}
        self._detected_button = [None, None]  # Shared with detection thread

        if not pygame_available:
            logger.warning("Pygame not available - joystick PTT disabled")
            return

        try:
            # Initialize only joystick subsystem (avoid display conflicts with Tkinter)
            if not pygame.joystick.get_init():
                pygame.joystick.init()

            joystick_count = pygame.joystick.get_count()

            if joystick_count == 0:
                logger.info("No joysticks detected")
                return

            # Initialize all joysticks
            for i in range(joystick_count):
                try:
                    js = pygame.joystick.Joystick(i)
                    js.init()
                    self.joysticks.append({
                        'id': i,
                        'name': js.get_name(),
                        'buttons': js.get_numbuttons(),
                        'joystick': js
                    })
                    logger.info(f"Joystick {i}: {js.get_name()} ({js.get_numbuttons()} buttons)")
                except Exception as e:
                    logger.error(f"Failed to init joystick {i}: {e}")

            if self.ptt_enabled and self.ptt_joystick_id is not None:
                logger.info(f"PTT configured: Joystick {self.ptt_joystick_id}, Button {self.ptt_button_id}")

            # Start joystick polling thread
            self._start_joystick_thread()

        except Exception as e:
            logger.error(f"Failed to init joystick system: {e}")

    def _start_joystick_thread(self):
        """Start background thread for joystick polling"""
        if self._joystick_thread and self._joystick_thread.is_alive():
            return

        self._joystick_running = True

        def joystick_poll_loop():
            """Background thread to poll joystick states"""
            import time
            import os

            # Initialize ONLY joystick and event subsystems - NOT full pygame.init()!
            # pygame.init() would initialize ALL subsystems including audio,
            # which conflicts with pygame.mixer used by TTS in another thread
            os.environ['SDL_VIDEODRIVER'] = 'dummy'
            os.environ['SDL_AUDIODRIVER'] = 'dummy'  # Prevent audio conflicts

            try:
                # Initialize ONLY what we need for joystick polling
                if not pygame.get_init():
                    pygame.display.init()  # Needed for event system
                pygame.joystick.init()

                # Re-init joysticks in this thread
                thread_joysticks = []
                for i in range(pygame.joystick.get_count()):
                    try:
                        js = pygame.joystick.Joystick(i)
                        js.init()
                        thread_joysticks.append({
                            'id': i,
                            'buttons': js.get_numbuttons(),
                            'joystick': js
                        })
                    except:
                        pass

                logger.info(f"Joystick thread initialized with {len(thread_joysticks)} joysticks")

                while self._joystick_running:
                    try:
                        # Pump events to update joystick states
                        pygame.event.pump()

                        # Read button states
                        for js_info in thread_joysticks:
                            js = js_info['joystick']
                            js_id = js_info['id']
                            for btn_id in range(js_info['buttons']):
                                try:
                                    state = js.get_button(btn_id)
                                    old_state = self._joystick_button_states.get((js_id, btn_id), False)
                                    if state != old_state:
                                        self._joystick_button_states[(js_id, btn_id)] = state
                                        if state:
                                            logger.debug(f"Joystick {js_id} button {btn_id} DOWN")
                                        else:
                                            logger.debug(f"Joystick {js_id} button {btn_id} UP")
                                except:
                                    pass

                        time.sleep(0.02)  # 50Hz polling
                    except Exception as e:
                        logger.error(f"Joystick poll error: {e}")
                        time.sleep(0.5)

            except Exception as e:
                logger.error(f"Joystick thread init error: {e}")

        self._joystick_thread = threading.Thread(target=joystick_poll_loop, daemon=True)
        self._joystick_thread.start()
        logger.info("Joystick polling thread started")

    def _stop_joystick_thread(self):
        """Stop the joystick polling thread"""
        self._joystick_running = False
        if self._joystick_thread:
            self._joystick_thread.join(timeout=1.0)

    def _configure_ptt_button(self):
        """Open dialog to configure PTT button mapping"""
        if not pygame_available:
            self._show_message("Erreur", "Pygame non disponible pour la detection des joysticks")
            return

        if not self.joysticks:
            # Try to reinitialize
            self._init_joystick_ptt()
            if not self.joysticks:
                self._show_message("Erreur", "Aucun joystick detecte. Connectez votre yoke et reessayez.")
                return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Configuration PTT (Push-to-Talk)")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()

        # Title
        ctk.CTkLabel(
            dialog, text="Configuration du bouton PTT",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=15)

        # Instructions
        ctk.CTkLabel(
            dialog,
            text="Selectionnez un joystick puis appuyez sur le bouton\nque vous voulez utiliser comme Push-to-Talk",
            text_color="#888888"
        ).pack(pady=5)

        # Joystick selection
        js_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        js_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(js_frame, text="Joystick:", width=100, anchor="w").pack(side="left")

        js_names = [f"{js['id']}: {js['name']}" for js in self.joysticks]
        js_var = ctk.StringVar(value=js_names[0] if js_names else "")
        js_combo = ctk.CTkComboBox(js_frame, variable=js_var, values=js_names, width=300)
        js_combo.pack(side="left", padx=10)

        # Current config display
        config_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        config_frame.pack(fill="x", padx=20, pady=10)

        current_config = "Non configure"
        if self.ptt_joystick_id is not None and self.ptt_button_id is not None:
            js_name = next((js['name'] for js in self.joysticks if js['id'] == self.ptt_joystick_id), "Unknown")
            current_config = f"Joystick {self.ptt_joystick_id} ({js_name}), Bouton {self.ptt_button_id}"

        config_label = ctk.CTkLabel(
            config_frame,
            text=f"Configuration actuelle: {current_config}",
            text_color="#00AA00" if self.ptt_enabled else "#888888"
        )
        config_label.pack()

        # Detection area
        detect_frame = ctk.CTkFrame(dialog, corner_radius=10)
        detect_frame.pack(fill="both", expand=True, padx=20, pady=10)

        detect_label = ctk.CTkLabel(
            detect_frame,
            text="Appuyez sur un bouton du joystick...",
            font=ctk.CTkFont(size=14),
            text_color="#FFAA00"
        )
        detect_label.pack(expand=True)

        # Variables for detection
        detected_button = [None, None]  # [joystick_id, button_id]
        detecting = [True]

        def joystick_detection_thread(selected_id):
            """Thread to detect joystick button presses using the polling cache"""
            import time
            js_info = next((js for js in self.joysticks if js['id'] == selected_id), None)
            if not js_info:
                return

            num_buttons = js_info['buttons']

            while detecting[0]:
                try:
                    # Read button states from the polling thread's cache
                    for btn_id in range(num_buttons):
                        button_key = (selected_id, btn_id)
                        if self._joystick_button_states.get(button_key, False):
                            detected_button[0] = selected_id
                            detected_button[1] = btn_id
                            logger.info(f"PTT button detected: Joystick {selected_id}, Button {btn_id}")
                            return
                    time.sleep(0.05)
                except Exception as e:
                    logger.error(f"Joystick detection thread error: {e}")
                    time.sleep(0.1)

        def update_ui():
            """Update UI based on detection results"""
            if not detecting[0]:
                return

            if detected_button[0] is not None and detected_button[1] is not None:
                detect_label.configure(
                    text=f"Bouton {detected_button[1]} detecte!",
                    text_color="#00FF00"
                )
                return  # Stop updating

            dialog.after(100, update_ui)

        def start_detection():
            """Start the detection thread"""
            selected_text = js_var.get()
            if not selected_text:
                detect_label.configure(text="Selectionnez un joystick", text_color="#FF5555")
                return

            try:
                selected_id = int(selected_text.split(":")[0])
            except:
                return

            # Reset detection
            detected_button[0] = None
            detected_button[1] = None
            detect_label.configure(text="Appuyez sur un bouton...", text_color="#FFAA00")

            # Start detection thread
            detection_thread = threading.Thread(
                target=joystick_detection_thread,
                args=(selected_id,),
                daemon=True
            )
            detection_thread.start()

            # Start UI updates
            update_ui()

        def save_ptt_config():
            detecting[0] = False

            if detected_button[0] is not None and detected_button[1] is not None:
                self.ptt_joystick_id = detected_button[0]
                self.ptt_button_id = detected_button[1]
                self.ptt_enabled = True

                # Save to config file
                self.config['ptt_joystick_id'] = self.ptt_joystick_id
                self.config['ptt_button_id'] = self.ptt_button_id
                self.config['ptt_enabled'] = True
                save_config(self.config)  # Call global save_config

                logger.info(f"PTT configured: Joystick {self.ptt_joystick_id}, Button {self.ptt_button_id}")
                self._show_message("Succes", f"PTT configure sur le bouton {self.ptt_button_id}")
            else:
                self._show_message("Erreur", "Aucun bouton detecte")

            dialog.destroy()

        def disable_ptt():
            detecting[0] = False
            self.ptt_enabled = False
            self.config['ptt_enabled'] = False
            save_config(self.config)  # Call global save_config
            logger.info("PTT disabled")
            dialog.destroy()

        def on_close():
            detecting[0] = False
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_close)

        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            btn_frame, text="Enregistrer", width=120,
            fg_color="#00AA00", hover_color="#008800",
            command=save_ptt_config
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="Desactiver PTT", width=120,
            fg_color="#AA5500", hover_color="#884400",
            command=disable_ptt
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="Detecter", width=120,
            fg_color="#2B4B6F", hover_color="#3B5B7F",
            command=start_detection
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="Annuler", width=120,
            command=on_close
        ).pack(side="right", padx=5)

    def _check_joystick_ptt(self):
        """Check if PTT button is pressed and trigger voice recording"""
        if not self.ptt_enabled or not pygame_available:
            return

        if self.ptt_joystick_id is None or self.ptt_button_id is None:
            return

        if not self.joysticks:
            return

        try:
            # Read button state from the polling thread's cache
            button_key = (self.ptt_joystick_id, self.ptt_button_id)
            button_state = self._joystick_button_states.get(button_key, False)

            # Detect button press (rising edge)
            if button_state and not self.ptt_button_pressed:
                self.ptt_button_pressed = True
                logger.info("PTT button pressed - starting voice recording")
                if COPILOT_AVAILABLE and self.voice:
                    self.voice.start_listening()

            elif not button_state and self.ptt_button_pressed:
                self.ptt_button_pressed = False
                logger.debug("PTT button released")

        except Exception as e:
            if self.update_count % 100 == 0:  # Log only occasionally
                logger.error(f"Joystick PTT error: {e}")

    def _connect_simconnect_async(self):
        """Connect to SimConnect asynchronously"""
        def connect():
            logger.info("Connecting to SimConnect...")
            try:
                if OPTIMIZATION_AVAILABLE:
                    # Use adaptive SimConnect (V2) with background polling
                    self.sim = get_adaptive_simconnect()
                    # IMPORTANT: Check the return value of connect()!
                    # connect() returns False if MSFS is not running
                    if not self.sim.connect():
                        raise Exception("SimConnect connection failed - MSFS not running")
                    # START BACKGROUND POLLING - this is the key optimization!
                    # All SimConnect reads now happen in background thread
                    self.sim.start_polling()
                    logger.info("SimConnect background polling started")
                else:
                    # Fallback to standard SimConnect
                    from SimConnect import SimConnect, AircraftRequests
                    self.sim = SimConnect()

                self.sim_connected = True

                # Wait a moment for first poll to populate data
                import time
                time.sleep(0.5)

                self._update_aircraft_info()

                aircraft_display = f"{self.aircraft_info['title'][:25]} ({self.aircraft_info['category']})"
                self.after(0, lambda: self.status_label.configure(
                    text="Connected to MSFS 2024!", text_color="#00FF00"
                ))
                self.after(0, lambda ad=aircraft_display: self.aircraft_label.configure(
                    text=f"Aircraft: {ad}"
                ))
                logger.info(f"SimConnect OK! Aircraft: {self.aircraft_info['title']}")

            except Exception as e:
                self.sim_connected = False
                logger.error(f"SimConnect error: {e}")
                self.after(0, lambda: self.status_label.configure(
                    text="Simulator not detected", text_color="#FF6666"
                ))

        threading.Thread(target=connect, daemon=True).start()

    def _safe_get(self, var_name: str):
        """Safely get SimConnect variable"""
        try:
            if OPTIMIZATION_AVAILABLE and hasattr(self.sim, 'get_data'):
                return self.sim.get_data(var_name)
            elif hasattr(self.sim, 'aircraft_requests'):
                return self.sim.aircraft_requests.get(var_name)
            return None
        except:
            return None

    def _update_aircraft_info(self):
        """Update aircraft information from snapshot (non-blocking)"""
        if not self.sim_connected:
            return

        try:
            title = None
            engine_type = None
            num_engines = None

            # Try snapshot first (non-blocking)
            if OPTIMIZATION_AVAILABLE and hasattr(self.sim, 'get_snapshot'):
                snap = self.sim.get_snapshot()
                if snap.title and snap.title != "Unknown":
                    title = snap.title
                engine_type = snap.engine_type
                num_engines = snap.num_engines

            # Fallback to direct read if snapshot doesn't have title yet
            if not title or title == "Unknown":
                raw_title = self._safe_get("TITLE")
                logger.debug(f"Raw TITLE from _safe_get: {raw_title} (type: {type(raw_title)})")
                if raw_title:
                    if isinstance(raw_title, bytes):
                        title = raw_title.decode('utf-8', errors='ignore').strip('\x00')
                    else:
                        title = str(raw_title).strip('\x00')
                    logger.debug(f"Decoded title: {title}")

            # Also get engine info from direct read if not in snapshot
            if engine_type is None or engine_type == 0:
                raw_engine = self._safe_get("ENGINE_TYPE")
                if raw_engine is not None:
                    engine_type = int(raw_engine)

            if num_engines is None or num_engines == 0:
                raw_engines = self._safe_get("NUMBER_OF_ENGINES")
                if raw_engines is not None:
                    num_engines = int(raw_engines)

            # Update aircraft info
            if title:
                self.aircraft_info["title"] = title
            if engine_type is not None:
                self.aircraft_info["engine_type"] = engine_type
            if num_engines is not None:
                self.aircraft_info["num_engines"] = num_engines

            self.aircraft_info["category"] = self._determine_aircraft_category()

            # Update UI label if we have a valid title
            if title and title != "Unknown" and hasattr(self, 'aircraft_label'):
                display_title = title[:25] if len(title) > 25 else title
                category = self.aircraft_info["category"]
                self.aircraft_label.configure(text=f"Aircraft: {display_title} ({category})")

            # Configure callouts V-speeds based on aircraft category
            if COPILOT_AVAILABLE and hasattr(self, 'callouts'):
                category = self.aircraft_info["category"]
                # Map our categories to callout V-speed profiles
                category_map = {
                    'light_piston': 'light_piston',
                    'twin_piston': 'light_piston',
                    'single_turboprop': 'light_turboprop',
                    'turboprop': 'medium_turboprop',
                    'light_jet': 'light_jet',
                    'jet': 'medium_jet',
                    'heavy_jet': 'heavy_jet',
                    'helicopter': 'helicopter',
                    'airliner': 'airliner'
                }
                mapped_category = category_map.get(category, 'light_piston')
                self.callouts.set_aircraft_category(mapped_category)

                # Update phase detector with aircraft profile
                if hasattr(self, 'phase_detector'):
                    self.phase_detector.set_aircraft_category(mapped_category)

        except Exception as e:
            logger.warning(f"Aircraft info error: {e}")

    def _determine_aircraft_category(self) -> str:
        """Determine aircraft category"""
        engine = self.aircraft_info.get("engine_type", 0)
        num_eng = self.aircraft_info.get("num_engines", 1)
        title = self.aircraft_info.get("title", "").lower()

        if engine == 1:  # Jet
            if num_eng >= 4 or any(x in title for x in ["747", "a380", "777"]):
                return "heavy_jet"
            elif num_eng >= 2:
                return "jet"
            else:
                return "light_jet"
        elif engine == 5:  # Turboprop
            if num_eng >= 2:
                return "turboprop"
            else:
                return "single_turboprop"
        elif engine == 0:  # Piston
            if num_eng >= 2:
                return "twin_piston"
            else:
                return "light_piston"
        elif engine == 3:  # Helicopter
            return "helicopter"

        return "light_piston"

    def _on_phase_change(self, new_phase, old_phase):
        """Callback when flight phase changes"""
        logger.info(f"Phase change: {old_phase.value} -> {new_phase.value}")

        if COPILOT_AVAILABLE:
            # Update UI - special handling for UNKNOWN (menu/loading)
            if new_phase == FlightPhase.UNKNOWN:
                self.after(0, lambda: self.copilot_status.configure(
                    text="En pause (menu du jeu)"
                ))
            else:
                self.after(0, lambda: self.copilot_status.configure(
                    text=f"Active | Phase: {new_phase.name}"
                ))

            # Voice announcement for phase changes
            # Skip announcements when no mission active or transitioning from/to UNKNOWN (menu)
            if self.config.get('copilot_enabled', True):
                if self.config.get('voice_enabled', True):
                    # Don't announce when no mission is active
                    if not self.mission_active:
                        logger.debug(f"Phase announcement skipped (no mission active): {old_phase.value} -> {new_phase.value}")
                        return

                    # Don't announce when entering or leaving menu
                    if old_phase == FlightPhase.UNKNOWN or new_phase == FlightPhase.UNKNOWN:
                        logger.debug(f"Phase announcement skipped (menu transition): {old_phase.value} -> {new_phase.value}")
                        return

                    import time
                    current_time = time.time()

                    if new_phase == FlightPhase.TAKEOFF_ROLL:
                        self.voice.speak("Decollage")
                    elif new_phase == FlightPhase.CRUISE:
                        # SMART COPILOT: Check if we're actually at the target cruise altitude
                        last_cruise_callout = getattr(self, '_last_cruise_callout', 0)
                        if current_time - last_cruise_callout > 300:  # 5 minutes cooldown

                            # Get current altitude and target cruise altitude
                            current_alt = self._safe_get("PLANE_ALTITUDE") if self.sim_connected else 0
                            current_alt = current_alt or 0
                            target_cruise = 0
                            if self.current_mission:
                                target_cruise = self.current_mission.get('cruise_alt', 0)

                            # Also try to get autopilot altitude setting
                            ap_alt = self._safe_get("AUTOPILOT_ALTITUDE_LOCK_VAR") if self.sim_connected else None

                            # Use autopilot altitude if set and higher than mission cruise
                            if ap_alt and ap_alt > target_cruise:
                                target_cruise = ap_alt

                            # Smart announcement based on altitude
                            if target_cruise > 0:
                                diff = target_cruise - current_alt
                                tolerance = 500  # 500 ft tolerance

                                if abs(diff) < tolerance:
                                    # At target altitude
                                    if target_cruise >= 18000:
                                        fl = int(target_cruise / 100)
                                        self.voice.speak(f"Niveau de croisiere flight level {fl} atteint")
                                    else:
                                        self.voice.speak(f"Niveau de croisiere {int(target_cruise)} pieds atteint")
                                    self._last_cruise_callout = current_time
                                elif diff > 1000:
                                    # Still climbing, announce current level
                                    if current_alt >= 18000:
                                        fl = int(current_alt / 100)
                                        target_fl = int(target_cruise / 100)
                                        self.voice.speak(f"Passing flight level {fl}, climbing to flight level {target_fl}")
                                    else:
                                        self.voice.speak(f"Passing {int(current_alt)} pieds, montee vers {int(target_cruise)}")
                                    self._last_cruise_callout = current_time
                                # If descending from above target, don't announce (controlled descent)
                            else:
                                # No target altitude set - use simple announcement
                                self.voice.speak("Niveau de croisiere atteint")
                                self._last_cruise_callout = current_time

                    elif new_phase == FlightPhase.LANDING_ROLL:
                        self.voice.speak("Atterrissage effectue")
                        # Reset cruise callout for next flight
                        self._last_cruise_callout = 0

    def _is_in_menu(self) -> bool:
        """Check if simulator is in menu (phase unknown or sim not running)"""
        if hasattr(self, 'phase_detector') and self.phase_detector:
            current_phase = self.phase_detector.current_phase
            if current_phase and current_phase.name.lower() == 'unknown':
                return True
        return False

    def _on_voice_command(self, transcription: str):
        """Callback when voice is transcribed - send to copilot LLM"""
        if not transcription or len(transcription.strip()) < 2:
            logger.debug("Empty or too short transcription, ignoring")
            return

        # Filter out noise/garbage transcriptions
        noise_phrases = ['sous-titrage', 'st\'', 'merci', '...']
        if any(noise in transcription.lower() for noise in noise_phrases) and len(transcription) < 30:
            logger.debug(f"Transcription filtered as noise: {transcription}")
            return

        logger.info(f"Voice command received: {transcription}")

        # Don't process when in menu
        if self._is_in_menu():
            logger.debug("Voice command ignored (in menu)")
            return

        if not COPILOT_AVAILABLE or not hasattr(self, 'copilot_llm'):
            logger.warning("Copilot LLM not available")
            return

        # Update LLM context with current flight data
        self._update_llm_context()

        # Send to LLM in a thread to avoid blocking
        def process_voice():
            try:
                response = self.copilot_llm.query(transcription)
                if response and hasattr(self, 'voice') and self.voice:
                    logger.info(f"Copilot response: {response}")
                    self.voice.speak(response)
            except Exception as e:
                logger.error(f"Error processing voice command: {e}")
                import traceback
                logger.error(traceback.format_exc())

        threading.Thread(target=process_voice, daemon=True).start()

    def _update_llm_context(self):
        """Update copilot LLM with current flight context"""
        if not COPILOT_AVAILABLE or not hasattr(self, 'copilot_llm'):
            return

        try:
            from copilot.llm import FlightContext

            # Get data from snapshot (non-blocking)
            if OPTIMIZATION_AVAILABLE and hasattr(self.sim, 'get_snapshot'):
                snap = self.sim.get_snapshot()
                altitude = snap.altitude
                airspeed = snap.airspeed
                heading = snap.heading
                vertical_speed = snap.vertical_speed
                latitude = snap.latitude
                longitude = snap.longitude
                fuel_gal = snap.fuel_quantity_gal
            else:
                altitude = self._safe_get("PLANE_ALTITUDE") or 0
                airspeed = self._safe_get("AIRSPEED_INDICATED") or 0
                heading = self._safe_get("PLANE_HEADING_DEGREES_TRUE") or 0
                vertical_speed = self._safe_get("VERTICAL_SPEED") or 0
                latitude = self._safe_get("PLANE_LATITUDE") or 0
                longitude = self._safe_get("PLANE_LONGITUDE") or 0
                fuel_gal = (self._safe_get("FUEL_TOTAL_QUANTITY_WEIGHT") or 0) / 6.7
                snap = None

            # Get phase
            phase = "unknown"
            if hasattr(self, 'phase_detector') and self.phase_detector:
                p = self.phase_detector.current_phase
                if p:
                    phase = p.value

            # Get mission info
            dep_icao = getattr(self, 'current_mission', {}).get('departure', {}).get('icao', '') if hasattr(self, 'current_mission') and self.current_mission else ""
            dep_name = getattr(self, 'current_mission', {}).get('departure', {}).get('name', '') if hasattr(self, 'current_mission') and self.current_mission else ""
            arr_icao = getattr(self, 'current_mission', {}).get('arrival', {}).get('icao', '') if hasattr(self, 'current_mission') and self.current_mission else ""
            arr_name = getattr(self, 'current_mission', {}).get('arrival', {}).get('name', '') if hasattr(self, 'current_mission') and self.current_mission else ""
            distance = getattr(self, 'current_mission', {}).get('distance', 0) if hasattr(self, 'current_mission') and self.current_mission else 0

            # Build context with navigation data
            context = FlightContext(
                latitude=latitude,
                longitude=longitude,
                altitude_ft=altitude,
                heading=heading,
                flight_phase=phase,
                airspeed_kts=airspeed,
                vertical_speed_fpm=vertical_speed,
                fuel_remaining_gal=fuel_gal,
                departure_icao=dep_icao,
                departure_name=dep_name,
                arrival_icao=arr_icao,
                arrival_name=arr_name,
                distance_nm=distance,
                aircraft_title=self.aircraft_info.get('title', ''),
                aircraft_category=self.aircraft_info.get('category', ''),
                # Navigation data from snapshot
                next_wp_distance_nm=snap.gps_wp_distance_nm if snap else 0,
                next_wp_bearing=snap.gps_wp_bearing if snap else 0,
                next_wp_eta_minutes=snap.gps_wp_eta_seconds / 60 if snap else 0,
                dest_eta_minutes=snap.gps_dest_eta_seconds / 60 if snap else 0,
                dest_ete_minutes=snap.gps_dest_ete_seconds / 60 if snap else 0,
                flight_plan_wp_count=snap.gps_wp_count if snap else 0,
                flight_plan_wp_index=snap.gps_wp_index if snap else 0,
                # Autopilot
                ap_active=snap.autopilot_master if snap else False,
                ap_hdg_mode=snap.ap_hdg_lock if snap else False,
                ap_hdg_selected=snap.ap_hdg_selected if snap else 0,
                ap_alt_mode=snap.ap_alt_lock if snap else False,
                ap_alt_selected=snap.ap_alt_selected if snap else 0,
                ap_spd_mode=snap.ap_spd_lock if snap else False,
                ap_spd_selected=snap.ap_spd_selected if snap else 0,
                ap_vs_mode=snap.ap_vs_lock if snap else False,
                ap_vs_selected=snap.ap_vs_selected if snap else 0,
                ap_nav_mode=snap.ap_nav_lock if snap else False,
                ap_appr_mode=snap.autopilot_approach if snap else False,
                # Radio
                nav1_freq=snap.nav1_frequency if snap else 0,
                nav1_dme=snap.nav1_dme_nm if snap else 0,
                com1_freq=snap.com1_frequency if snap else 0,
            )

            self.copilot_llm.update_context(context)

        except Exception as e:
            logger.error(f"Error updating LLM context: {e}")

    def _on_callout(self, callout):
        """Callback when a callout is triggered - speak it"""
        if not COPILOT_AVAILABLE:
            return

        if not self.config.get('copilot_enabled', True):
            return

        if not self.config.get('voice_enabled', True):
            return

        # Don't speak callouts when no mission is active (user is in menu or hasn't started)
        if not self.mission_active:
            logger.debug(f"Callout skipped (no mission active): {callout.text}")
            return

        # Don't speak callouts when in menu
        if self._is_in_menu():
            logger.debug(f"Callout skipped (in menu): {callout.text}")
            return

        # Speak the callout with priority (interrupts if priority >= 2)
        if hasattr(self, 'voice') and self.voice:
            priority = callout.priority >= 2
            self.voice.speak(callout.text, priority=priority)
            logger.info(f"Callout spoken: {callout.text}")

    def _on_checklist_event(self, event: str, data):
        """Callback for checklist events - speak items and completions"""
        if not COPILOT_AVAILABLE:
            return

        if not self.config.get('copilot_enabled', True):
            return

        if not self.config.get('voice_enabled', True):
            return

        if not hasattr(self, 'voice') or not self.voice:
            return

        # Don't speak checklist events when in menu
        if self._is_in_menu():
            logger.debug(f"Checklist event skipped (in menu): {event}")
            return

        if event == "checklist_started":
            checklist = data
            self.voice.speak(f"Checklist {checklist.name}. {checklist.items[0].challenge}... {checklist.items[0].response}")
            logger.info(f"Checklist started: {checklist.name}")

        elif event == "item_checked":
            item = data
            # Speak next item if checklist is still active
            if hasattr(self, 'checklists') and self.checklists.active_checklist:
                next_item = self.checklists.active_checklist.current_item
                if next_item:
                    self.voice.speak(f"{next_item.challenge}... {next_item.response}")
            logger.info(f"Checklist item checked: {item.challenge}")

        elif event == "item_skipped":
            item = data
            # Speak next item
            if hasattr(self, 'checklists') and self.checklists.active_checklist:
                next_item = self.checklists.active_checklist.current_item
                if next_item:
                    self.voice.speak(f"{next_item.challenge}... {next_item.response}")
            logger.info(f"Checklist item skipped: {item.challenge}")

        elif event == "checklist_completed":
            checklist = data
            self.voice.speak(f"Checklist {checklist.name} terminee.")
            logger.info(f"Checklist completed: {checklist.name}")

        elif event == "checklist_cancelled":
            self.voice.speak("Checklist annulee.")
            logger.info("Checklist cancelled")

        elif event == "item_auto_checked":
            result = data
            # Auto-verified item - announce result
            if result.get('passed'):
                self.voice.speak(f"{result['challenge']}... {result['response']}. Verifie.")
            logger.info(f"Checklist item auto-checked: {result['challenge']} - {'OK' if result['passed'] else 'FAIL'}")

        elif event == "item_next":
            # Next item announced after auto-check
            item = data
            self.voice.speak(f"{item.challenge}... {item.response}")

    def _on_checklist_start(self):
        """Handle checklist Start button click"""
        if not hasattr(self, 'checklist_dropdown'):
            return

        # Map dropdown display name to checklist ID
        name_to_id = {
            "Before Start": "before_start",
            "Before Takeoff": "before_takeoff",
            "Approach": "approach",
            "Before Landing": "before_landing",
            "After Landing": "after_landing",
            "Shutdown": "shutdown"
        }

        selected = self.checklist_dropdown.get()
        checklist_id = name_to_id.get(selected)
        if checklist_id:
            self.start_checklist(checklist_id)

    def _get_sim_data_dict(self) -> Dict[str, float]:
        """
        Get current SimConnect data as a dictionary for checklist auto-verification
        Returns dict mapping variable names to their current values
        """
        if not self.sim_connected:
            return {}

        # List of SimConnect variables needed for checklist verification
        variables = [
            "BRAKE_PARKING_POSITION",
            "GENERAL_ENG_THROTTLE_LEVER_POSITION:1",
            "GENERAL_ENG_MIXTURE_LEVER_POSITION:1",
            "ELECTRICAL_MASTER_BATTERY",
            "AVIONICS_MASTER_SWITCH",
            "LIGHT_BEACON",
            "LIGHT_LANDING",
            "LIGHT_STROBE",
            "LIGHT_NAV",
            "LIGHT_TAXI",
            "FUEL_TOTAL_QUANTITY_WEIGHT",
            "FLAPS_HANDLE_PERCENT",
            "TRANSPONDER_STATE",
            "CANOPY_OPEN",
            "GEAR_HANDLE_POSITION",
            "AIRSPEED_INDICATED",
            "AUTOPILOT_MASTER",
            "GENERAL_ENG_COMBUSTION:1",
        ]

        data = {}
        for var in variables:
            value = self._safe_get(var)
            if value is not None:
                data[var] = value

        return data

    def _run_auto_checklist(self):
        """Run the selected checklist automatically using SimConnect data"""
        if not COPILOT_AVAILABLE or not hasattr(self, 'checklists'):
            return

        if not self.sim_connected:
            if hasattr(self, 'voice') and self.voice:
                self.voice.speak("SimConnect non connecte. Impossible de verifier automatiquement.")
            return

        # Get checklist ID from dropdown
        name_to_id = {
            "Before Start": "before_start",
            "Before Takeoff": "before_takeoff",
            "Approach": "approach",
            "Before Landing": "before_landing",
            "After Landing": "after_landing",
            "Shutdown": "shutdown"
        }

        selected = self.checklist_dropdown.get()
        checklist_id = name_to_id.get(selected)
        if not checklist_id:
            return

        # Get current sim data
        sim_data = self._get_sim_data_dict()

        # Define speak callback
        def speak(text):
            if hasattr(self, 'voice') and self.voice and self.config.get('voice_enabled', True):
                self.voice.speak(text)

        # Run auto checklist in a thread to avoid blocking UI
        def run_thread():
            speak(f"Verification automatique checklist {selected}")

            # Small delay for TTS
            import time
            time.sleep(1.5)

            summary = self.checklists.run_auto_checklist(
                checklist_id,
                sim_data,
                speak_callback=speak,
                delay_between_items=1.5
            )

            # Update UI with results
            self.after(0, lambda: self._show_auto_checklist_results(summary))

        threading.Thread(target=run_thread, daemon=True).start()

    def _show_auto_checklist_results(self, summary: Dict):
        """Display auto-checklist results"""
        if not summary:
            return

        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        manual = summary.get('manual', 0)
        total = summary.get('total_items', 0)

        result_text = f"Checklist: {passed}/{total} OK"
        if failed > 0:
            result_text += f", {failed} a verifier"
        if manual > 0:
            result_text += f", {manual} manuels"

        # Show in copilot response area
        if hasattr(self, 'copilot_response'):
            self.copilot_response.configure(text=result_text)

        logger.info(f"Auto-checklist result: {summary}")

    def start_checklist(self, checklist_id: str):
        """Start a checklist by ID - can be called from UI or voice command"""
        if not COPILOT_AVAILABLE or not hasattr(self, 'checklists'):
            return

        self.checklists.start_checklist(checklist_id)

    def check_checklist_item(self):
        """Confirm/check current checklist item - responds to 'check' or 'roger' voice command"""
        if not COPILOT_AVAILABLE or not hasattr(self, 'checklists'):
            return

        self.checklists.check_item()

    def skip_checklist_item(self):
        """Skip current checklist item"""
        if not COPILOT_AVAILABLE or not hasattr(self, 'checklists'):
            return

        self.checklists.skip_item()

    def cancel_checklist(self):
        """Cancel current checklist"""
        if not COPILOT_AVAILABLE or not hasattr(self, 'checklists'):
            return

        self.checklists.cancel_checklist()

    def _init_microphones(self):
        """Initialize microphone dropdown with available devices"""
        if not COPILOT_AVAILABLE or not hasattr(self, 'voice') or self.voice is None:
            self.mic_dropdown.configure(values=["No Voice System"])
            return

        try:
            # Get available microphones
            devices = self.voice.get_available_microphones()
            if devices:
                self.mic_devices = devices
                # Create display names (truncated)
                display_names = [f"{name[:35]}" for idx, name in devices]
                self.mic_dropdown.configure(values=display_names)

                # Try to restore preferred microphone from config
                preferred_mic = self.config.get('preferred_microphone', '')
                selected_idx = 0  # Default to first mic

                if preferred_mic:
                    # Search for preferred mic in available devices
                    for i, (idx, name) in enumerate(devices):
                        if preferred_mic.lower() in name.lower():
                            selected_idx = i
                            logger.info(f"Found preferred microphone: {name}")
                            break

                # Select the microphone
                self.mic_dropdown.set(display_names[selected_idx])
                device_index, device_name = devices[selected_idx]
                self.voice.set_microphone(device_index)
                logger.info(f"Detected {len(devices)} microphones")
            else:
                self.mic_dropdown.configure(values=["No mic found"])
        except Exception as e:
            logger.error(f"Error initializing mics: {e}")
            self.mic_dropdown.configure(values=["Error"])

    def _on_mic_selected(self, selection):
        """Handle microphone selection from dropdown"""
        if not hasattr(self, 'mic_devices') or not self.mic_devices:
            return

        # Find the selected device index
        try:
            display_names = [f"{name[:35]}" for idx, name in self.mic_devices]
            selected_index = display_names.index(selection)
            device_index, device_name = self.mic_devices[selected_index]
            self.voice.set_microphone(device_index)
            logger.info(f"Microphone changed to: {device_name}")

            # Save preference to config (use a keyword from the name for matching)
            # Extract a unique identifier from the mic name
            self.config['preferred_microphone'] = device_name
            self._save_config()
            logger.info(f"Saved preferred microphone: {device_name}")

            # Clear the level indicator
            if hasattr(self, 'mic_level_label'):
                self.mic_level_label.configure(text="")
        except (ValueError, IndexError) as e:
            logger.error(f"Error selecting mic: {e}")

    def _test_microphone(self):
        """Test selected microphone and show level"""
        if not hasattr(self, 'voice') or self.voice is None:
            return

        try:
            self.mic_level_label.configure(text="Testing...", text_color="#FFAA00")
            self.update()

            # Get single level reading
            level = self.voice.get_mic_level_once()

            if level >= 0:
                # Show level with color
                if level > 0.1:
                    text = f"OK ({level:.2%})"
                    color = "#44FF44"
                elif level > 0.001:
                    text = f"Low ({level:.2%})"
                    color = "#FFAA00"
                else:
                    text = "Silent"
                    color = "#FF6666"
                self.mic_level_label.configure(text=text, text_color=color)
            else:
                self.mic_level_label.configure(text="Error", text_color="#FF4444")
        except Exception as e:
            logger.error(f"Mic test error: {e}")
            self.mic_level_label.configure(text="Error", text_color="#FF4444")

    # Sentinel value to indicate "command handled, no response needed"
    _CHECKLIST_HANDLED = "__HANDLED__"

    def _process_checklist_command(self, command: str) -> Optional[str]:
        """
        Process checklist-related voice/text commands
        Returns:
            - Response string if command was handled and needs to be spoken
            - _CHECKLIST_HANDLED if command was handled (callback will speak)
            - None if not a checklist command (should continue to LLM)
        """
        if not hasattr(self, 'checklists'):
            return None

        cmd = command.lower().strip()

        # Checklist mappings (voice command -> checklist ID)
        checklist_triggers = {
            ('before start', 'avant demarrage', 'pre start'): 'before_start',
            ('before takeoff', 'avant decollage', 'pre takeoff'): 'before_takeoff',
            ('approach', 'approche'): 'approach',
            ('before landing', 'avant atterrissage', 'pre landing'): 'before_landing',
            ('after landing', 'apres atterrissage', 'post landing'): 'after_landing',
            ('shutdown', 'arret', 'parking'): 'shutdown',
        }

        # Check if starting a checklist
        if 'checklist' in cmd or 'check list' in cmd:
            for triggers, checklist_id in checklist_triggers.items():
                for trigger in triggers:
                    if trigger in cmd:
                        self.start_checklist(checklist_id)
                        return self._CHECKLIST_HANDLED  # Callback speaks the first item
            # Generic "checklist" without specifying which one
            return "Checklists disponibles: before start, before takeoff, approach, before landing, after landing, shutdown"

        # If a checklist is active, handle confirmation/skip commands
        if self.checklists.active_checklist:
            # Confirmation words
            if any(word in cmd for word in ['check', 'roger', 'ok', 'set', 'confirme', 'verifie', 'fait', 'done']):
                self.check_checklist_item()
                return self._CHECKLIST_HANDLED  # Callback speaks the next item

            # Skip words
            if any(word in cmd for word in ['skip', 'next', 'suivant', 'passer']):
                self.skip_checklist_item()
                return self._CHECKLIST_HANDLED

            # Cancel words
            if any(word in cmd for word in ['cancel', 'annule', 'stop checklist', 'arrete']):
                self.cancel_checklist()
                return self._CHECKLIST_HANDLED  # Callback speaks cancellation

            # Repeat current item
            if any(word in cmd for word in ['repeat', 'repete', 'again', 'encore']):
                current = self.checklists.active_checklist.current_item
                if current:
                    return f"{current.challenge}... {current.response}"

        return None  # Not a checklist command

    def _listen_and_ask_copilot(self):
        """Listen for voice input and ask the copilot"""
        if not COPILOT_AVAILABLE:
            return

        if not hasattr(self, 'voice') or not self.voice:
            self.copilot_response.configure(text="Système vocal non disponible")
            return

        if not self.config.get('groq_api_key'):
            self.copilot_response.configure(text="Clé Groq API requise pour la reconnaissance vocale")
            return

        # Update UI to show we're listening
        self.copilot_response.configure(text="🎤 Écoute en cours... (parlez maintenant)")
        self.copilot_mic_btn.configure(state="disabled", text="🔴 Écoute...")
        self.update()

        def listen_thread():
            try:
                # Use the voice system's record and transcribe
                text = self.voice._record_and_transcribe()

                if text:
                    logger.info(f"Voice input: {text}")
                    # Put the text in the entry and trigger ask
                    self.after(0, lambda: self._handle_voice_input(text))
                else:
                    self.after(0, lambda: self.copilot_response.configure(text="Aucune parole détectée"))
                    self.after(0, lambda: self.copilot_mic_btn.configure(state="normal", text="🎤 Mic"))

            except Exception as e:
                logger.error(f"Voice listen error: {e}")
                self.after(0, lambda: self.copilot_response.configure(text=f"Erreur: {e}"))
                self.after(0, lambda: self.copilot_mic_btn.configure(state="normal", text="🎤 Mic"))

        threading.Thread(target=listen_thread, daemon=True).start()

    def _handle_voice_input(self, text: str):
        """Handle voice input after transcription"""
        # Reset button
        self.copilot_mic_btn.configure(state="normal", text="🎤 Mic")

        # Show what was heard
        self.copilot_response.configure(text=f"🎤 \"{text}\"")
        self.update()

        # Put in entry for visibility
        self.copilot_entry.delete(0, 'end')
        self.copilot_entry.insert(0, text)

        # Process the command (same as _ask_copilot but with text parameter)
        self._process_voice_question(text)

    def _process_voice_question(self, question: str):
        """Process a voice question (shared logic with _ask_copilot)"""
        if not question:
            return

        # First, check for checklist commands
        checklist_response = self._process_checklist_command(question)
        if checklist_response is not None:
            if checklist_response == self._CHECKLIST_HANDLED:
                return
            self.copilot_response.configure(text=checklist_response)
            if self.config.get('voice_enabled', True) and hasattr(self, 'voice'):
                self.voice.speak(checklist_response)
            return

        # Update copilot context with current flight data (uses snapshot)
        self._update_llm_context()

        # Show "thinking" message
        self.copilot_response.configure(text="Réflexion en cours...")
        self.update()

        # Ask copilot in a thread
        def ask_thread():
            try:
                response = self.copilot_llm.process_voice_command(question)
                self.after(0, lambda: self.copilot_response.configure(text=response))

                if self.config.get('voice_enabled', True) and hasattr(self, 'voice'):
                    self.voice.speak(response)
            except Exception as e:
                logger.error(f"Copilot query error: {e}")
                self.after(0, lambda: self.copilot_response.configure(text=f"Erreur: {e}"))

        threading.Thread(target=ask_thread, daemon=True).start()

    def _ask_copilot(self):
        """Ask a question to the AI copilot"""
        if not COPILOT_AVAILABLE:
            return

        question = self.copilot_entry.get().strip()
        if not question:
            return

        # Clear input
        self.copilot_entry.delete(0, 'end')

        # First, check for checklist commands
        checklist_response = self._process_checklist_command(question)
        if checklist_response is not None:
            # _CHECKLIST_HANDLED means callback already handles speech
            if checklist_response == self._CHECKLIST_HANDLED:
                return
            # Otherwise, display and speak the response
            self.copilot_response.configure(text=checklist_response)
            if self.config.get('voice_enabled', True) and hasattr(self, 'voice'):
                self.voice.speak(checklist_response)
            return

        # Update copilot context with current flight data (uses snapshot)
        self._update_llm_context()

        # Show "thinking" message
        self.copilot_response.configure(text="Réflexion en cours...")
        self.update()

        # Ask copilot in a thread to avoid freezing UI
        def ask_thread():
            try:
                response = self.copilot_llm.process_voice_command(question)
                self.after(0, lambda: self.copilot_response.configure(text=response))

                # Also speak the response if voice is enabled
                if self.config.get('voice_enabled', True) and hasattr(self, 'voice'):
                    self.voice.speak(response)
            except Exception as e:
                logger.error(f"Copilot query error: {e}")
                self.after(0, lambda: self.copilot_response.configure(text=f"Erreur: {e}"))

        threading.Thread(target=ask_thread, daemon=True).start()

    def _generate_mission(self):
        """Generate a new mission"""
        # Stop pattern training if active
        if self.pattern_training_active:
            self._stop_pattern_training()

        self._update_aircraft_info()

        self.mission_text.configure(text="Loading aviation data...\n(airports, weather, runways)")
        self.update()

        # Use Aviation API
        if AVIATION_API_AVAILABLE:
            category = self.aircraft_info.get('category', 'light_piston')

            # Use user-configured distance range
            user_min = self.dist_min_var.get()
            user_max = self.dist_max_var.get()

            mission_data = prepare_mission_data(
                min_distance=user_min,
                max_distance=user_max,
                aircraft_category=category
            )

            if mission_data:
                departure = {
                    'icao': mission_data['departure']['icao'],
                    'name': mission_data['departure']['name'],
                    'lat': mission_data['departure']['lat'],
                    'lon': mission_data['departure']['lon'],
                    'runway': mission_data['departure'].get('runway'),
                    'weather': mission_data['departure'].get('weather')
                }
                arrival = {
                    'icao': mission_data['arrival']['icao'],
                    'name': mission_data['arrival']['name'],
                    'lat': mission_data['arrival']['lat'],
                    'lon': mission_data['arrival']['lon'],
                    'runway': mission_data['arrival'].get('runway'),
                    'weather': mission_data['arrival'].get('weather')
                }
                distance = mission_data['distance_nm']
            else:
                self.mission_text.configure(text="Error: Could not generate mission")
                return
        else:
            if len(self.airports) < 2:
                self.mission_text.configure(text="Error: Not enough airports")
                return
            dep_local, arr_local = random.sample(self.airports, 2)
            departure = {**dep_local, 'runway': None, 'weather': None}
            arrival = {**arr_local, 'runway': None, 'weather': None}
            distance = calculate_distance_nm(departure['lat'], departure['lon'], arrival['lat'], arrival['lon'])

        # Calculate cruise altitude for this mission
        category = self.aircraft_info.get("category", "light_piston")
        profile = AIRCRAFT_PROFILES.get(category, AIRCRAFT_PROFILES["light_piston"])
        cruise_alt = calculate_optimal_altitude(distance, profile["max_alt"])

        self.current_mission = {
            'departure': departure,
            'arrival': arrival,
            'distance': distance,
            'cruise_alt': cruise_alt  # Store target cruise altitude for smart copilot
        }
        self.current_constraint = get_random_constraint()

        # Generate flight plan with proper departure/approach procedures
        self.current_flightplan = generate_flightplan_pln(
            departure, arrival,
            aircraft_info=self.aircraft_info,
            config=self.config
        )

        # Auto-copy PLN
        if self.auto_copy_var.get() and self.current_flightplan:
            dest_folder = self.pln_path_entry.get()
            if dest_folder and os.path.exists(dest_folder):
                try:
                    dest_path = Path(dest_folder) / Path(self.current_flightplan).name
                    shutil.copy2(self.current_flightplan, dest_path)
                    logger.info(f"PLN copied to: {dest_path}")
                except Exception as e:
                    logger.error(f"PLN copy error: {e}")

        # Update UI
        dep_rwy = departure.get('runway')
        dep_rwy_str = f"RWY {dep_rwy['ident']}" if dep_rwy else "RWY auto"
        arr_rwy = arrival.get('runway')
        arr_rwy_str = f"RWY {arr_rwy['ident']}" if arr_rwy else "RWY auto"

        dep_weather = departure.get('weather', {})
        arr_weather = arrival.get('weather', {})
        dep_wind = dep_weather.get('wind_description', '?') if dep_weather else '?'
        arr_wind = arr_weather.get('wind_description', '?') if arr_weather else '?'

        mission_str = (
            f"Departure: {departure['name'][:30]} ({departure['icao']})\n"
            f"   {dep_rwy_str} | Wind: {dep_wind}\n"
            f"Arrival: {arrival['name'][:30]} ({arrival['icao']})\n"
            f"   {arr_rwy_str} | Wind: {arr_wind}\n"
            f"Distance: {distance:.0f} nm"
        )
        self.mission_text.configure(text=mission_str)

        diff_colors = {"easy": "#00AA00", "normal": "#FFAA00", "hard": "#FF4444"}
        diff = self.current_constraint.get('difficulty', 'normal')
        self.constraint_text.configure(
            text=f"{self.current_constraint['name']}: {self.current_constraint['value']} {self.current_constraint['unit']} ({diff.upper()})",
            text_color=diff_colors.get(diff, "#FF6666")
        )

        # Initialize mission state
        self.mission_active = True
        self.was_on_ground = True
        self.penalty_cooldown = 0
        self.departure_lat = departure['lat']
        self.departure_lon = departure['lon']
        self.arrival_lat = arrival['lat']
        self.arrival_lon = arrival['lon']
        self.total_distance = distance
        self.mission_started = False
        self.mission_progress = 0.0

        self.progress_bar.set(0)
        self.progress_bar.configure(progress_color="#4A90D9")
        self.progress_label.configure(text="0% - At parking - Ready for departure")

        # Reset payment tracking
        self.takeoff_time = None
        self.landing_time = None
        self.flight_time_hours = 0
        self.constraint_violations = 0
        self.max_vs_landing = 0
        self.had_overspeed = False

        current_hour = datetime.now().hour
        self.is_night_flight = current_hour >= 21 or current_hour < 6
        self.is_weekend = datetime.now().weekday() >= 5
        self.is_bad_weather = False

        # Start V2 systems
        if COPILOT_AVAILABLE and self.config.get('copilot_enabled', True):
            self.debrief.start_recording()

            # Reset copilot systems for new mission
            if hasattr(self, 'callouts') and self.callouts:
                self.callouts.reset()
            if hasattr(self, 'phase_detector') and self.phase_detector:
                self.phase_detector.reset()

                # Set departure and arrival for runway detection
                dep_rwy = departure.get('runway')
                dep_rwy_heading = None
                if dep_rwy and dep_rwy.get('ident'):
                    try:
                        # Extract runway number (e.g., "06L" -> 6, "24R" -> 24)
                        rwy_num = ''.join(c for c in dep_rwy['ident'] if c.isdigit())
                        if rwy_num:
                            dep_rwy_heading = int(rwy_num) * 10
                    except:
                        pass
                self.phase_detector.set_departure(departure['lat'], departure['lon'], dep_rwy_heading)

                arr_rwy = arrival.get('runway')
                arr_rwy_heading = None
                if arr_rwy and arr_rwy.get('ident'):
                    try:
                        rwy_num = ''.join(c for c in arr_rwy['ident'] if c.isdigit())
                        if rwy_num:
                            arr_rwy_heading = int(rwy_num) * 10
                    except:
                        pass
                self.phase_detector.set_arrival(arrival['lat'], arrival['lon'], arr_rwy_heading)

            if self.config.get('voice_enabled', True):
                self.voice.speak(f"Mission generee. Depart de {departure['icao']} vers {arrival['icao']}. Distance {distance:.0f} miles nautiques.")

        if UTILS_AVAILABLE:
            self.flight_recorder.start_recording(departure, arrival, self.aircraft_info)

        # Update stats display
        category = self.aircraft_info.get('category', 'light_piston')
        hourly_rate = PILOT_HOURLY_RATES.get(category, 55)
        self.stats_label.configure(
            text=f"Missions: {self.missions_completed} | Rate: {hourly_rate}EUR/h ({category})"
        )

        play_mission_sound()
        logger.info(f"Mission: {departure['icao']} -> {arrival['icao']} - {distance:.0f} nm")

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in nautical miles"""
        # Protection against None values
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return 0.0

        import math
        R = 3440.065  # Earth radius in nautical miles

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def _update_loop(self):
        """
        Main update loop - OPTIMIZED VERSION
        Uses snapshot from background thread - NO BLOCKING SimConnect calls!
        """
        self.update_count += 1

        # Refresh career panel every 5 seconds
        if self.update_count % 5 == 0:
            self._refresh_career_panel()

        # Check joystick PTT button (non-blocking)
        self._check_joystick_ptt()

        if self.sim_connected and OPTIMIZATION_AVAILABLE:
            try:
                # =====================================================
                # GET SNAPSHOT - NON-BLOCKING read from background cache
                # This is the KEY optimization - no SimConnect calls here!
                # =====================================================
                snap = self.sim.get_snapshot()

                # Extract data from snapshot (already converted to proper units)
                altitude = snap.altitude
                altitude_agl = snap.altitude_agl
                bank_angle = snap.bank_angle
                vertical_speed = snap.vertical_speed
                on_ground = snap.on_ground
                airspeed = snap.get_effective_airspeed()
                latitude = snap.latitude
                longitude = snap.longitude
                heading = snap.heading
                ground_speed = snap.ground_speed
                pitch = snap.pitch
                parking_brake = snap.parking_brake
                eng_combustion = snap.engine_running
                gear_down = snap.gear_down
                throttle_position = snap.throttle_percent
                spoilers_position = snap.spoilers_percent
                light_beacon = snap.light_beacon
                light_landing = snap.light_landing
                light_taxi = snap.light_taxi
                in_parking_state = snap.in_parking_state
                flaps_percent = snap.flaps_percent
                sim_running = snap.sim_running

                # V2 Enhanced variables
                stall_warning = snap.stall_warning
                overspeed_warning = snap.overspeed_warning
                g_force = snap.g_force
                touchdown_velocity = snap.touchdown_velocity
                engine_rpm_pct = snap.engine_rpm_percent
                engine_oil_temp = snap.engine_oil_temp
                total_fuel_flow_gph = snap.fuel_flow_gph_1 + snap.fuel_flow_gph_2
                density_altitude = snap.density_altitude
                structural_ice_pct = snap.structural_ice_pct
                pitot_ice_pct = snap.pitot_ice_pct
                autopilot_master = snap.autopilot_master
                autopilot_approach = snap.autopilot_approach
                autopilot_glideslope = snap.autopilot_glideslope

                # Passenger estimation from snapshot
                self._estimated_passengers = snap.estimated_passengers

                # --- Track if aircraft has flown (for landing detection) ---
                if not hasattr(self, '_flight_start_pos'):
                    self._flight_start_pos = None
                    self._has_flown_distance = False

                # Record position when first airborne
                if not on_ground and self._flight_start_pos is None:
                    if latitude != 0 and longitude != 0:
                        self._flight_start_pos = (latitude, longitude)
                        self._has_flown_distance = False

                # Check if we've flown at least 1nm
                if self._flight_start_pos and not self._has_flown_distance:
                    if latitude != 0 and longitude != 0:
                        start_lat, start_lon = self._flight_start_pos
                        dist = self._haversine(start_lat, start_lon, latitude, longitude)
                        if dist > 1.0:
                            self._has_flown_distance = True

                # Update display (lightweight string operations)
                parts = []
                parts.append(f"Alt: {altitude:.0f} ft")
                parts.append(f"Bank: {bank_angle:.1f}°")
                parts.append(f"VS: {vertical_speed:.0f} fpm")

                if on_ground:
                    parts.append(f"GS: {ground_speed:.0f} kts")
                else:
                    parts.append(f"IAS: {airspeed:.0f} kts")

                self.data_text.configure(text=" | ".join(parts))
                self.debug_text.configure(text=f"[AGL: {altitude_agl:.0f}ft] Lat: {latitude:.4f} Lon: {longitude:.4f}")

                # Update V2 systems
                if COPILOT_AVAILABLE and self.config.get('copilot_enabled', True):

                    # Create FlightState from snapshot data (already converted)
                    flight_state = FlightState(
                        sim_running=sim_running,
                        on_ground=on_ground,
                        altitude_agl=altitude_agl,
                        altitude_msl=altitude,
                        airspeed=airspeed,
                        ground_speed=ground_speed,
                        vertical_speed=vertical_speed,
                        pitch=pitch,
                        heading=heading,
                        has_flown=getattr(self, '_has_flown_distance', False),
                        engine_running=eng_combustion,
                        parking_brake=parking_brake,
                        gear_down=gear_down,
                        flaps_percent=flaps_percent,
                        throttle_percent=throttle_position,
                        spoilers_percent=spoilers_position,
                        light_beacon=light_beacon,
                        light_landing=light_landing,
                        light_taxi=light_taxi,
                        in_parking_state=in_parking_state,
                        latitude=latitude,
                        longitude=longitude,
                        # V2 Enhanced variables
                        stall_warning=stall_warning,
                        overspeed_warning=overspeed_warning,
                        g_force=g_force,
                        touchdown_velocity=touchdown_velocity,
                        engine_rpm_percent=engine_rpm_pct,
                        engine_oil_temp=engine_oil_temp,
                        fuel_flow_gph=total_fuel_flow_gph,
                        density_altitude=density_altitude,
                        structural_ice_pct=structural_ice_pct,
                        pitot_ice_pct=pitot_ice_pct,
                        autopilot_master=autopilot_master,
                        autopilot_approach=autopilot_approach,
                        autopilot_glideslope=autopilot_glideslope
                    )

                    # Update phase detector with FlightState
                    self.phase_detector.update(flight_state)

                    # Check callouts (skip when in menu/unknown phase)
                    phase_name = self.phase_detector.current_phase.name
                    if phase_name.lower() != 'unknown':
                        triggered_callouts = self.callouts.check_callouts(
                            flight_phase=phase_name,
                            altitude_agl=altitude_agl,
                            altitude_msl=altitude,
                            airspeed=airspeed,
                            vertical_speed=vertical_speed,
                            on_ground=on_ground,
                            gear_down=gear_down
                        )

                        # Handle touchdown callout - announce landing rating
                        for callout in triggered_callouts:
                            if callout.id == "touchdown":
                                rating, score = self.callouts.get_landing_rating(vertical_speed)
                                if hasattr(self, 'voice') and self.voice:
                                    self.voice.speak(rating, priority=True)

                    # Check for pilot errors (skip if no mission active, in menu, PREFLIGHT, or relaxed mode)
                    relaxed_mode = self.config.get('relaxed_mode', False)
                    if hasattr(self, 'error_detector') and self.error_detector.enabled and not relaxed_mode and self.mission_active:
                        if phase_name.lower() not in ['unknown', 'preflight', 'parked']:
                            errors = self.error_detector.check_errors(
                                flight_phase=phase_name.lower(),
                                altitude_agl=altitude_agl,
                                altitude_msl=altitude,
                                airspeed=airspeed,
                                vertical_speed=vertical_speed,
                                bank_angle=bank_angle,
                                pitch_angle=pitch,
                                gear_down=gear_down,
                                flaps_position=flaps_percent,
                                on_ground=on_ground,
                                stall_warning_active=stall_warning,
                                overspeed_warning_active=overspeed_warning,
                                g_force=g_force,
                                structural_ice_pct=structural_ice_pct,
                                pitot_ice_pct=pitot_ice_pct
                            )

                            # Speak error warnings
                            for error in errors:
                                if hasattr(self, 'voice') and self.voice:
                                    self.voice.speak(error.voice_message, priority=True)
                                    logger.warning(f"Pilot error: {error.message}")

                # Update pattern trainer if active
                if self.pattern_training_active and self.pattern_trainer:
                    if phase_name.lower() != 'unknown':
                        self.pattern_trainer.update(
                            latitude=latitude,
                            longitude=longitude,
                            altitude_msl=altitude,
                            altitude_agl=altitude_agl,
                            heading=heading,
                            airspeed=airspeed,
                            vertical_speed=vertical_speed,
                            on_ground=on_ground,
                            bank_angle=bank_angle,
                            gear_down=gear_down
                        )

                # Update flight recorder
                if UTILS_AVAILABLE and self.flight_recorder.recording:
                    self.flight_recorder.record_point(
                        latitude=latitude,
                        longitude=longitude,
                        altitude=altitude,
                        altitude_agl=altitude_agl,
                        heading=heading,
                        airspeed=airspeed,
                        ground_speed=ground_speed,
                        vertical_speed=vertical_speed,
                        bank=bank_angle,
                        pitch=pitch,
                        flight_phase=self.phase_detector.current_phase.name if COPILOT_AVAILABLE else "",
                        on_ground=on_ground
                    )

                # Mission progress
                if self.mission_active and latitude is not None and longitude is not None:
                    self._update_mission_progress(latitude, longitude, altitude_agl, airspeed, ground_speed)

                # Check constraints
                if self.mission_active and self.current_constraint:
                    self._check_constraints(bank_angle, altitude, vertical_speed, on_ground, airspeed)

                # Update aircraft info periodically
                if self.update_count % 30 == 0:
                    self._update_aircraft_info()

                # Update V2 Systems display
                if SYSTEMS_AVAILABLE and hasattr(self, 'systems_text'):
                    try:
                        # Get fuel data from snapshot (NO blocking calls!)
                        fuel_pct = "--"
                        fuel_qty_gal = snap.fuel_quantity_gal
                        fuel_cap_gal = snap.fuel_capacity_gal

                        # Calculate fuel percentage
                        if fuel_cap_gal > 0:
                            pct = (fuel_qty_gal / fuel_cap_gal) * 100
                            pct = min(100, max(0, pct))
                            fuel_pct = f"{pct:.0f}%"
                        elif fuel_qty_gal > 0:
                            fuel_pct = f"{fuel_qty_gal:.0f}gal"

                        # Get wear/maintenance
                        wear_pct = "0%"
                        if hasattr(self, 'maintenance') and self.aircraft_info.get('title'):
                            aircraft_id = self.aircraft_info.get('title', 'Unknown')[:20]
                            category = self.aircraft_info.get('category', 'light_piston')
                            # Use get_or_create to ensure aircraft is tracked
                            aircraft_status = self.maintenance.get_or_create_aircraft(
                                aircraft_id,
                                self.aircraft_info.get('title', 'Unknown'),
                                category
                            )
                            wear_pct = f"{aircraft_status.wear_percent:.0f}%"

                        # Get passengers - always show count from SimConnect
                        pax_count = getattr(self, '_estimated_passengers', 0)
                        pax = f"{pax_count} pax" if pax_count >= 0 else "0 pax"

                        # Add comfort score if passengers system is active with a mission
                        if hasattr(self, 'passengers') and self.passengers.current:
                            comfort = self.passengers.current
                            # Sync passenger count from SimConnect
                            if pax_count > 0:
                                comfort.passenger_count = pax_count
                            if comfort.passenger_count > 0 and comfort.current_score > 0:
                                pax = f"{comfort.passenger_count} pax ({comfort.current_score:.0f}%)"

                        self.systems_text.configure(
                            text=f"Fuel: {fuel_pct} | Wear: {wear_pct} | Passengers: {pax}"
                        )
                    except Exception as sys_e:
                        logger.debug(f"Systems display error: {sys_e}")

            except Exception as e:
                logger.error(f"Update error: {e}")

        if self.penalty_cooldown > 0:
            self.penalty_cooldown -= 1

        # GUI update interval - now FAST since no blocking SimConnect calls!
        # Background thread handles SimConnect polling, GUI just reads cached snapshot
        gui_interval = 100  # 100ms = 10 updates/second for smooth UI
        self.after(gui_interval, self._update_loop)

    def _update_mission_progress(self, latitude, longitude, altitude_agl, airspeed, ground_speed):
        """Update mission progress"""
        if not self.current_mission:
            return

        alt_agl = float(altitude_agl) if altitude_agl is not None else 0
        spd = float(airspeed) if airspeed is not None else 0

        is_flying = (alt_agl > 20 and spd > 10) or (alt_agl > 100)

        # Detect takeoff
        if not self.mission_started and is_flying:
            self.mission_started = True
            self.takeoff_time = datetime.now()
            logger.info("Mission started - Takeoff detected")

        # Calculate progress
        distance_to_arrival = calculate_distance_nm(
            latitude, longitude,
            self.arrival_lat, self.arrival_lon
        )

        if self.total_distance > 0:
            distance_covered = self.total_distance - distance_to_arrival
            progress = max(0, min(100, (distance_covered / self.total_distance) * 100))
        else:
            progress = 0

        self.mission_progress = progress
        self.progress_bar.set(progress / 100)

        # Status
        if not self.mission_started:
            status = "At parking - Ready for departure"
            self.progress_bar.configure(progress_color="#4A90D9")
        elif is_flying:
            status = f"In flight - {distance_to_arrival:.0f} nm remaining"
            self.progress_bar.configure(progress_color="#00AA00")
        elif progress < 95:
            status = f"On ground - {distance_to_arrival:.0f} nm remaining"
            self.progress_bar.configure(progress_color="#FFAA00")
        else:
            status = "Approaching destination"
            self.progress_bar.configure(progress_color="#00AA00")

        self.progress_label.configure(text=f"{progress:.0f}% - {status}")

        # Mission completion
        truly_on_ground = alt_agl < 10 and spd < 15
        if self.mission_started and truly_on_ground and distance_to_arrival < 5:
            ground_spd = ground_speed if ground_speed is not None else spd
            is_stopped = ground_spd < 2

            if is_stopped:
                self._complete_mission()

    def _check_constraints(self, bank_angle, altitude, vertical_speed, on_ground, airspeed):
        """Check constraint violations"""
        # Skip if relaxed mode or constraints disabled
        if self.config.get('relaxed_mode', False):
            return
        if not self.config.get('constraints', {}).get('enabled', True):
            return

        ctype = self.current_constraint['type']
        cvalue = self.current_constraint['value']
        violation = False

        if ctype == "bank" and bank_angle is not None:
            violation = abs(bank_angle) > cvalue
        elif ctype == "altitude_min" and altitude is not None:
            violation = altitude < cvalue and not on_ground
        elif ctype == "altitude_max" and altitude is not None:
            violation = altitude > cvalue
        elif ctype == "speed_max" and airspeed is not None:
            violation = airspeed > cvalue
            if violation:
                self.had_overspeed = True
        elif ctype == "vs_max" and vertical_speed is not None:
            violation = abs(vertical_speed) > cvalue

        if violation:
            self.constraint_violations += 1
            self.score_label.configure(text_color="#FF4444")
            if self.penalty_cooldown == 0:
                play_penalty_sound()
                self.penalty_cooldown = 3

                # Copilot error detection
                if COPILOT_AVAILABLE and self.config.get('copilot_enabled', True):
                    self.error_detector.record_violation(ctype, cvalue)
        else:
            color = "#00FF00" if self.score >= 0 else "#FF4444"
            self.score_label.configure(text_color=color)

        # Landing detection
        if on_ground and not self.was_on_ground:
            vs = vertical_speed if vertical_speed else 0
            self.max_vs_landing = abs(vs)
            logger.info(f"Landing detected: {vs:.0f} fpm")

        self.was_on_ground = on_ground if on_ground is not None else self.was_on_ground

    def _complete_mission(self):
        """Complete mission and calculate payment"""
        if not self.mission_active:
            return

        self.landing_time = datetime.now()
        logger.info("Mission completed - At parking")

        # Calculate payment
        category = self.aircraft_info.get('category', 'light_piston')
        hourly_rate = PILOT_HOURLY_RATES.get(category, 55)

        if self.takeoff_time:
            flight_duration = self.landing_time - self.takeoff_time
            self.flight_time_hours = flight_duration.total_seconds() / 3600
        else:
            self.flight_time_hours = self.total_distance / 150

        self.flight_time_hours = max(0.5, self.flight_time_hours)

        base_salary = hourly_rate * self.flight_time_hours

        if self.flight_time_hours > 5:
            per_diem = PER_DIEM_LONG
        elif self.flight_time_hours > 2:
            per_diem = PER_DIEM_MEDIUM
        else:
            per_diem = PER_DIEM_SHORT

        # Bonuses
        bonus_total = 0
        bonuses = []

        if self.is_night_flight:
            night_bonus = base_salary * BONUS_NIGHT_FLIGHT
            bonus_total += night_bonus
            bonuses.append(f"Night +{night_bonus:.0f}EUR")

        if self.is_weekend:
            weekend_bonus = base_salary * BONUS_WEEKEND
            bonus_total += weekend_bonus
            bonuses.append(f"Weekend +{weekend_bonus:.0f}EUR")

        landing_vs = abs(self.max_vs_landing)
        if landing_vs < 100:
            bonus_total += BONUS_SOFT_LANDING
            bonuses.append(f"Butter landing +{BONUS_SOFT_LANDING}EUR")
        elif landing_vs < 200:
            bonus_total += BONUS_GOOD_LANDING
            bonuses.append(f"Good landing +{BONUS_GOOD_LANDING}EUR")

        if self.constraint_violations == 0:
            bonus_total += BONUS_CONSTRAINTS_RESPECTED
            bonuses.append(f"Constraints OK +{BONUS_CONSTRAINTS_RESPECTED}EUR")

        # Penalties
        penalty_total = 0
        penalties = []

        if landing_vs > 500:
            penalty_total += abs(PENALTY_HARD_LANDING_SEVERE)
            penalties.append(f"Very hard landing {PENALTY_HARD_LANDING_SEVERE}EUR")
        elif landing_vs > 300:
            penalty_total += abs(PENALTY_HARD_LANDING_MEDIUM)
            penalties.append(f"Hard landing {PENALTY_HARD_LANDING_MEDIUM}EUR")

        if self.constraint_violations > 0:
            violation_penalty = self.constraint_violations * abs(PENALTY_CONSTRAINT_VIOLATION)
            penalty_total += violation_penalty
            penalties.append(f"Violations x{self.constraint_violations}: -{violation_penalty:.0f}EUR")

        if self.had_overspeed:
            penalty_total += abs(PENALTY_OVERSPEED)
            penalties.append(f"Overspeed {PENALTY_OVERSPEED}EUR")

        # Fuel cost (V2)
        fuel_cost = 0
        if SYSTEMS_AVAILABLE and self.config.get('fuel_management', True):
            fuel_cost = self.fuel_manager.calculate_cost(
                self.total_distance,
                self.flight_time_hours,
                category
            )
            penalties.append(f"Fuel -{fuel_cost:.0f}EUR")
            penalty_total += fuel_cost

        # Total
        total_pay = base_salary + per_diem + bonus_total - penalty_total

        self.score += total_pay
        self.missions_completed += 1
        self.total_hours += self.flight_time_hours

        # Update UI
        self.progress_bar.set(1.0)
        self.progress_bar.configure(progress_color="#00FF00")
        self.progress_label.configure(text="100% - MISSION COMPLETE!")

        bonus_str = ", ".join(bonuses) if bonuses else "None"
        penalty_str = ", ".join(penalties) if penalties else "None"

        result_text = (
            f"\n\n{'='*35}\n"
            f"PAYSLIP\n"
            f"{'='*35}\n"
            f"Flight time: {self.flight_time_hours:.1f}h\n"
            f"Hourly rate: {hourly_rate} EUR/h\n"
            f"{'─'*35}\n"
            f"Base salary: {base_salary:.2f} EUR\n"
            f"Per diem: +{per_diem:.2f} EUR\n"
            f"Bonuses: +{bonus_total:.2f} EUR\n"
            f"  ({bonus_str})\n"
            f"Penalties: -{penalty_total:.2f} EUR\n"
            f"  ({penalty_str})\n"
            f"{'─'*35}\n"
            f"TOTAL: {'+' if total_pay >= 0 else ''}{total_pay:.2f} EUR\n"
            f"{'='*35}"
        )

        current_text = self.mission_text.cget("text")
        self.mission_text.configure(text=current_text + result_text)

        # Stop V2 systems
        if COPILOT_AVAILABLE:
            self.debrief.stop_recording()
            debrief_result = self.debrief.generate_debrief(
                self.current_mission['departure']['icao'],
                self.current_mission['arrival']['icao'],
                self.aircraft_info['title']
            )

            if self.config.get('voice_enabled', True):
                self.voice.speak(debrief_result.voice_debrief)

        if UTILS_AVAILABLE:
            track = self.flight_recorder.stop_recording()
            if track:
                self.flight_recorder.save_current_track('kml')

        # Log to career
        if CAREER_AVAILABLE and self.config.get('career_mode', True):
            self.logbook.add_entry_from_mission({
                'departure': self.current_mission['departure'],
                'arrival': self.current_mission['arrival'],
                'aircraft': self.aircraft_info,
                'flight_time': self.flight_time_hours,
                'distance': self.total_distance,
                'landing_vs': self.max_vs_landing
            })

            # Update pilot profile
            if self.pilot:
                # Add flight time
                self.pilot.add_flight_time(self.flight_time_hours, category)

                # Add landing
                self.pilot.add_landing(self.max_vs_landing)

                # Add distance
                self.pilot.add_distance(self.total_distance)

                # Check for license upgrade
                if self.pilot.can_upgrade_license():
                    old_license = self.pilot.license.value
                    self.pilot.upgrade_license()
                    new_license = self.pilot.license.value
                    logger.info(f"License upgraded: {old_license} -> {new_license}")
                    self._show_upgrade_notification(old_license, new_license)

                # Update company reputation
                if hasattr(self, 'current_company') and self.current_company:
                    perf_score = 1.0
                    if self.constraint_violations > 0:
                        perf_score -= self.constraint_violations * 0.1
                    if landing_vs > 300:
                        perf_score -= 0.2
                    perf_score = max(0.0, min(1.0, perf_score))
                    self.current_company.complete_mission(total_pay, perf_score)

                # Check progression unlocks
                if self.progression:
                    pilot_data = self.pilot.to_dict()
                    company_data = self.companies.to_save_dict() if self.companies else {}
                    newly_unlocked = self.progression.check_unlocks(pilot_data, company_data)
                    for unlock in newly_unlocked:
                        logger.info(f"Unlock achieved: {unlock.name}")

                logger.info(f"Career updated: {self.pilot.total_hours:.1f}h total, {self.pilot.total_landings} landings")

        play_success_sound()
        self.mission_active = False
        self._save_game()

        # Update score display
        color = "#00FF00" if self.score >= 0 else "#FF4444"
        self.score_label.configure(text=f"BANK ACCOUNT: {self.score:.2f} EUR", text_color=color)
        self.stats_label.configure(
            text=f"Missions: {self.missions_completed} | Hours: {self.total_hours:.1f}h"
        )

    def _save_game(self):
        """Save game state with full career data"""
        # Build pilot data from profile or basic data
        if CAREER_AVAILABLE and hasattr(self, 'pilot') and self.pilot:
            pilot_data = self.pilot.to_dict()
            # Ensure bank_balance is synced with score
            pilot_data['bank_balance'] = self.score
            pilot_data['missions_completed'] = self.missions_completed
        else:
            pilot_data = {
                "name": "Pilot",
                "bank_balance": self.score,
                "total_hours": self.total_hours,
                "missions_completed": self.missions_completed
            }

        self.save_data = {
            "pilot": pilot_data
        }

        # Add company data if available
        if CAREER_AVAILABLE and hasattr(self, 'companies') and self.companies:
            self.save_data['company'] = self.companies.to_save_dict()

        # Add logbook if available
        if CAREER_AVAILABLE and hasattr(self, 'logbook') and self.logbook:
            self.save_data['logbook'] = self.logbook.to_save_dict()

        save_game(self.save_data)

    def _reset_score(self):
        """Reset score and career"""
        self.score = 100.00
        self.missions_completed = 0
        self.total_hours = 0

        # Reset pilot profile if career mode
        if CAREER_AVAILABLE and hasattr(self, 'pilot') and self.pilot:
            from career.pilot_profile import PilotProfile, set_pilot
            self.pilot = PilotProfile()  # Create fresh profile
            set_pilot(self.pilot)

        self.score_label.configure(text=f"BANK ACCOUNT: {self.score:.2f} EUR", text_color="#00FF00")
        self.stats_label.configure(text=f"Missions: {self.missions_completed} | Hours: {self.total_hours:.1f}h")
        self._save_game()

        # Refresh career panel
        if hasattr(self, '_refresh_career_panel'):
            self._refresh_career_panel()

    def _on_close(self):
        """Handle window close"""
        # Stop pattern training if active
        if self.pattern_training_active and self.pattern_trainer:
            self.pattern_trainer.stop_session()
            self.pattern_training_active = False

        self._save_game()
        self._save_config()

        if COPILOT_AVAILABLE:
            self.voice.stop()

        if self.sim:
            try:
                if hasattr(self.sim, 'disconnect'):
                    self.sim.disconnect()
                elif hasattr(self.sim, 'exit'):
                    self.sim.exit()
            except:
                pass

        self.destroy()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("   MSFS 2024 - Mission Generator V2")
    print("=" * 50)

    # Ensure directories exist
    SOUNDS_DIR.mkdir(exist_ok=True)
    FLIGHTPLANS_DIR.mkdir(exist_ok=True)

    app = MissionGeneratorV2()
    app.mainloop()
