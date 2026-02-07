"""
Mission Generator pour Microsoft Flight Simulator 2024
Utilise SimConnect et CustomTkinter pour une interface moderne Dark Mode
Score persistant en EUROS - Plans de vol elabores avec IA (Groq)
"""

import json
import random
import math
import threading
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from SimConnect import SimConnect, AircraftRequests

# ============================================================================
# CONFIGURATION LOGGING
# ============================================================================

logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

log_filename = logs_dir / f"mission_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MissionGenerator")
logger.info(f"=== MSFS 2024 Mission Generator - Demarrage ===")

# Import du module API Aviation (METAR, aeroports mondiaux, pistes)
try:
    from aviation_api import prepare_mission_data, get_weather_info, calculate_optimal_runway
    AVIATION_API_AVAILABLE = True
    logger.info("Module Aviation API charge")
except ImportError as e:
    AVIATION_API_AVAILABLE = False
    logger.warning(f"Module Aviation API non disponible: {e}")

# Import du systeme V2 Career
try:
    from v2.career import get_pilot, get_company_manager, get_logbook, get_progression
    from v2.career.pilot_profile import License, AIRCRAFT_CATEGORIES
    from v2.career.companies import ReputationLevel, REPUTATION_MULTIPLIERS
    CAREER_SYSTEM_AVAILABLE = True
    logger.info("Module Career V2 charge")
except ImportError as e:
    CAREER_SYSTEM_AVAILABLE = False
    logger.warning(f"Module Career V2 non disponible: {e}")

# ============================================================================
# CONFIGURATION
# ============================================================================

AIRPORTS_FILE = "airports.json"
SAVE_FILE = "savegame.json"
CONFIG_FILE = "config.json"
FLIGHTPLANS_DIR = Path("flightplans")
UPDATE_INTERVAL = 1000

FLIGHTPLANS_DIR.mkdir(exist_ok=True)

# ============================================================================
# SYSTEME DE REMUNERATION PILOTE (tarifs realistes)
# ============================================================================

# Tarif horaire selon le type d'avion (€/heure de vol)
PILOT_HOURLY_RATES = {
    "light_piston": 55,        # Cessna, Piper - pilote prive/instructeur
    "twin_piston": 75,         # Baron, DA62 - pilote charter
    "single_turboprop": 95,    # TBM, PC-12 - pilote cargo regional
    "turboprop": 120,          # King Air, ATR - pilote regional
    "light_jet": 150,          # Citation, Phenom - pilote business jet
    "jet": 200,                # A320, 737 - copilote airline
    "heavy_jet": 280,          # 747, A380 - commandant de bord
    "helicopter": 85,          # Helicoptere - pilote SAMU/travail aerien
}

# Indemnites (per diem)
PER_DIEM_SHORT = 35       # Escale < 2h
PER_DIEM_MEDIUM = 65      # Vol 2-5h
PER_DIEM_LONG = 120       # Vol > 5h ou international

# Bonus
BONUS_NIGHT_FLIGHT = 0.25       # +25% vol de nuit
BONUS_WEEKEND = 0.15            # +15% week-end
BONUS_BAD_WEATHER = 0.20        # +20% mauvaise meteo (visibilite < 5km)
BONUS_SOFT_LANDING = 50         # Atterrissage < 100 fpm
BONUS_GOOD_LANDING = 25         # Atterrissage 100-200 fpm
BONUS_CONSTRAINTS_RESPECTED = 30  # Toutes contraintes respectees

# Penalites
PENALTY_HARD_LANDING_MEDIUM = -50    # Atterrissage 300-500 fpm
PENALTY_HARD_LANDING_SEVERE = -150   # Atterrissage > 500 fpm
PENALTY_CRASH = -500                 # Crash / degats
PENALTY_CONSTRAINT_VIOLATION = -10   # Par violation de contrainte (cumul)
PENALTY_OVERSPEED = -25              # Survitesse detectee

# Anciennes constantes (compatibilite)
PENALTY_PER_SECOND = 0.05  # Penalite par seconde de violation
SOFT_LANDING_BONUS = 50.0  # Bonus atterrissage doux
CRASH_PENALTY = 200.0      # Penalite crash

# ============================================================================
# PALETTE COULEURS CAREER PANEL
# ============================================================================

COLORS = {
    'accent': '#4A90D9',      # Bleu - titres
    'positive': '#00FF00',    # Vert - succes
    'positive_alt': '#00AA00',
    'negative': '#FF4444',    # Rouge - erreur
    'warning': '#FFAA00',     # Orange - attention
    'text': '#AAAAAA',        # Gris - texte normal
    'text_dim': '#888888',    # Gris fonce
    'bg_dark': '#1a1a2e',     # Fond custom
    'bg_panel': '#2d2d44',    # Fond panneau
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
# CONFIGURATION PERSISTANTE
# ============================================================================

def load_config() -> dict:
    """Charge la configuration"""
    default_config = {
        "pln_destination_folder": str(FLIGHTPLANS_DIR.absolute()),
        "groq_api_key": "",
        "auto_copy_pln": False
    }
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Merge avec defaults
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
            return config
    except:
        return default_config

def save_config(config: dict):
    """Sauvegarde la configuration"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration sauvegardee")
    except Exception as e:
        logger.error(f"Erreur sauvegarde config: {e}")

# ============================================================================
# GESTION AUDIO (PYGAME)
# ============================================================================

pygame_available = False
try:
    import pygame
    pygame.mixer.init()
    pygame_available = True
    logger.info("Pygame mixer initialise")
except Exception as e:
    logger.warning(f"Pygame non disponible: {e}")

def play_sound(sound_file: str):
    if not pygame_available:
        return
    sound_path = Path("sounds") / sound_file
    if sound_path.exists():
        try:
            pygame.mixer.music.load(str(sound_path))
            pygame.mixer.music.play()
        except Exception as e:
            logger.error(f"Erreur audio: {e}")

def play_penalty_sound():
    play_sound("penalty.wav")

def play_success_sound():
    play_sound("success.wav")

def play_crash_sound():
    play_sound("crash.wav")

def play_mission_sound():
    play_sound("mission.wav")

# ============================================================================
# SAUVEGARDE PERSISTANTE
# ============================================================================

def load_save() -> dict:
    try:
        with open(SAVE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Sauvegarde chargee: {data.get('score', 100):.2f} EUR")
            return data
    except:
        logger.info("Nouvelle sauvegarde creee")
        return {"score": 100.00, "missions_completed": 0, "best_landing": 0}

def save_game(data: dict):
    try:
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Erreur sauvegarde: {e}")

# ============================================================================
# UTILITAIRES
# ============================================================================

def calculate_distance_nm(lat1, lon1, lat2, lon2) -> float:
    R = 3440.065
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def load_airports(filepath: str) -> list:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            airports = data.get('airports', [])
            logger.info(f"{len(airports)} aeroports charges")
            return airports
    except:
        logger.error(f"Erreur chargement aeroports")
        return []

# ============================================================================
# GENERATION DE PLAN DE VOL MSFS (.PLN) - VERSION ELABOREE
# ============================================================================

def generate_waypoints_between(dep: dict, arr: dict, num_waypoints: int = 3) -> list:
    """Genere des waypoints intermediaires entre deux aeroports"""
    waypoints = []

    for i in range(1, num_waypoints + 1):
        ratio = i / (num_waypoints + 1)

        # Interpolation + leger offset aleatoire pour rendre le trajet plus realiste
        lat = dep['lat'] + (arr['lat'] - dep['lat']) * ratio
        lon = dep['lon'] + (arr['lon'] - dep['lon']) * ratio

        # Ajout d'un offset aleatoire (simule des waypoints de navigation)
        lat += random.uniform(-0.5, 0.5)
        lon += random.uniform(-0.5, 0.5)

        waypoint_id = f"WPT{i:02d}"
        waypoints.append({
            "id": waypoint_id,
            "lat": lat,
            "lon": lon
        })

    return waypoints

def format_coordinate(value: float, is_lat: bool) -> str:
    """Formate une coordonnee pour le fichier PLN"""
    if is_lat:
        direction = "N" if value >= 0 else "S"
    else:
        direction = "E" if value >= 0 else "W"
    return f"{direction}{abs(value):.6f}"

def parse_runway_ident(runway_ident: str) -> tuple:
    """
    Parse un identifiant de piste (ex: "27R", "09L", "04C", "18")
    Retourne (numero, designator) ex: (27, "RIGHT") ou (9, "LEFT")
    """
    if not runway_ident:
        return (1, "NONE")

    import re
    match = re.match(r'(\d+)([LRC])?', str(runway_ident).upper())
    if match:
        number = int(match.group(1))
        suffix = match.group(2)

        designator_map = {
            'L': 'LEFT',
            'R': 'RIGHT',
            'C': 'CENTER',
            None: 'NONE'
        }
        designator = designator_map.get(suffix, 'NONE')

        return (number, designator)

    return (1, "NONE")


def generate_flightplan_pln_with_waypoints(departure: dict, arrival: dict, custom_waypoints: list = None, aircraft_info: dict = None) -> str:
    """Genere un fichier plan de vol au format MSFS (.pln) avec waypoints personnalises et pistes optimales"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mission_{departure['icao']}_{arrival['icao']}_{timestamp}.pln"
    filepath = FLIGHTPLANS_DIR / filename

    # Extraire les pistes si disponibles
    dep_runway = departure.get('runway')
    arr_runway = arrival.get('runway')

    dep_rwy_num, dep_rwy_des = parse_runway_ident(dep_runway.get('ident') if dep_runway else None)
    arr_rwy_num, arr_rwy_des = parse_runway_ident(arr_runway.get('ident') if arr_runway else None)

    logger.debug(f"Pistes: Depart {dep_runway.get('ident') if dep_runway else 'auto'} -> Arrivee {arr_runway.get('ident') if arr_runway else 'auto'}")

    # Calcul distance
    distance = calculate_distance_nm(departure['lat'], departure['lon'], arrival['lat'], arrival['lon'])

    # Determiner le profil avion et l'altitude max
    category = aircraft_info.get("category", "light_piston") if aircraft_info else "light_piston"
    profile = AIRCRAFT_PROFILES.get(category, AIRCRAFT_PROFILES["light_piston"])
    max_alt = profile["max_alt"]

    # Utiliser les waypoints custom ou generer des standards
    if custom_waypoints and len(custom_waypoints) > 0:
        waypoints = custom_waypoints
        # Determiner l'altitude de croisiere depuis les waypoints (altitude max utilisee)
        cruise_alt = max(wpt.get('alt', 5000) for wpt in waypoints)
        logger.info(f"Utilisation de {len(waypoints)} waypoints - Cruise FL{cruise_alt//100:03d}")
    else:
        # Fallback: generer des waypoints basiques
        cruise_alt = calculate_optimal_altitude(distance, max_alt)
        num_wpts = min(5, max(1, int(distance / 100)))
        waypoints = generate_waypoints_between(departure, arrival, num_wpts)
        # Ajouter altitude aux waypoints generes
        for i, wpt in enumerate(waypoints):
            position = (i + 1) / (num_wpts + 1)
            if position < 0.3:
                wpt['alt'] = int(cruise_alt * 0.6)
            elif position > 0.7:
                wpt['alt'] = int(cruise_alt * 0.5)
            else:
                wpt['alt'] = cruise_alt
        logger.info(f"Utilisation de {len(waypoints)} waypoints auto-generes - Cruise FL{cruise_alt//100:03d}")

    # Construction du XML
    dep_coord = f"{format_coordinate(departure['lat'], True)},{format_coordinate(departure['lon'], False)},+000000.00"
    arr_coord = f"{format_coordinate(arrival['lat'], True)},{format_coordinate(arrival['lon'], False)},+000000.00"

    # Type de vol selon altitude
    flight_type = "IFR" if cruise_alt >= 10000 else "VFR"

    # Generer les waypoints XML avec le bon type (VOR, Intersection, ou User)
    waypoints_xml = ""
    for i, wpt in enumerate(waypoints):
        wpt_id = wpt.get('id', f"WPT{i+1:02d}")[:5].upper()
        wpt_lat = wpt.get('lat', 0)
        wpt_lon = wpt.get('lon', 0)
        wpt_alt = wpt.get('alt', 5000)
        wpt_type = wpt.get('type', 'User')  # VOR, INT, ou User

        wpt_coord = f"{format_coordinate(wpt_lat, True)},{format_coordinate(wpt_lon, False)},+{wpt_alt:06.2f}"

        # Determiner le type de waypoint MSFS
        if wpt_type == 'VOR':
            atc_type = "VOR"
            waypoints_xml += f'''
        <ATCWaypoint id="{wpt_id}">
            <ATCWaypointType>{atc_type}</ATCWaypointType>
            <WorldPosition>{wpt_coord}</WorldPosition>
            <SpeedMaxFP>-1</SpeedMaxFP>
            <ICAO>
                <ICAOIdent>{wpt_id}</ICAOIdent>
            </ICAO>
        </ATCWaypoint>'''
        elif wpt_type == 'INT':
            atc_type = "Intersection"
            waypoints_xml += f'''
        <ATCWaypoint id="{wpt_id}">
            <ATCWaypointType>{atc_type}</ATCWaypointType>
            <WorldPosition>{wpt_coord}</WorldPosition>
            <SpeedMaxFP>-1</SpeedMaxFP>
            <ICAO>
                <ICAOIdent>{wpt_id}</ICAOIdent>
            </ICAO>
        </ATCWaypoint>'''
        else:
            waypoints_xml += f'''
        <ATCWaypoint id="{wpt_id}">
            <ATCWaypointType>User</ATCWaypointType>
            <WorldPosition>{wpt_coord}</WorldPosition>
            <SpeedMaxFP>-1</SpeedMaxFP>
        </ATCWaypoint>'''

    # Route type selon le type de waypoints
    has_real_navaids = any(wpt.get('type') in ['VOR', 'INT'] for wpt in waypoints)
    route_type = "LowAlt" if has_real_navaids and flight_type == "IFR" else "Direct"

    # Construire les infos de piste pour le depart
    dep_runway_xml = f'''<RunwayNumberFP>{dep_rwy_num}</RunwayNumberFP>
            <RunwayDesignatorFP>{dep_rwy_des}</RunwayDesignatorFP>'''

    # Construire les infos de piste pour l'arrivee
    arr_runway_xml = f'''<RunwayNumberFP>{arr_rwy_num}</RunwayNumberFP>
            <RunwayDesignatorFP>{arr_rwy_des}</RunwayDesignatorFP>'''

    pln_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<SimBase.Document Type="AceXML" version="1,0">
    <Descr>AceXML Document</Descr>
    <FlightPlan.FlightPlan>
        <Title>{departure['icao']} to {arrival['icao']}</Title>
        <FPType>{flight_type}</FPType>
        <RouteType>{route_type}</RouteType>
        <CruisingAlt>{cruise_alt}.000</CruisingAlt>
        <DepartureID>{departure['icao']}</DepartureID>
        <DepartureLLA>{dep_coord}</DepartureLLA>
        <DestinationID>{arrival['icao']}</DestinationID>
        <DestinationLLA>{arr_coord}</DestinationLLA>
        <Descr>{departure['name']} to {arrival['name']}</Descr>
        <DepartureName>{departure['name']}</DepartureName>
        <DestinationName>{arrival['name']}</DestinationName>
        <AppVersion>
            <AppVersionMajor>11</AppVersionMajor>
            <AppVersionBuild>282174</AppVersionBuild>
        </AppVersion>
        <ATCWaypoint id="{departure['icao']}">
            <ATCWaypointType>Airport</ATCWaypointType>
            <WorldPosition>{dep_coord}</WorldPosition>
            {dep_runway_xml}
            <ICAO>
                <ICAOIdent>{departure['icao']}</ICAOIdent>
            </ICAO>
        </ATCWaypoint>{waypoints_xml}
        <ATCWaypoint id="{arrival['icao']}">
            <ATCWaypointType>Airport</ATCWaypointType>
            <WorldPosition>{arr_coord}</WorldPosition>
            {arr_runway_xml}
            <ICAO>
                <ICAOIdent>{arrival['icao']}</ICAOIdent>
            </ICAO>
        </ATCWaypoint>
    </FlightPlan.FlightPlan>
</SimBase.Document>'''

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(pln_content)
        logger.info(f"Plan de vol genere: {filepath} ({len(waypoints)} waypoints, {route_type})")
        return str(filepath)
    except Exception as e:
        logger.error(f"Erreur generation PLN: {e}")
        return None


# ============================================================================
# BASE DE DONNEES NAVAIDS
# ============================================================================

NAVAIDS_FILE = "navaids.json"

def load_navaids() -> dict:
    """Charge la base de donnees des navaids (VOR, NDB, intersections)"""
    try:
        with open(NAVAIDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Navaids charges: {len(data.get('vors', []))} VORs, {len(data.get('intersections', []))} intersections")
            return data
    except Exception as e:
        logger.warning(f"Navaids non disponibles: {e}")
        return {"vors": [], "intersections": [], "airways": []}

def find_navaids_near_route(departure: dict, arrival: dict, navaids: dict, max_distance_nm: float = 50) -> list:
    """Trouve les navaids proches de la route directe entre depart et arrivee"""
    nearby = []

    # Coordonnees de la route
    dep_lat, dep_lon = departure['lat'], departure['lon']
    arr_lat, arr_lon = arrival['lat'], arrival['lon']

    # Vecteur de la route
    route_vec = (arr_lat - dep_lat, arr_lon - dep_lon)
    route_length = math.sqrt(route_vec[0]**2 + route_vec[1]**2)

    if route_length == 0:
        return []

    # Parcourir tous les navaids
    all_navaids = []
    for vor in navaids.get('vors', []):
        all_navaids.append({**vor, 'type': 'VOR'})
    for fix in navaids.get('intersections', []):
        all_navaids.append({**fix, 'type': 'INT'})

    for nav in all_navaids:
        nav_lat, nav_lon = nav['lat'], nav['lon']

        # Projection du navaid sur la route
        t = ((nav_lat - dep_lat) * route_vec[0] + (nav_lon - dep_lon) * route_vec[1]) / (route_length ** 2)

        # Ignorer si avant le depart ou apres l'arrivee
        if t < 0.1 or t > 0.9:
            continue

        # Point projete sur la route
        proj_lat = dep_lat + t * route_vec[0]
        proj_lon = dep_lon + t * route_vec[1]

        # Distance du navaid a la route
        dist_to_route = calculate_distance_nm(nav_lat, nav_lon, proj_lat, proj_lon)

        if dist_to_route <= max_distance_nm:
            # Distance depuis le depart (pour tri)
            dist_from_dep = calculate_distance_nm(dep_lat, dep_lon, nav_lat, nav_lon)
            nearby.append({
                'id': nav['id'],
                'name': nav.get('name', nav['id']),
                'lat': nav_lat,
                'lon': nav_lon,
                'type': nav['type'],
                'dist_from_dep': dist_from_dep,
                'position_ratio': t
            })

    # Trier par position sur la route
    nearby.sort(key=lambda x: x['position_ratio'])

    return nearby

# ============================================================================
# INTEGRATION GROQ (OPTIONNEL)
# ============================================================================

# Profils avion (utilise par Groq et fallback)
AIRCRAFT_PROFILES = {
    "light_piston": {
        "type_vol": "VFR",
        "alt_range": "2000-8000 ft",
        "vitesse": "90-140 kts",
        "description": "Avion leger monomoteur (Cessna, Piper)",
        "max_alt": 12000
    },
    "twin_piston": {
        "type_vol": "VFR/IFR",
        "alt_range": "5000-15000 ft",
        "vitesse": "140-200 kts",
        "description": "Bimoteur piston (Baron, DA62)",
        "max_alt": 20000
    },
    "single_turboprop": {
        "type_vol": "IFR",
        "alt_range": "FL100-FL280",
        "vitesse": "200-280 kts",
        "description": "Turboprop monomoteur (TBM, PC-12)",
        "max_alt": 28000
    },
    "turboprop": {
        "type_vol": "IFR",
        "alt_range": "FL150-FL300",
        "vitesse": "250-350 kts",
        "description": "Turboprop bimoteur (King Air, ATR)",
        "max_alt": 31000
    },
    "light_jet": {
        "type_vol": "IFR",
        "alt_range": "FL300-FL410",
        "vitesse": "350-450 kts",
        "description": "Jet leger (Citation, Phenom)",
        "max_alt": 45000
    },
    "jet": {
        "type_vol": "IFR",
        "alt_range": "FL320-FL410",
        "vitesse": "450-520 kts",
        "description": "Jet commercial (A320, 737)",
        "max_alt": 41000
    },
    "heavy_jet": {
        "type_vol": "IFR",
        "alt_range": "FL350-FL430",
        "vitesse": "480-560 kts",
        "description": "Gros porteur (747, A380, 777)",
        "max_alt": 43000
    },
    "helicopter": {
        "type_vol": "VFR",
        "alt_range": "500-5000 ft",
        "vitesse": "80-150 kts",
        "description": "Helicoptere",
        "max_alt": 10000
    }
}

def calculate_optimal_altitude(distance: float, max_alt: int) -> int:
    """Calcule l'altitude optimale selon la distance et le plafond de l'avion"""
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

def generate_route_with_navaids(departure: dict, arrival: dict, aircraft_info: dict = None) -> list:
    """Genere une route realiste en utilisant les vrais navaids"""

    # Charger les navaids
    navaids = load_navaids()

    # Profil avion
    category = aircraft_info.get("category", "light_piston") if aircraft_info else "light_piston"
    profile = AIRCRAFT_PROFILES.get(category, AIRCRAFT_PROFILES["light_piston"])

    # Distance et altitude
    distance = calculate_distance_nm(departure['lat'], departure['lon'], arrival['lat'], arrival['lon'])
    cruise_alt = calculate_optimal_altitude(distance, profile["max_alt"])

    # Trouver les navaids proches de la route
    nearby_navaids = find_navaids_near_route(departure, arrival, navaids, max_distance_nm=60)

    if not nearby_navaids:
        logger.info("Aucun navaid trouve, utilisation de waypoints generes")
        return []

    # Selectionner les meilleurs navaids (3-5 selon la distance)
    if distance < 150:
        num_waypoints = min(2, len(nearby_navaids))
    elif distance < 300:
        num_waypoints = min(3, len(nearby_navaids))
    elif distance < 500:
        num_waypoints = min(4, len(nearby_navaids))
    else:
        num_waypoints = min(5, len(nearby_navaids))

    # Selectionner des waypoints bien espaces
    selected = []
    if num_waypoints > 0 and nearby_navaids:
        step = len(nearby_navaids) / num_waypoints
        for i in range(num_waypoints):
            idx = int(i * step)
            if idx < len(nearby_navaids):
                selected.append(nearby_navaids[idx])

    # Construire les waypoints avec altitudes progressives
    waypoints = []
    total_wpts = len(selected)

    for i, nav in enumerate(selected):
        # Calcul altitude progressive
        position = (i + 1) / (total_wpts + 1)

        if position < 0.3:
            # Phase de montee
            alt = int(cruise_alt * (0.4 + position * 2))
        elif position > 0.7:
            # Phase de descente
            descent_progress = (position - 0.7) / 0.3
            alt = int(cruise_alt * (1.0 - descent_progress * 0.6))
        else:
            # Croisiere
            alt = cruise_alt

        # Arrondir a 1000ft pres
        alt = round(alt / 1000) * 1000
        alt = max(3000, min(alt, profile["max_alt"]))

        waypoints.append({
            "id": nav['id'],
            "lat": nav['lat'],
            "lon": nav['lon'],
            "alt": alt,
            "type": nav['type'],
            "description": f"{nav['type']} {nav.get('name', nav['id'])}"
        })

    logger.info(f"Route generee avec {len(waypoints)} navaids reels (FL{cruise_alt//100:03d})")
    return waypoints

def generate_route_with_groq(departure: dict, arrival: dict, api_key: str, aircraft_info: dict = None) -> list:
    """Utilise Groq pour generer une route realiste adaptee au type d'avion"""
    if not api_key:
        return generate_route_with_navaids(departure, arrival, aircraft_info)

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        # Charger les navaids disponibles
        navaids = load_navaids()
        nearby_navaids = find_navaids_near_route(departure, arrival, navaids, max_distance_nm=80)

        # Calcul de la distance
        distance = calculate_distance_nm(departure['lat'], departure['lon'], arrival['lat'], arrival['lon'])

        # Parametres par defaut si pas d'info avion
        if aircraft_info is None:
            aircraft_info = {
                "title": "Avion generique",
                "category": "light_piston",
                "cruise_speed": 120,
                "cruise_alt": 5000
            }

        category = aircraft_info.get("category", "light_piston")
        cruise_speed = aircraft_info.get("cruise_speed", 120)

        profile = AIRCRAFT_PROFILES.get(category, AIRCRAFT_PROFILES["light_piston"])

        # Calcul altitude optimale pour ce vol
        cruise_alt = calculate_optimal_altitude(distance, profile["max_alt"])

        # Construire la liste des navaids disponibles pour le prompt
        navaids_list = ""
        if nearby_navaids:
            navaids_list = "\n\nNAVAIDS DISPONIBLES SUR LA ROUTE (utilise ces vrais waypoints):\n"
            for nav in nearby_navaids[:15]:  # Max 15 pour le prompt
                navaids_list += f"- {nav['id']} ({nav['type']}): lat {nav['lat']:.4f}, lon {nav['lon']:.4f} - {nav.get('name', '')}\n"

        prompt = f"""Tu es un dispatcher aerien professionnel. Genere une route de vol IFR realiste.

AVION:
- Type: {aircraft_info.get('title', 'Inconnu')}
- Categorie: {profile['description']}
- Altitude max: {profile['max_alt']} ft
- Type de vol: {profile['type_vol']}

VOL:
- Depart: {departure['icao']} ({departure['lat']:.4f}, {departure['lon']:.4f})
- Arrivee: {arrival['icao']} ({arrival['lat']:.4f}, {arrival['lon']:.4f})
- Distance: {distance:.0f} nm
- Altitude croisiere: {cruise_alt} ft (FL{cruise_alt//100:03d})
{navaids_list}

INSTRUCTIONS:
1. UTILISE UNIQUEMENT les navaids de la liste ci-dessus (VOR et intersections reels)
2. Selectionne 3-5 waypoints bien espaces le long de la route
3. Altitudes progressives: montee -> croisiere ({cruise_alt}ft) -> descente
4. Ne jamais depasser {profile['max_alt']} ft

RETOURNE UNIQUEMENT ce JSON (sans texte avant/apres):
[
  {{"id": "XXX", "lat": 00.0000, "lon": 0.0000, "alt": 00000}}
]"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es un expert ATC. Reponds UNIQUEMENT en JSON valide, sans markdown, sans explication."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.2
        )

        # Parse la reponse JSON
        content = response.choices[0].message.content.strip()

        # Nettoyer la reponse (enlever markdown si present)
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        # Extraire le JSON de la reponse
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            waypoints = json.loads(json_match.group())

            # Valider et corriger les waypoints
            validated = []
            for wpt in waypoints:
                if 'id' in wpt and 'lat' in wpt and 'lon' in wpt:
                    # S'assurer que l'altitude est dans les limites
                    alt = wpt.get('alt', cruise_alt)
                    alt = max(3000, min(alt, profile["max_alt"]))
                    validated.append({
                        "id": str(wpt['id'])[:5].upper(),
                        "lat": float(wpt['lat']),
                        "lon": float(wpt['lon']),
                        "alt": int(alt)
                    })

            if validated:
                logger.info(f"Groq: {len(validated)} waypoints generes (FL{cruise_alt//100:03d})")
                return validated

    except Exception as e:
        logger.warning(f"Groq erreur: {e}, fallback sur navaids locaux")

    # Fallback: utiliser la generation locale avec navaids
    return generate_route_with_navaids(departure, arrival, aircraft_info)

# ============================================================================
# CONTRAINTES
# ============================================================================

CONSTRAINTS = [
    {"name": "Inclinaison max", "value": 35, "unit": "°", "type": "bank", "difficulty": "facile"},
    {"name": "Inclinaison max", "value": 30, "unit": "°", "type": "bank", "difficulty": "normal"},
    {"name": "Inclinaison max", "value": 25, "unit": "°", "type": "bank", "difficulty": "difficile"},
    {"name": "Altitude min", "value": 1000, "unit": "ft", "type": "altitude_min", "difficulty": "facile"},
    {"name": "Altitude min", "value": 1500, "unit": "ft", "type": "altitude_min", "difficulty": "normal"},
    {"name": "Altitude max", "value": 10000, "unit": "ft", "type": "altitude_max", "difficulty": "facile"},
    {"name": "Vitesse max", "value": 280, "unit": "kts", "type": "speed_max", "difficulty": "facile"},
    {"name": "Vitesse max", "value": 250, "unit": "kts", "type": "speed_max", "difficulty": "normal"},
    {"name": "VS max", "value": 1000, "unit": "fpm", "type": "vs_max", "difficulty": "facile"},
    {"name": "VS max", "value": 700, "unit": "fpm", "type": "vs_max", "difficulty": "normal"},
]

def get_random_constraint() -> dict:
    weights = [3 if c['difficulty'] == 'facile' else 2 if c['difficulty'] == 'normal' else 1 for c in CONSTRAINTS]
    return random.choices(CONSTRAINTS, weights=weights, k=1)[0]

# ============================================================================
# APPLICATION PRINCIPALE
# ============================================================================

class MissionGeneratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MSFS 2024 - Mission Generator")

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

        # Sauvegarde
        self.save_data = load_save()
        self.score = self.save_data.get('score', 100.00)
        self.missions_completed = self.save_data.get('missions_completed', 0)

        # Variables
        self.airports = load_airports(AIRPORTS_FILE)
        self.current_mission = None
        self.current_constraint = None
        self.current_flightplan = None
        self.mission_active = False
        self.was_on_ground = True
        self.penalty_cooldown = 0
        self.update_count = 0

        # Variables progression mission
        self.departure_lat = None
        self.departure_lon = None
        self.arrival_lat = None
        self.arrival_lon = None
        self.total_distance = 0
        self.mission_started = False  # True quand l'avion a decolle
        self.mission_progress = 0.0  # 0-100%

        # Variables remuneration pilote
        self.takeoff_time = None       # Heure de decollage
        self.landing_time = None       # Heure d'atterrissage
        self.flight_time_hours = 0     # Temps de vol en heures
        self.constraint_violations = 0 # Nombre de violations de contrainte
        self.max_vs_landing = 0        # VS max a l'atterrissage (fpm)
        self.had_overspeed = False     # Survitesse detectee
        self.is_night_flight = False   # Vol de nuit
        self.is_weekend = False        # Vol week-end
        self.is_bad_weather = False    # Mauvaise meteo

        # SimConnect
        self.sim_connected = False
        self.sim = None
        self.aircraft_requests = None

        # Info avion
        self.aircraft_info = {
            "title": "Inconnu",
            "type": "UNKNOWN",
            "model": "UNKNOWN",
            "engine_type": 0,  # 0=Piston, 1=Jet, 5=Turboprop
            "num_engines": 1,
            "cruise_speed": 120,  # kts par defaut
            "cruise_alt": 5000,  # ft par defaut
            "category": "light"  # light, turboprop, jet, heavy
        }

        # Career System V2
        self._init_career_system()

        self._build_ui()
        self._connect_simconnect_async()
        self.after(UPDATE_INTERVAL, self._update_loop)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _init_career_system(self):
        """Initialise le systeme de carriere V2"""
        if CAREER_SYSTEM_AVAILABLE:
            self.pilot = get_pilot()
            self.companies = get_company_manager()
            self.logbook = get_logbook()
            self.progression = get_progression()
            self.current_company = self.companies.select_random_company()
            logger.info(f"Career system initialized - Pilot: {self.pilot.name}, License: {self.pilot.license.value}")
        else:
            self.pilot = None
            self.companies = None
            self.logbook = None
            self.progression = None
            self.current_company = None
            logger.warning("Career system not available")

    def _build_ui(self):
        # Main container with 2 columns (35% / 65%)
        self.main_container = ctk.CTkFrame(self, corner_radius=0)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.main_container.grid_columnconfigure(0, weight=35)
        self.main_container.grid_columnconfigure(1, weight=65)
        self.main_container.grid_rowconfigure(0, weight=1)

        # === LEFT PANEL: CAREER ===
        self._build_career_panel()

        # === RIGHT PANEL: MISSION ===
        self._build_mission_panel()

    def _build_career_panel(self):
        """Construit le panneau Carriere (gauche, 35%)"""
        self.career_panel = ctk.CTkFrame(self.main_container, corner_radius=10, fg_color=COLORS['bg_dark'])
        self.career_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)

        # Titre Carriere
        career_title = ctk.CTkLabel(
            self.career_panel, text="CARRIERE PILOTE",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=COLORS['accent']
        )
        career_title.pack(pady=(15, 10))

        # Scrollable content
        self.career_scroll = ctk.CTkScrollableFrame(
            self.career_panel, fg_color="transparent"
        )
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
        """Arbre de progression des licences STUDENT -> PPL -> CPL -> ATPL"""
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
        if self.pilot:
            current_license = self.pilot.license.value.upper()  # Ensure uppercase
            progress_data = self.pilot.get_next_license_progress()

        licenses = ['STUDENT', 'PPL', 'CPL', 'ATPL']
        license_hours = {
            'STUDENT': 0,
            'PPL': 40,
            'CPL': 200,
            'ATPL': 1500
        }

        self.license_nodes = {}
        self.license_progress_bars = {}

        for i, lic in enumerate(licenses):
            # Determine state
            lic_idx = licenses.index(lic)
            current_idx = licenses.index(current_license)

            if lic_idx < current_idx:
                # Past license - completed
                node_color = LICENSE_COLORS[lic]
                text_color = node_color
                is_active = False
            elif lic_idx == current_idx:
                # Current license
                node_color = LICENSE_COLORS[lic]
                text_color = "#FFFFFF"
                is_active = True
            else:
                # Future license - locked
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

            # Progress bar between licenses (except after last)
            if i < len(licenses) - 1:
                next_lic = licenses[i + 1]
                next_hours = license_hours[next_lic]

                # Calculate progress to next license
                progress_pct = 0
                if self.pilot:
                    if lic_idx < current_idx:
                        progress_pct = 1.0
                    elif lic_idx == current_idx and progress_data:
                        progress_pct = progress_data.get('hours_progress', 0) / 100

                bar_frame = ctk.CTkFrame(license_frame, fg_color="transparent")
                bar_frame.pack(pady=2)

                # Connector line
                connector = ctk.CTkLabel(bar_frame, text="|", text_color="#444444")
                connector.pack()

                # Progress bar
                progress_bar = ctk.CTkProgressBar(
                    bar_frame, width=80, height=10,
                    corner_radius=5,
                    fg_color="#333333",
                    progress_color=LICENSE_COLORS.get(next_lic, "#4A90D9")
                )
                progress_bar.set(progress_pct)
                progress_bar.pack(pady=2)
                self.license_progress_bars[lic] = progress_bar

                # Hours label
                if self.pilot and lic_idx == current_idx:
                    hours_text = f"{self.pilot.total_hours:.0f}h / {next_hours}h"
                elif lic_idx < current_idx:
                    hours_text = f"{next_hours}h"
                else:
                    hours_text = f"0h / {next_hours}h"

                hours_label = ctk.CTkLabel(
                    bar_frame, text=hours_text,
                    font=ctk.CTkFont(size=9), text_color="#888888"
                )
                hours_label.pack()

                connector2 = ctk.CTkLabel(bar_frame, text="|", text_color="#444444")
                connector2.pack()

        # Padding at bottom
        ctk.CTkLabel(license_frame, text="", height=5).pack()

    def _build_company_widget(self):
        """Widget Compagnie avec reputation"""
        company_frame = ctk.CTkFrame(self.career_scroll, corner_radius=10, fg_color=COLORS['bg_panel'])
        company_frame.pack(fill="x", pady=(0, 10))

        title = ctk.CTkLabel(
            company_frame, text="COMPAGNIE ACTUELLE",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS['accent']
        )
        title.pack(pady=(10, 5))

        if self.current_company:
            company_name = self.current_company.name
            reputation = self.current_company.reputation
            rep_level = self.current_company.reputation_level.value.upper()
            multiplier = self.current_company.pay_multiplier
        else:
            company_name = "Freelance"
            reputation = 50
            rep_level = "NEUTRAL"
            multiplier = 1.0

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
        """Grid 4x2 des categories d'avions"""
        categories_frame = ctk.CTkFrame(self.career_scroll, corner_radius=10, fg_color=COLORS['bg_panel'])
        categories_frame.pack(fill="x", pady=(0, 10))

        title = ctk.CTkLabel(
            categories_frame, text="CATEGORIES AVIONS",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS['accent']
        )
        title.pack(pady=(10, 5))

        # Get available categories
        if self.pilot:
            available = self.pilot.get_available_categories()
        else:
            available = ['light_piston']

        current_category = self.aircraft_info.get('category', 'light_piston')

        # Categories in order
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

            # Determine colors
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

            # Badge
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
        """Widget statistiques du pilote"""
        stats_frame = ctk.CTkFrame(self.career_scroll, corner_radius=10, fg_color=COLORS['bg_panel'])
        stats_frame.pack(fill="x", pady=(0, 10))

        title = ctk.CTkLabel(
            stats_frame, text="STATISTIQUES",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS['accent']
        )
        title.pack(pady=(10, 5))

        # Get stats
        if self.pilot:
            total_hours = self.pilot.total_hours
            total_landings = self.pilot.total_landings
            perfect_landings = self.pilot.perfect_landings
            total_distance = self.pilot.total_distance_nm
            hours_by_cat = self.pilot.hours_by_category
        else:
            total_hours = 0
            total_landings = 0
            perfect_landings = 0
            total_distance = 0
            hours_by_cat = {}

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

            # Category name
            ctk.CTkLabel(
                row_frame, text=display_name, width=80,
                font=ctk.CTkFont(size=9), text_color=COLORS['text_dim'], anchor="w"
            ).pack(side="left")

            # Mini bar
            bar = ctk.CTkProgressBar(
                row_frame, height=8, width=100,
                corner_radius=4,
                fg_color="#333333",
                progress_color=COLORS['accent']
            )
            bar.set(cat_hours / max_hours if max_hours > 0 else 0)
            bar.pack(side="left", padx=5)
            self.category_hour_bars[cat] = bar

            # Hours value
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
        ctk.CTkLabel(
            land_frame, text="Atterrissages",
            font=ctk.CTkFont(size=9), text_color=COLORS['text_dim']
        ).pack()

        # Perfect landings
        perfect_frame = ctk.CTkFrame(other_stats, fg_color="transparent")
        perfect_frame.pack(side="left", expand=True)
        self.perfect_label = ctk.CTkLabel(
            perfect_frame, text=f"{perfect_landings}",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=COLORS['positive']
        )
        self.perfect_label.pack()
        ctk.CTkLabel(
            perfect_frame, text="Parfaits",
            font=ctk.CTkFont(size=9), text_color=COLORS['text_dim']
        ).pack()

        # Distance
        dist_frame = ctk.CTkFrame(other_stats, fg_color="transparent")
        dist_frame.pack(side="left", expand=True)
        self.distance_label = ctk.CTkLabel(
            dist_frame, text=f"{total_distance:.0f}",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=COLORS['accent']
        )
        self.distance_label.pack()
        ctk.CTkLabel(
            dist_frame, text="nm parcourus",
            font=ctk.CTkFont(size=9), text_color=COLORS['text_dim']
        ).pack()

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

    def _build_mission_panel(self):
        """Construit le panneau Mission (droite, 65%)"""
        self.mission_panel = ctk.CTkFrame(self.main_container, corner_radius=10)
        self.mission_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)

        # Scrollable content for mission panel
        self.main_frame = ctk.CTkScrollableFrame(self.mission_panel, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # === HEADER SCORE ===
        self.header_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.header_frame.pack(fill="x", pady=(0, 10))

        self.score_label = ctk.CTkLabel(
            self.header_frame,
            text=f"COMPTE EN BANQUE: {self.score:.2f} EUR",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#00FF00" if self.score >= 0 else "#FF4444"
        )
        self.score_label.pack(pady=(10, 5))

        self.stats_label = ctk.CTkLabel(
            self.header_frame,
            text=f"Missions: {self.missions_completed} | Tarif horaire selon avion",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        self.stats_label.pack(pady=(0, 10))

        # === STATUS ===
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="Connexion au simulateur...",
            font=ctk.CTkFont(size=13),
            text_color="#FFA500"
        )
        self.status_label.pack(pady=(0, 10))

        # === BOUTON MISSION ===
        self.generate_btn = ctk.CTkButton(
            self.main_frame,
            text="GENERER MISSION",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            fg_color="#1E5631",
            hover_color="#2E7D32",
            command=self._generate_mission
        )
        self.generate_btn.pack(pady=8, padx=40, fill="x")

        # === MISSION ===
        self.mission_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.mission_frame.pack(pady=8, padx=15, fill="x")

        self.mission_title = ctk.CTkLabel(
            self.mission_frame, text="MISSION",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#4A90D9"
        )
        self.mission_title.pack(pady=(8, 3))

        self.mission_text = ctk.CTkLabel(
            self.mission_frame,
            text="Appuyez sur 'GENERER MISSION' pour commencer",
            font=ctk.CTkFont(size=13), wraplength=550
        )
        self.mission_text.pack(pady=(0, 8), padx=10)

        # === PROGRESSION ===
        self.progress_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color="#1a1a2e")
        self.progress_frame.pack(pady=8, padx=15, fill="x")

        self.progress_title = ctk.CTkLabel(
            self.progress_frame, text="PROGRESSION MISSION",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#4A90D9"
        )
        self.progress_title.pack(pady=(8, 3))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            width=400,
            height=20,
            corner_radius=10,
            fg_color="#2d2d44",
            progress_color="#00AA00"
        )
        self.progress_bar.pack(pady=(5, 5), padx=20)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="0% - En attente de mission",
            font=ctk.CTkFont(size=12),
            text_color="#AAAAAA"
        )
        self.progress_label.pack(pady=(0, 8))

        # === CONTRAINTE ===
        self.constraint_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color="#4A1010")
        self.constraint_frame.pack(pady=8, padx=15, fill="x")

        self.constraint_title = ctk.CTkLabel(
            self.constraint_frame, text="CONTRAINTE",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#FF4444"
        )
        self.constraint_title.pack(pady=(8, 3))

        self.constraint_text = ctk.CTkLabel(
            self.constraint_frame, text="Aucune contrainte active",
            font=ctk.CTkFont(size=13), text_color="#FF6666"
        )
        self.constraint_text.pack(pady=(0, 8))

        # === DONNEES AVION ===
        self.data_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.data_frame.pack(pady=8, padx=15, fill="x")

        self.data_title = ctk.CTkLabel(
            self.data_frame, text="DONNEES AVION",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888"
        )
        self.data_title.pack(pady=(8, 3))

        self.aircraft_label = ctk.CTkLabel(
            self.data_frame, text="Avion: En attente de connexion...",
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

        # === DOSSIER PLN ===
        self.pln_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.pln_frame.pack(pady=8, padx=15, fill="x")

        self.pln_title = ctk.CTkLabel(
            self.pln_frame, text="DOSSIER PLANS DE VOL (.PLN)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888"
        )
        self.pln_title.pack(pady=(8, 5))

        self.pln_path_frame = ctk.CTkFrame(self.pln_frame, fg_color="transparent")
        self.pln_path_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.pln_path_entry = ctk.CTkEntry(
            self.pln_path_frame,
            placeholder_text="Chemin du dossier PLN...",
            font=ctk.CTkFont(size=11),
            height=30
        )
        self.pln_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.pln_path_entry.insert(0, self.config.get('pln_destination_folder', ''))

        self.pln_browse_btn = ctk.CTkButton(
            self.pln_path_frame, text="Parcourir",
            font=ctk.CTkFont(size=11), width=80, height=30,
            command=self._browse_pln_folder
        )
        self.pln_browse_btn.pack(side="left", padx=(0, 5))

        self.pln_open_btn = ctk.CTkButton(
            self.pln_path_frame, text="Ouvrir",
            font=ctk.CTkFont(size=11), width=60, height=30,
            fg_color="#2B4B6F",
            command=self._open_pln_folder
        )
        self.pln_open_btn.pack(side="left")

        # Auto-copy checkbox
        self.auto_copy_var = ctk.BooleanVar(value=self.config.get('auto_copy_pln', False))
        self.auto_copy_check = ctk.CTkCheckBox(
            self.pln_frame,
            text="Copier automatiquement les PLN dans ce dossier",
            variable=self.auto_copy_var,
            font=ctk.CTkFont(size=11),
            command=self._on_auto_copy_changed
        )
        self.auto_copy_check.pack(pady=(0, 8))

        # === GROQ API ===
        self.groq_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.groq_frame.pack(pady=8, padx=15, fill="x")

        self.groq_title = ctk.CTkLabel(
            self.groq_frame, text="GROQ API (routes IA - optionnel)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888"
        )
        self.groq_title.pack(pady=(8, 5))

        self.groq_entry = ctk.CTkEntry(
            self.groq_frame,
            placeholder_text="Cle API Groq (optionnel)...",
            font=ctk.CTkFont(size=11),
            height=30, show="*"
        )
        self.groq_entry.pack(fill="x", padx=10, pady=(0, 8))
        if self.config.get('groq_api_key'):
            self.groq_entry.insert(0, self.config['groq_api_key'])

        # === BOUTONS BAS ===
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
            self.bottom_frame, text="Sauvegarder Config",
            font=ctk.CTkFont(size=11), height=28,
            fg_color="#4B6F2B", hover_color="#5B7F3B",
            command=self._save_config
        )
        self.save_config_btn.pack(side="right", padx=5)

    def _refresh_career_panel(self):
        """Met a jour le panneau carriere avec les donnees actuelles"""
        if not CAREER_SYSTEM_AVAILABLE or not self.pilot:
            return

        try:
            # Update total hours
            self.total_hours_label.configure(text=f"{self.pilot.total_hours:.1f}h")

            # Update landings
            self.landings_label.configure(text=f"{self.pilot.total_landings}")
            self.perfect_label.configure(text=f"{self.pilot.perfect_landings}")
            self.distance_label.configure(text=f"{self.pilot.total_distance_nm:.0f}")

            # Update bank balance (both panels)
            bank_color = COLORS['positive'] if self.score >= 0 else COLORS['negative']
            self.bank_label.configure(text=f"{self.score:.2f} EUR", text_color=bank_color)
            self.score_label.configure(text=f"COMPTE EN BANQUE: {self.score:.2f} EUR", text_color=bank_color)

            # Update license progress
            progress_data = self.pilot.get_next_license_progress()
            current_license = self.pilot.license.value.upper()  # Ensure uppercase

            # Update license nodes
            licenses = ['STUDENT', 'PPL', 'CPL', 'ATPL']
            for lic in licenses:
                lic_idx = licenses.index(lic)
                current_idx = licenses.index(current_license)

                if lic_idx < current_idx:
                    node_color = LICENSE_COLORS[lic]
                    self.license_nodes[lic].configure(fg_color="transparent", border_color=node_color)
                elif lic_idx == current_idx:
                    node_color = LICENSE_COLORS[lic]
                    self.license_nodes[lic].configure(fg_color=node_color, border_color=node_color)
                else:
                    self.license_nodes[lic].configure(fg_color="transparent", border_color="#444444")

            # Update progress bars between licenses
            license_hours = {'STUDENT': 0, 'PPL': 40, 'CPL': 200, 'ATPL': 1500}
            for i, lic in enumerate(licenses[:-1]):
                lic_idx = licenses.index(lic)
                current_idx = licenses.index(current_license)
                next_lic = licenses[i + 1]

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

    def _browse_pln_folder(self):
        folder = filedialog.askdirectory(title="Selectionnez le dossier de destination des PLN")
        if folder:
            self.pln_path_entry.delete(0, 'end')
            self.pln_path_entry.insert(0, folder)
            self.config['pln_destination_folder'] = folder
            save_config(self.config)
            logger.info(f"Dossier PLN: {folder}")

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

    def _save_config(self):
        self.config['pln_destination_folder'] = self.pln_path_entry.get()
        self.config['groq_api_key'] = self.groq_entry.get()
        self.config['auto_copy_pln'] = self.auto_copy_var.get()
        save_config(self.config)
        self.save_config_btn.configure(text="Sauvegarde!", fg_color="#2E7D32")
        self.after(2000, lambda: self.save_config_btn.configure(text="Sauvegarder Config", fg_color="#4B6F2B"))

    def _connect_simconnect_async(self):
        def connect():
            logger.info("Connexion SimConnect...")
            try:
                self.sim = SimConnect()
                self.aircraft_requests = AircraftRequests(self.sim, _time=0)
                self.sim_connected = True

                # Recuperer les infos de l'avion
                self._update_aircraft_info()

                aircraft_display = f"{self.aircraft_info['title'][:25]} ({self.aircraft_info['category']})"
                self.after(0, lambda: self.status_label.configure(
                    text="Connecte a MSFS 2024!", text_color="#00FF00"
                ))
                self.after(0, lambda ad=aircraft_display: self.aircraft_label.configure(
                    text=f"Avion: {ad}"
                ))
                logger.info(f"SimConnect OK! Avion: {self.aircraft_info['title']}")
            except Exception as e:
                self.sim_connected = False
                logger.error(f"SimConnect: {e}")
                self.after(0, lambda: self.status_label.configure(
                    text="Simulateur non detecte", text_color="#FF6666"
                ))
        threading.Thread(target=connect, daemon=True).start()

    def _update_aircraft_info(self):
        """Recupere les informations de l'avion actuel"""
        if not self.sim_connected or not self.aircraft_requests:
            return

        try:
            # Recuperer les infos de base
            title = self._safe_get("TITLE")
            atc_type = self._safe_get("ATC_TYPE")
            atc_model = self._safe_get("ATC_MODEL")
            engine_type = self._safe_get("ENGINE_TYPE")
            num_engines = self._safe_get("NUMBER_OF_ENGINES")
            design_cruise_alt = self._safe_get("DESIGN_CRUISE_ALT")
            design_speed = self._safe_get("DESIGN_SPEED_VC")

            # Mettre a jour les infos
            if title:
                self.aircraft_info["title"] = str(title)
            if atc_type:
                self.aircraft_info["type"] = str(atc_type)
            if atc_model:
                self.aircraft_info["model"] = str(atc_model)
            if engine_type is not None:
                self.aircraft_info["engine_type"] = int(engine_type)
            if num_engines is not None:
                self.aircraft_info["num_engines"] = int(num_engines)
            if design_cruise_alt is not None and design_cruise_alt > 0:
                self.aircraft_info["cruise_alt"] = int(design_cruise_alt)
            if design_speed is not None and design_speed > 0:
                self.aircraft_info["cruise_speed"] = int(design_speed)

            # Determiner la categorie
            self.aircraft_info["category"] = self._determine_aircraft_category()

            logger.info(f"Avion detecte: {self.aircraft_info['title']} | "
                       f"Type: {self.aircraft_info['category']} | "
                       f"Moteur: {self.aircraft_info['engine_type']} | "
                       f"Cruise: {self.aircraft_info['cruise_speed']}kts @ {self.aircraft_info['cruise_alt']}ft")

        except Exception as e:
            logger.warning(f"Erreur lecture info avion: {e}")

    def _determine_aircraft_category(self) -> str:
        """Determine la categorie de l'avion selon ses caracteristiques"""
        engine = self.aircraft_info.get("engine_type", 0)
        num_eng = self.aircraft_info.get("num_engines", 1)
        cruise_alt = self.aircraft_info.get("cruise_alt", 5000)
        title = self.aircraft_info.get("title", "").lower()

        # Detection par type de moteur
        if engine == 1:  # Jet
            if num_eng >= 4 or "747" in title or "a380" in title or "777" in title:
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
        else:
            # Detection par mots-cles dans le titre
            if any(x in title for x in ["cessna", "piper", "c172", "c152", "pa28"]):
                return "light_piston"
            elif any(x in title for x in ["baron", "bonanza", "sr22", "da62"]):
                return "twin_piston"
            elif any(x in title for x in ["tbm", "pc-12", "pilatus", "caravan"]):
                return "turboprop"
            elif any(x in title for x in ["citation", "learjet", "phenom", "cj"]):
                return "light_jet"
            elif any(x in title for x in ["737", "a320", "a319", "a321", "320"]):
                return "jet"
            elif any(x in title for x in ["747", "777", "787", "a350", "a380"]):
                return "heavy_jet"

        return "light_piston"  # Par defaut

    def _generate_mission(self):
        """Genere une mission avec meteo temps reel et pistes optimales"""

        # Mettre a jour les infos avion avant de generer la route
        self._update_aircraft_info()

        # Afficher message de chargement
        self.mission_text.configure(text="Chargement donnees aviation...\n(aeroports, meteo, pistes)")
        self.update()

        # Utiliser l'API Aviation si disponible (aeroports mondiaux + meteo + pistes)
        if AVIATION_API_AVAILABLE:
            # Determiner la distance selon le type d'avion
            category = self.aircraft_info.get('category', 'light_piston')
            if category in ['light_piston', 'helicopter']:
                min_dist, max_dist = 50, 300
            elif category in ['twin_piston', 'single_turboprop']:
                min_dist, max_dist = 100, 600
            elif category in ['turboprop', 'light_jet']:
                min_dist, max_dist = 150, 1000
            else:  # jet, heavy_jet
                min_dist, max_dist = 300, 2500

            # Recuperer mission complete avec meteo et pistes
            mission_data = prepare_mission_data(
                min_distance=min_dist,
                max_distance=max_dist
            )

            if mission_data:
                dep_data = mission_data['departure']
                arr_data = mission_data['arrival']

                # Construire les dictionnaires pour compatibilite
                departure = {
                    'icao': dep_data['icao'],
                    'name': dep_data['name'],
                    'lat': dep_data['lat'],
                    'lon': dep_data['lon'],
                    'runway': dep_data.get('runway'),
                    'weather': dep_data.get('weather')
                }
                arrival = {
                    'icao': arr_data['icao'],
                    'name': arr_data['name'],
                    'lat': arr_data['lat'],
                    'lon': arr_data['lon'],
                    'runway': arr_data.get('runway'),
                    'weather': arr_data.get('weather')
                }
                distance = mission_data['distance_nm']
            else:
                # Fallback sur aeroports locaux
                logger.warning("API Aviation echec, utilisation aeroports locaux")
                if len(self.airports) < 2:
                    self.mission_text.configure(text="Erreur: pas assez d'aeroports disponibles")
                    return
                dep_local, arr_local = random.sample(self.airports, 2)
                departure = {**dep_local, 'runway': None, 'weather': None}
                arrival = {**arr_local, 'runway': None, 'weather': None}
                distance = calculate_distance_nm(departure['lat'], departure['lon'], arrival['lat'], arrival['lon'])
        else:
            # Mode sans API - aeroports locaux uniquement
            if len(self.airports) < 2:
                self.mission_text.configure(text="Erreur: pas assez d'aeroports disponibles")
                return
            dep_local, arr_local = random.sample(self.airports, 2)
            departure = {**dep_local, 'runway': None, 'weather': None}
            arrival = {**arr_local, 'runway': None, 'weather': None}
            distance = calculate_distance_nm(departure['lat'], departure['lon'], arrival['lat'], arrival['lon'])

        self.current_mission = {'departure': departure, 'arrival': arrival, 'distance': distance}
        self.current_constraint = get_random_constraint()

        # Essayer Groq pour une route IA, sinon route standard
        groq_key = self.groq_entry.get() or self.config.get('groq_api_key', '')
        groq_waypoints = None
        if groq_key:
            logger.info(f"Generation route IA pour {self.aircraft_info['category']}...")
            groq_waypoints = generate_route_with_groq(departure, arrival, groq_key, self.aircraft_info)

        # Generation PLN (avec waypoints et pistes)
        self.current_flightplan = generate_flightplan_pln_with_waypoints(
            departure, arrival,
            custom_waypoints=groq_waypoints,
            aircraft_info=self.aircraft_info
        )

        # Copie automatique si active
        if self.auto_copy_var.get() and self.current_flightplan:
            dest_folder = self.pln_path_entry.get()
            if dest_folder and os.path.exists(dest_folder):
                try:
                    dest_path = Path(dest_folder) / Path(self.current_flightplan).name
                    shutil.copy2(self.current_flightplan, dest_path)
                    logger.info(f"PLN copie vers: {dest_path}")
                except Exception as e:
                    logger.error(f"Erreur copie PLN: {e}")

        # Interface - Afficher les infos completes
        pln_name = Path(self.current_flightplan).name if self.current_flightplan else "Erreur"

        # Info piste depart
        dep_rwy = departure.get('runway')
        dep_rwy_str = f"RWY {dep_rwy['ident']}" if dep_rwy else "RWY auto"

        # Info piste arrivee
        arr_rwy = arrival.get('runway')
        arr_rwy_str = f"RWY {arr_rwy['ident']}" if arr_rwy else "RWY auto"

        # Info meteo
        dep_weather = departure.get('weather', {})
        arr_weather = arrival.get('weather', {})
        dep_wind = dep_weather.get('wind_description', '?') if dep_weather else '?'
        arr_wind = arr_weather.get('wind_description', '?') if arr_weather else '?'

        mission_str = (
            f"Depart: {departure['name'][:30]} ({departure['icao']})\n"
            f"   {dep_rwy_str} | Vent: {dep_wind}\n"
            f"Arrivee: {arrival['name'][:30]} ({arrival['icao']})\n"
            f"   {arr_rwy_str} | Vent: {arr_wind}\n"
            f"Distance: {distance:.0f} nm"
        )
        self.mission_text.configure(text=mission_str)

        diff_colors = {"facile": "#00AA00", "normal": "#FFAA00", "difficile": "#FF4444"}
        diff = self.current_constraint.get('difficulty', 'normal')
        self.constraint_text.configure(
            text=f"{self.current_constraint['name']}: {self.current_constraint['value']} {self.current_constraint['unit']} ({diff.upper()})",
            text_color=diff_colors.get(diff, "#FF6666")
        )

        self.mission_active = True
        self.was_on_ground = True
        self.penalty_cooldown = 0

        # Initialiser la progression
        self.departure_lat = departure['lat']
        self.departure_lon = departure['lon']
        self.arrival_lat = arrival['lat']
        self.arrival_lon = arrival['lon']
        self.total_distance = distance
        self.mission_started = False
        self.mission_progress = 0.0

        # Reset barre de progression
        self.progress_bar.set(0)
        self.progress_bar.configure(progress_color="#4A90D9")
        self.progress_label.configure(text="0% - Au parking - Pret au depart")

        # Reset variables remuneration
        self.takeoff_time = None
        self.landing_time = None
        self.flight_time_hours = 0
        self.constraint_violations = 0
        self.max_vs_landing = 0
        self.had_overspeed = False

        # Determiner vol de nuit (entre 21h et 6h)
        current_hour = datetime.now().hour
        self.is_night_flight = current_hour >= 21 or current_hour < 6

        # Determiner week-end (samedi=5, dimanche=6)
        self.is_weekend = datetime.now().weekday() >= 5

        # Determiner mauvaise meteo (visibilite < 5km dans le METAR)
        self.is_bad_weather = False
        dep_weather = departure.get('weather', {})
        if dep_weather:
            visibility = dep_weather.get('visibility_sm', 10)
            if visibility and visibility < 3:  # Moins de 3 SM = mauvaise visibilite
                self.is_bad_weather = True

        # Afficher tarif horaire
        category = self.aircraft_info.get('category', 'light_piston')
        hourly_rate = PILOT_HOURLY_RATES.get(category, 55)
        self.stats_label.configure(
            text=f"Missions: {self.missions_completed} | Tarif: {hourly_rate}EUR/h ({category})"
        )

        play_mission_sound()
        logger.info(f"Mission: {departure['icao']} ({dep_rwy_str}) -> {arrival['icao']} ({arr_rwy_str}) - {distance:.0f} nm")

    def _update_loop(self):
        self.update_count += 1

        # Refresh career panel every 5 seconds
        if self.update_count % 5 == 0:
            self._refresh_career_panel()

        if self.sim_connected and self.aircraft_requests:
            try:
                # Mise a jour info avion toutes les 30 secondes
                if self.update_count % 30 == 0:
                    old_title = self.aircraft_info.get('title', '')
                    self._update_aircraft_info()
                    if self.aircraft_info.get('title', '') != old_title:
                        aircraft_display = f"{self.aircraft_info['title'][:25]} ({self.aircraft_info['category']})"
                        self.aircraft_label.configure(text=f"Avion: {aircraft_display}")

                altitude = self._safe_get("PLANE_ALTITUDE")
                altitude_agl = self._safe_get("PLANE_ALT_ABOVE_GROUND")  # Altitude par rapport au sol (AGL)
                bank_angle = self._safe_get("PLANE_BANK_DEGREES")
                vertical_speed = self._safe_get("VERTICAL_SPEED")
                on_ground = self._safe_get("SIM_ON_GROUND")
                airspeed = self._safe_get("AIRSPEED_INDICATED")
                latitude = self._safe_get("PLANE_LATITUDE")
                longitude = self._safe_get("PLANE_LONGITUDE")
                ground_velocity = self._safe_get("GROUND_VELOCITY")  # Vitesse au sol (kts)
                eng1_combustion = self._safe_get("GENERAL_ENG_COMBUSTION:1")  # Moteur 1 en marche
                turb_n1 = self._safe_get("TURB_ENG_N1:1")  # N1 turboprop/jet (fallback)
                eng1_rpm = self._safe_get("GENERAL_ENG_RPM:1")  # RPM moteur (fallback)
                parking_brake = self._safe_get("BRAKE_PARKING_POSITION")  # Frein de parking

                # Conversion bank (radians -> degres)
                if bank_angle is not None and abs(bank_angle) < 10:
                    bank_angle = math.degrees(bank_angle)

                # Affichage
                parts = []
                if altitude is not None:
                    parts.append(f"Alt: {altitude:.0f} ft")
                if bank_angle is not None:
                    parts.append(f"Bank: {bank_angle:.1f}°")
                if vertical_speed is not None:
                    parts.append(f"VS: {vertical_speed:.0f} fpm")
                if airspeed is not None:
                    parts.append(f"Speed: {airspeed:.0f} kts")

                if parts:
                    self.data_text.configure(text=" | ".join(parts))
                else:
                    self.data_text.configure(text="Donnees non disponibles...")

                # Afficher altitude AGL dans le debug
                agl_str = f"AGL: {altitude_agl:.0f}ft" if altitude_agl is not None else "AGL: ?"
                if latitude is not None and longitude is not None:
                    self.debug_text.configure(text=f"[{agl_str}] Lat: {latitude:.4f} Lon: {longitude:.4f}")
                else:
                    self.debug_text.configure(text=f"[{agl_str}]")

                # === PROGRESSION MISSION ===
                if self.mission_active and latitude is not None and longitude is not None:
                    self._update_mission_progress(latitude, longitude, altitude_agl, airspeed, ground_velocity, eng1_combustion, turb_n1, eng1_rpm)

                # Logique de jeu
                if self.mission_active and self.current_constraint:
                    self._check_constraints(bank_angle, altitude, vertical_speed, on_ground, airspeed)

            except Exception as e:
                logger.error(f"Update: {e}")

        if self.penalty_cooldown > 0:
            self.penalty_cooldown -= 1

        self.after(UPDATE_INTERVAL, self._update_loop)

    def _safe_get(self, var_name: str):
        try:
            return self.aircraft_requests.get(var_name)
        except:
            return None

    def _update_mission_progress(self, latitude, longitude, altitude_agl, airspeed, ground_velocity, eng_combustion, turb_n1=None, eng_rpm=None):
        """Met a jour la progression de la mission basee sur la distance parcourue"""

        if not self.current_mission:
            return

        # Utiliser l'altitude AGL (Above Ground Level) - plus fiable que SIM_ON_GROUND
        # Seuils bas pour compatibilite helicopteres
        alt_agl = float(altitude_agl) if altitude_agl is not None else 0
        spd = float(airspeed) if airspeed is not None else 0

        # En vol si: altitude AGL > 20ft ET vitesse > 10kts
        # OU altitude AGL > 100ft (meme en stationnaire, on est en l'air)
        is_flying = (alt_agl > 20 and spd > 10) or (alt_agl > 100)
        is_on_ground = not is_flying

        # Debug toutes les 5 secondes
        if self.update_count % 5 == 0:
            logger.debug(f"Progress: AGL={alt_agl:.1f}ft, Speed={spd:.1f}kts, is_flying={is_flying}, mission_started={self.mission_started}")

        # Recuperer les coordonnees de depart et arrivee
        if self.departure_lat is None:
            dep = self.current_mission.get('departure', {})
            arr = self.current_mission.get('arrival', {})
            self.departure_lat = dep.get('lat')
            self.departure_lon = dep.get('lon')
            self.arrival_lat = arr.get('lat')
            self.arrival_lon = arr.get('lon')
            self.total_distance = self.current_mission.get('distance', 0)

        if self.departure_lat is None or self.arrival_lat is None:
            return

        # Detecter le decollage (premiere fois qu'on quitte le sol)
        if not self.mission_started and is_flying:
            self.mission_started = True
            self.takeoff_time = datetime.now()  # Enregistrer heure de decollage
            logger.info("Mission demarree - Decollage detecte")

        # Calculer la distance restante jusqu'a l'arrivee
        distance_to_arrival = calculate_distance_nm(
            latitude, longitude,
            self.arrival_lat, self.arrival_lon
        )

        # Calculer la progression (0-100%)
        if self.total_distance > 0:
            distance_covered = self.total_distance - distance_to_arrival
            # Limiter entre 0 et 100%
            progress = max(0, min(100, (distance_covered / self.total_distance) * 100))
        else:
            progress = 0

        self.mission_progress = progress

        # Mettre a jour la barre de progression
        self.progress_bar.set(progress / 100)

        # Determiner le statut
        if not self.mission_started:
            status = "Au parking - Pret au depart"
            self.progress_bar.configure(progress_color="#4A90D9")  # Bleu
        elif is_flying:
            status = f"En vol - {distance_to_arrival:.0f} nm restants"
            self.progress_bar.configure(progress_color="#00AA00")  # Vert
        elif progress < 95:
            status = f"Au sol - {distance_to_arrival:.0f} nm restants"
            self.progress_bar.configure(progress_color="#FFAA00")  # Orange
        else:
            status = "Approche destination"
            self.progress_bar.configure(progress_color="#00AA00")  # Vert

        self.progress_label.configure(text=f"{progress:.0f}% - {status}")

        # === DETECTION FIN DE MISSION ===
        # Conditions: proche de l'arrivee + au sol + arrete + moteur coupe
        # Au sol = altitude AGL < 10ft ET vitesse < 15kts (compatible helico)
        truly_on_ground = alt_agl < 10 and spd < 15

        if self.mission_started and truly_on_ground:
            # Verifier si l'avion est arrete (vitesse sol < 2kts)
            ground_spd = ground_velocity if ground_velocity is not None else spd
            is_stopped = ground_spd < 2

            # Verifier si le moteur est coupe - multiple methodes
            # Methode 1: GENERAL_ENG_COMBUSTION (standard)
            engine_off_combustion = eng_combustion is not None and not eng_combustion
            # Methode 2: TURB_ENG_N1 < 5% (turboprop/jet - N1 quasi nul = moteur coupe)
            engine_off_n1 = turb_n1 is not None and turb_n1 < 5.0
            # Methode 3: RPM < 50 (piston/general)
            engine_off_rpm = eng_rpm is not None and eng_rpm < 50
            # Moteur considere coupe si au moins une methode confirme
            engine_off = engine_off_combustion or engine_off_n1 or engine_off_rpm

            # Debug toutes les 5 secondes quand au sol et arrete
            if is_stopped and self.update_count % 5 == 0:
                logger.debug(f"Fin mission check: dist_arrival={distance_to_arrival:.1f}nm, engine_off={engine_off} "
                           f"(combustion={eng_combustion}, N1={turb_n1}, RPM={eng_rpm})")

            if is_stopped and engine_off and distance_to_arrival < 10:
                self._complete_mission_at_parking()

    def _complete_mission_at_parking(self):
        """Complete la mission quand l'avion est au parking moteur coupe - Calcul remuneration realiste"""
        if not self.mission_active:
            return

        self.landing_time = datetime.now()
        logger.info("Mission terminee - Arrivee au parking, moteur coupe")

        # === CALCUL REMUNERATION PILOTE ===
        category = self.aircraft_info.get('category', 'light_piston')
        hourly_rate = PILOT_HOURLY_RATES.get(category, 55)

        # Calculer le temps de vol (en heures)
        if self.takeoff_time:
            flight_duration = self.landing_time - self.takeoff_time
            self.flight_time_hours = flight_duration.total_seconds() / 3600
        else:
            # Estimer selon la distance (vitesse moyenne 150kts)
            self.flight_time_hours = self.total_distance / 150

        # Minimum 0.5h de vol compte (temps bloc)
        self.flight_time_hours = max(0.5, self.flight_time_hours)

        # --- SALAIRE DE BASE ---
        base_salary = hourly_rate * self.flight_time_hours

        # --- PER DIEM (indemnites) ---
        if self.flight_time_hours > 5:
            per_diem = PER_DIEM_LONG
        elif self.flight_time_hours > 2:
            per_diem = PER_DIEM_MEDIUM
        else:
            per_diem = PER_DIEM_SHORT

        # --- BONUS ---
        bonuses = []
        bonus_total = 0

        # Bonus vol de nuit (+25%)
        if self.is_night_flight:
            night_bonus = base_salary * BONUS_NIGHT_FLIGHT
            bonus_total += night_bonus
            bonuses.append(f"Nuit +{night_bonus:.0f}EUR")

        # Bonus week-end (+15%)
        if self.is_weekend:
            weekend_bonus = base_salary * BONUS_WEEKEND
            bonus_total += weekend_bonus
            bonuses.append(f"Week-end +{weekend_bonus:.0f}EUR")

        # Bonus mauvaise meteo (+20%)
        if self.is_bad_weather:
            weather_bonus = base_salary * BONUS_BAD_WEATHER
            bonus_total += weather_bonus
            bonuses.append(f"IMC +{weather_bonus:.0f}EUR")

        # Bonus atterrissage doux
        landing_vs = abs(self.max_vs_landing)
        if landing_vs < 100:
            bonus_total += BONUS_SOFT_LANDING
            bonuses.append(f"Atterro parfait +{BONUS_SOFT_LANDING}EUR")
        elif landing_vs < 200:
            bonus_total += BONUS_GOOD_LANDING
            bonuses.append(f"Bon atterro +{BONUS_GOOD_LANDING}EUR")

        # Bonus contraintes respectees
        if self.constraint_violations == 0:
            bonus_total += BONUS_CONSTRAINTS_RESPECTED
            bonuses.append(f"Contraintes OK +{BONUS_CONSTRAINTS_RESPECTED}EUR")

        # --- PENALITES ---
        penalties = []
        penalty_total = 0

        # Penalite atterrissage dur
        if landing_vs > 500:
            penalty_total += abs(PENALTY_HARD_LANDING_SEVERE)
            penalties.append(f"Atterro tres dur {PENALTY_HARD_LANDING_SEVERE}EUR")
        elif landing_vs > 300:
            penalty_total += abs(PENALTY_HARD_LANDING_MEDIUM)
            penalties.append(f"Atterro dur {PENALTY_HARD_LANDING_MEDIUM}EUR")

        # Penalite violations contraintes
        if self.constraint_violations > 0:
            violation_penalty = self.constraint_violations * abs(PENALTY_CONSTRAINT_VIOLATION)
            penalty_total += violation_penalty
            penalties.append(f"Violations x{self.constraint_violations}: -{violation_penalty:.0f}EUR")

        # Penalite survitesse
        if self.had_overspeed:
            penalty_total += abs(PENALTY_OVERSPEED)
            penalties.append(f"Survitesse {PENALTY_OVERSPEED}EUR")

        # === TOTAL ===
        total_pay = base_salary + per_diem + bonus_total - penalty_total

        # Ajouter au compte en banque
        self.score += total_pay
        self.missions_completed += 1

        # === MISE A JOUR CAREER SYSTEM ===
        if CAREER_SYSTEM_AVAILABLE and self.pilot:
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
            if self.current_company:
                # Performance score based on violations and landing quality
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

        # === MISE A JOUR INTERFACE ===
        self.progress_bar.set(1.0)
        self.progress_bar.configure(progress_color="#00FF00")
        self.progress_label.configure(text="100% - MISSION ACCOMPLIE!")

        # Formater le detail de la paie
        bonus_str = ", ".join(bonuses) if bonuses else "Aucun"
        penalty_str = ", ".join(penalties) if penalties else "Aucune"

        result_text = (
            f"\n\n{'='*35}\n"
            f"FICHE DE PAIE\n"
            f"{'='*35}\n"
            f"Temps de vol: {self.flight_time_hours:.1f}h\n"
            f"Tarif horaire: {hourly_rate} EUR/h\n"
            f"{'─'*35}\n"
            f"Salaire base: {base_salary:.2f} EUR\n"
            f"Per diem: +{per_diem:.2f} EUR\n"
            f"Bonus: +{bonus_total:.2f} EUR\n"
            f"  ({bonus_str})\n"
            f"Penalites: -{penalty_total:.2f} EUR\n"
            f"  ({penalty_str})\n"
            f"{'─'*35}\n"
            f"TOTAL: {'+' if total_pay >= 0 else ''}{total_pay:.2f} EUR\n"
            f"{'='*35}"
        )

        current_text = self.mission_text.cget("text")
        self.mission_text.configure(text=current_text + result_text)

        play_success_sound()
        self.mission_active = False
        self._save_game()

        # Reset progression
        self.mission_started = False
        self.mission_progress = 0

        # Mettre a jour le score
        color = "#00FF00" if self.score >= 0 else "#FF4444"
        self.score_label.configure(text=f"COMPTE EN BANQUE: {self.score:.2f} EUR", text_color=color)

        category = self.aircraft_info.get('category', 'light_piston')
        hourly_rate = PILOT_HOURLY_RATES.get(category, 55)
        self.stats_label.configure(
            text=f"Missions: {self.missions_completed} | Tarif: {hourly_rate}EUR/h ({category})"
        )

    def _show_upgrade_notification(self, old_license: str, new_license: str):
        """Affiche une notification de montee en licence"""
        try:
            # Create popup window
            popup = ctk.CTkToplevel(self)
            popup.title("LICENCE OBTENUE!")
            popup.geometry("400x200")
            popup.resizable(False, False)
            popup.attributes('-topmost', True)

            # Center on screen
            popup.update_idletasks()
            x = (popup.winfo_screenwidth() - 400) // 2
            y = (popup.winfo_screenheight() - 200) // 2
            popup.geometry(f"400x200+{x}+{y}")

            # Content
            ctk.CTkLabel(
                popup, text="FELICITATIONS!",
                font=ctk.CTkFont(size=24, weight="bold"),
                text_color=COLORS['positive']
            ).pack(pady=(20, 10))

            ctk.CTkLabel(
                popup, text=f"Vous avez obtenu la licence {new_license}!",
                font=ctk.CTkFont(size=16),
                text_color="#FFFFFF"
            ).pack(pady=5)

            ctk.CTkLabel(
                popup, text=f"{old_license} → {new_license}",
                font=ctk.CTkFont(size=14),
                text_color=LICENSE_COLORS.get(new_license, COLORS['accent'])
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

    def _check_constraints(self, bank_angle, altitude, vertical_speed, on_ground, airspeed):
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
                self.had_overspeed = True  # Tracker survitesse
        elif ctype == "vs_max" and vertical_speed is not None:
            violation = abs(vertical_speed) > cvalue

        if violation:
            self.constraint_violations += 1  # Compteur violations
            self.score_label.configure(text_color="#FF4444")
            if self.penalty_cooldown == 0:
                play_penalty_sound()
                self.penalty_cooldown = 3
        else:
            color = "#00FF00" if self.score >= 0 else "#FF4444"
            self.score_label.configure(text_color=color)

        # Enregistrer le VS a l'atterrissage
        if on_ground and not self.was_on_ground:
            vs = vertical_speed if vertical_speed else 0
            self.max_vs_landing = abs(vs)  # Enregistrer pour le calcul de paie

            # Afficher feedback immediat (sans modifier le score - sera fait a la fin)
            if abs(vs) < 100:
                feedback = "Atterrissage parfait!"
            elif abs(vs) < 200:
                feedback = "Bon atterrissage"
            elif abs(vs) < 300:
                feedback = "Atterrissage correct"
            elif abs(vs) < 500:
                feedback = "Atterrissage un peu dur..."
            else:
                feedback = "ATTERRISSAGE TRES DUR!"
                play_crash_sound()

            # Note: on ne termine plus la mission ici, elle se termine au parking
            logger.info(f"Atterrissage detecte: {vs:.0f} fpm - {feedback}")

        self.was_on_ground = on_ground if on_ground is not None else self.was_on_ground
        color = "#00FF00" if self.score >= 0 else "#FF4444"
        self.score_label.configure(text=f"COMPTE EN BANQUE: {self.score:.2f} EUR", text_color=color)

        category = self.aircraft_info.get('category', 'light_piston')
        hourly_rate = PILOT_HOURLY_RATES.get(category, 55)
        self.stats_label.configure(
            text=f"Missions: {self.missions_completed} | Tarif: {hourly_rate}EUR/h | Violations: {self.constraint_violations}"
        )

    def _save_game(self):
        self.save_data = {"score": self.score, "missions_completed": self.missions_completed}
        save_game(self.save_data)

    def _reset_score(self):
        self.score = 100.00
        self.missions_completed = 0
        self.score_label.configure(text=f"COMPTE EN BANQUE: {self.score:.2f} EUR", text_color="#00FF00")
        self.stats_label.configure(text=f"Missions: {self.missions_completed} | Tarif horaire selon avion")
        self._save_game()

    def _on_close(self):
        self._save_game()
        self._save_config()
        if self.sim:
            try:
                self.sim.exit()
            except:
                pass
        self.destroy()

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("   MSFS 2024 - Mission Generator")
    print("=" * 50)
    Path("sounds").mkdir(exist_ok=True)
    app = MissionGeneratorApp()
    app.mainloop()
