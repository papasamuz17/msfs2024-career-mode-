"""
Aviation API Module V2 - Enhanced with Caching and Weather Integration
- METAR (weather) with unified cache
- Global airports database
- Runway calculations
- Integration with V2 optimization modules
"""

import requests
import re
import math
import random
import logging
from typing import Optional, Tuple, List, Dict
from pathlib import Path

# Import V2 optimization modules
try:
    from optimization import get_cache, cached
    from optimization.airport_index import AirportSpatialIndex, get_airport_index
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False

logger = logging.getLogger("MissionGenerator.V2.AviationAPI")

# ============================================================================
# API CONFIGURATION
# ============================================================================

NOAA_METAR_URL = "https://aviationweather.gov/api/data/metar"
OURAIRPORTS_AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
OURAIRPORTS_RUNWAYS_URL = "https://davidmegginson.github.io/ourairports-data/runways.csv"

# Cache for non-optimized mode
_airports_cache = None
_runways_cache = None

# ============================================================================
# METAR - AVIATION WEATHER
# ============================================================================

def fetch_metar(icao: str, use_cache: bool = True) -> Optional[str]:
    """
    Fetch METAR from NOAA with optional caching

    Args:
        icao: Airport ICAO code
        use_cache: Use unified cache (default True)

    Returns:
        Raw METAR string or None
    """
    icao = icao.upper()
    cache_key = f"metar_{icao}"

    # Try cache first
    if use_cache and OPTIMIZATION_AVAILABLE:
        cache = get_cache()
        cached_metar = cache.get(cache_key)
        if cached_metar:
            logger.debug(f"METAR cache hit: {icao}")
            return cached_metar

    try:
        response = requests.get(
            NOAA_METAR_URL,
            params={"ids": icao, "format": "raw"},
            timeout=10
        )
        if response.status_code == 200 and response.text.strip():
            metar = response.text.strip().split('\n')[0]

            # Store in cache (15 min TTL for METAR)
            if use_cache and OPTIMIZATION_AVAILABLE:
                cache = get_cache()
                cache.set(cache_key, metar, ttl=900)  # 15 minutes

            logger.debug(f"METAR {icao}: {metar}")
            return metar
    except Exception as e:
        logger.warning(f"METAR error {icao}: {e}")

    return None


def parse_metar_wind(metar: str) -> Optional[Dict]:
    """
    Parse wind from METAR

    Returns:
        {"direction": int (degrees), "speed": int (kts), "gust": int or None}
    """
    if not metar:
        return None

    # METAR wind pattern: 27015G25KT or 270/15KT or VRB05KT or 00000KT
    wind_pattern = r'\b(VRB|\d{3})(\d{2,3})(G(\d{2,3}))?(KT|MPS)\b'
    match = re.search(wind_pattern, metar)

    if match:
        direction_str = match.group(1)
        speed = int(match.group(2))
        gust = int(match.group(4)) if match.group(4) else None
        unit = match.group(5)

        # Convert MPS to KT if needed
        if unit == "MPS":
            speed = int(speed * 1.944)
            if gust:
                gust = int(gust * 1.944)

        # Variable wind
        if direction_str == "VRB":
            direction = None
        else:
            direction = int(direction_str)

        return {
            "direction": direction,
            "speed": speed,
            "gust": gust,
            "raw": match.group(0)
        }

    return None


def parse_metar_visibility(metar: str) -> Optional[float]:
    """
    Parse visibility from METAR

    Returns:
        Visibility in statute miles
    """
    if not metar:
        return None

    # Pattern for visibility in SM (statute miles)
    vis_pattern = r'\b(\d+)SM\b'
    match = re.search(vis_pattern, metar)
    if match:
        return float(match.group(1))

    # Pattern for fractional visibility
    frac_pattern = r'\b(\d+)/(\d+)SM\b'
    match = re.search(frac_pattern, metar)
    if match:
        return float(match.group(1)) / float(match.group(2))

    # Pattern for visibility in meters (European METAR)
    meters_pattern = r'\b(\d{4})\b'
    match = re.search(meters_pattern, metar)
    if match:
        meters = int(match.group(1))
        return meters / 1609.34  # Convert to SM

    return 10.0  # Default good visibility


def get_weather_info(icao: str) -> Dict:
    """Get complete weather info for an airport"""
    metar = fetch_metar(icao)
    wind = parse_metar_wind(metar) if metar else None
    visibility = parse_metar_visibility(metar) if metar else None

    return {
        "icao": icao,
        "metar": metar,
        "wind": wind,
        "visibility_sm": visibility,
        "wind_description": format_wind_description(wind) if wind else "Wind unknown"
    }


def format_wind_description(wind: Dict) -> str:
    """Format readable wind description"""
    if not wind:
        return "Calm"

    if wind["direction"] is None:
        desc = f"Variable {wind['speed']}kt"
    else:
        desc = f"{wind['direction']:03d}/{wind['speed']}kt"

    if wind.get("gust"):
        desc += f" (gusts {wind['gust']}kt)"

    return desc


# ============================================================================
# GLOBAL AIRPORTS DATABASE
# ============================================================================

def parse_csv_line(line: str) -> List[str]:
    """Parse CSV line with quote handling"""
    parts = []
    current = ""
    in_quotes = False

    for char in line:
        if char == '"':
            in_quotes = not in_quotes
            current += char
        elif char == ',' and not in_quotes:
            parts.append(current)
            current = ""
        else:
            current += char

    parts.append(current)
    return parts


def fetch_airports_database(use_index: bool = True) -> List[Dict]:
    """
    Download OurAirports database

    Args:
        use_index: Use spatial index for faster queries (V2 optimization)

    Returns:
        List of airport dictionaries
    """
    global _airports_cache

    # Try spatial index first (V2 optimization)
    if use_index and OPTIMIZATION_AVAILABLE:
        index = get_airport_index()
        if index._airports:
            logger.debug(f"Using spatial index with {len(index._airports)} airports")
            return index._airports

    if _airports_cache is not None:
        return _airports_cache

    logger.info("Downloading global airports database...")

    try:
        response = requests.get(OURAIRPORTS_AIRPORTS_URL, timeout=30)
        if response.status_code != 200:
            logger.error(f"Airport download error: {response.status_code}")
            return []

        # Parse CSV
        lines = response.text.strip().split('\n')
        headers = lines[0].split(',')
        idx = {h.strip('"'): i for i, h in enumerate(headers)}

        airports = []
        for line in lines[1:]:
            parts = parse_csv_line(line)
            if len(parts) < len(headers):
                continue

            try:
                airport_type = parts[idx.get('type', 2)].strip('"')

                # Filter: keep only large and medium airports
                if airport_type not in ['large_airport', 'medium_airport']:
                    continue

                icao = parts[idx.get('ident', 1)].strip('"')
                name = parts[idx.get('name', 3)].strip('"')
                lat = parts[idx.get('latitude_deg', 4)].strip('"')
                lon = parts[idx.get('longitude_deg', 5)].strip('"')
                country = parts[idx.get('iso_country', 8)].strip('"')
                continent = parts[idx.get('continent', 7)].strip('"')

                # Validate data
                if not icao or len(icao) != 4 or not lat or not lon:
                    continue

                airports.append({
                    "icao": icao,
                    "name": name,
                    "lat": float(lat),
                    "lon": float(lon),
                    "country": country,
                    "continent": continent,
                    "type": airport_type
                })
            except (ValueError, IndexError):
                continue

        _airports_cache = airports

        # Load into spatial index if available
        if use_index and OPTIMIZATION_AVAILABLE:
            index = get_airport_index()
            index.load_airports(airports)

        logger.info(f"Airports database loaded: {len(airports)} airports")
        return airports

    except Exception as e:
        logger.error(f"Airport loading error: {e}")
        return []


def calculate_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in nautical miles between two points"""
    R = 3440.065  # Earth radius in nm
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_random_airports(
    count: int = 2,
    continent: str = None,
    country: str = None,
    min_distance_nm: float = 100,
    max_distance_nm: float = 1500,
    departure_lat: float = None,
    departure_lon: float = None
) -> List[Dict]:
    """
    Select random airports with constraints

    Args:
        count: Number of airports (default 2)
        continent: Filter by continent (EU, NA, SA, AS, AF, OC)
        country: Filter by country code
        min_distance_nm: Minimum distance between airports
        max_distance_nm: Maximum distance between airports
        departure_lat/lon: Optional fixed departure coordinates

    Returns:
        List of airport dictionaries
    """
    airports = fetch_airports_database()

    if not airports:
        logger.error("No airports available")
        return []

    # Filter by continent/country if specified
    filtered = airports
    if continent:
        filtered = [a for a in filtered if a['continent'] == continent]
    if country:
        filtered = [a for a in filtered if a['country'] == country]

    if len(filtered) < 2:
        filtered = airports  # Fallback to all airports

    # Select departure airport
    if departure_lat is not None and departure_lon is not None:
        # Find nearest airport to specified coordinates
        departure = min(filtered, key=lambda a: calculate_distance_nm(
            departure_lat, departure_lon, a['lat'], a['lon']
        ))
    else:
        departure = random.choice(filtered)

    # Find arrival airport at appropriate distance
    candidates = []
    for apt in filtered:
        if apt['icao'] == departure['icao']:
            continue

        dist = calculate_distance_nm(
            departure['lat'], departure['lon'],
            apt['lat'], apt['lon']
        )

        if min_distance_nm <= dist <= max_distance_nm:
            candidates.append((apt, dist))

    if not candidates:
        # Relax constraints progressively - try expanding range by 50% first
        relaxed_min = min_distance_nm * 0.5
        relaxed_max = max_distance_nm * 1.5
        for apt in filtered:
            if apt['icao'] != departure['icao']:
                dist = calculate_distance_nm(
                    departure['lat'], departure['lon'],
                    apt['lat'], apt['lon']
                )
                if relaxed_min <= dist <= relaxed_max:
                    candidates.append((apt, dist))

    if not candidates:
        # Last resort - pick the airport closest to the requested max distance
        best = None
        best_diff = float('inf')
        target = (min_distance_nm + max_distance_nm) / 2
        for apt in filtered:
            if apt['icao'] != departure['icao']:
                dist = calculate_distance_nm(
                    departure['lat'], departure['lon'],
                    apt['lat'], apt['lon']
                )
                if dist > 20:
                    diff = abs(dist - target)
                    if diff < best_diff:
                        best_diff = diff
                        best = (apt, dist)
        if best:
            candidates.append(best)

    if not candidates:
        logger.warning("Unable to find valid airport pair")
        return []

    arrival, distance = random.choice(candidates)

    departure['distance_to_arrival'] = distance
    arrival['distance_from_departure'] = distance

    return [departure, arrival]


def find_airports_near(lat: float, lon: float, radius_nm: float = 50, limit: int = 10) -> List[Dict]:
    """
    Find airports near a position using spatial index if available

    Args:
        lat, lon: Center coordinates
        radius_nm: Search radius in nautical miles
        limit: Maximum number of results

    Returns:
        List of airports sorted by distance
    """
    # Use spatial index if available (V2 optimization)
    if OPTIMIZATION_AVAILABLE:
        index = get_airport_index()
        if index._airports:
            return index.find_nearest(lat, lon, radius_nm, limit)

    # Fallback to linear search
    airports = fetch_airports_database()
    nearby = []

    for apt in airports:
        dist = calculate_distance_nm(lat, lon, apt['lat'], apt['lon'])
        if dist <= radius_nm:
            apt_copy = apt.copy()
            apt_copy['distance_nm'] = dist
            nearby.append(apt_copy)

    nearby.sort(key=lambda x: x['distance_nm'])
    return nearby[:limit]


# ============================================================================
# RUNWAYS
# ============================================================================

def fetch_runways_database() -> Dict[str, List[Dict]]:
    """Download runway database"""
    global _runways_cache

    if _runways_cache is not None:
        return _runways_cache

    logger.info("Downloading runway database...")

    try:
        response = requests.get(OURAIRPORTS_RUNWAYS_URL, timeout=30)
        if response.status_code != 200:
            logger.error(f"Runway download error: {response.status_code}")
            return {}

        lines = response.text.strip().split('\n')
        headers = lines[0].split(',')
        idx = {h.strip('"'): i for i, h in enumerate(headers)}

        runways = {}
        for line in lines[1:]:
            parts = parse_csv_line(line)
            if len(parts) < len(headers):
                continue

            try:
                airport_ident = parts[idx.get('airport_ident', 2)].strip('"')
                le_ident = parts[idx.get('le_ident', 8)].strip('"')
                he_ident = parts[idx.get('he_ident', 12)].strip('"')
                le_heading = parts[idx.get('le_heading_degT', 9)].strip('"')
                he_heading = parts[idx.get('he_heading_degT', 13)].strip('"')
                length_ft = parts[idx.get('length_ft', 3)].strip('"')
                width_ft = parts[idx.get('width_ft', 4)].strip('"')
                surface = parts[idx.get('surface', 5)].strip('"')
                is_closed = parts[idx.get('closed', 7)].strip('"')

                if is_closed == '1':
                    continue

                if airport_ident not in runways:
                    runways[airport_ident] = []

                # Add both runway ends
                if le_ident and le_heading:
                    runways[airport_ident].append({
                        "ident": le_ident,
                        "heading": float(le_heading) if le_heading else 0,
                        "length_ft": int(float(length_ft)) if length_ft else 0,
                        "width_ft": int(float(width_ft)) if width_ft else 0,
                        "surface": surface
                    })

                if he_ident and he_heading:
                    runways[airport_ident].append({
                        "ident": he_ident,
                        "heading": float(he_heading) if he_heading else 0,
                        "length_ft": int(float(length_ft)) if length_ft else 0,
                        "width_ft": int(float(width_ft)) if width_ft else 0,
                        "surface": surface
                    })

            except (ValueError, IndexError):
                continue

        _runways_cache = runways
        logger.info(f"Runway database loaded: {len(runways)} airports")
        return runways

    except Exception as e:
        logger.error(f"Runway loading error: {e}")
        return {}


def get_airport_runways(icao: str) -> List[Dict]:
    """Get runways for an airport"""
    runways = fetch_runways_database()
    return runways.get(icao.upper(), [])


def calculate_optimal_runway(icao: str, wind: Dict) -> Optional[Dict]:
    """
    Calculate optimal runway based on wind

    Returns runway with best headwind component
    """
    runways = get_airport_runways(icao)

    if not runways:
        logger.warning(f"No runways found for {icao}")
        return None

    # If no wind or light/variable wind, take longest runway
    if not wind or wind.get('direction') is None or wind.get('speed', 0) < 3:
        longest = max(runways, key=lambda r: r.get('length_ft', 0))
        logger.info(f"{icao}: Light/variable wind, runway {longest['ident']} (longest)")
        return longest

    wind_dir = wind['direction']
    wind_speed = wind['speed']

    best_runway = None
    best_headwind = -999

    for runway in runways:
        heading = runway.get('heading', 0)

        # Calculate angle between wind and runway
        angle_diff = abs(wind_dir - heading)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff

        # Headwind component (positive = headwind, negative = tailwind)
        headwind_component = wind_speed * math.cos(math.radians(angle_diff))

        # Crosswind component
        crosswind_component = abs(wind_speed * math.sin(math.radians(angle_diff)))

        # Penalize runways with excessive crosswind (>15kt)
        if crosswind_component > 15:
            headwind_component -= (crosswind_component - 15) * 0.5

        if headwind_component > best_headwind:
            best_headwind = headwind_component
            best_runway = runway
            best_runway['headwind'] = round(headwind_component, 1)
            best_runway['crosswind'] = round(crosswind_component, 1)

    if best_runway:
        logger.info(f"{icao}: Wind {wind_dir:03d}/{wind_speed}kt -> Runway {best_runway['ident']} "
                   f"(headwind {best_runway['headwind']}kt, crosswind {best_runway['crosswind']}kt)")

    return best_runway


# ============================================================================
# MAIN FUNCTION - COMPLETE MISSION PREPARATION
# ============================================================================

def prepare_mission_data(
    departure_icao: str = None,
    arrival_icao: str = None,
    continent: str = None,
    country: str = None,
    min_distance: float = 100,
    max_distance: float = 1500,
    aircraft_category: str = None
) -> Optional[Dict]:
    """
    Prepare all data for a mission:
    - Airports (random or specified)
    - Weather for both airports
    - Optimal runways based on wind

    Args:
        departure_icao: Optional specific departure
        arrival_icao: Optional specific arrival
        continent: Filter by continent
        country: Filter by country
        min_distance: Minimum distance (nm)
        max_distance: Maximum distance (nm)
        aircraft_category: Aircraft category for distance selection

    Returns:
        Complete mission dictionary
    """

    # Adjust distances based on aircraft category
    if aircraft_category:
        if aircraft_category in ['light_piston', 'helicopter']:
            min_distance = max(50, min_distance)
            max_distance = min(300, max_distance)
        elif aircraft_category in ['twin_piston', 'single_turboprop']:
            min_distance = max(100, min_distance)
            max_distance = min(600, max_distance)
        elif aircraft_category in ['turboprop', 'light_jet']:
            min_distance = max(150, min_distance)
            max_distance = min(1000, max_distance)
        # jet, heavy_jet use full range

    # 1. Airport selection
    if departure_icao and arrival_icao:
        # Specified airports - get their info
        airports = fetch_airports_database()
        departure = next((a for a in airports if a['icao'] == departure_icao.upper()), None)
        arrival = next((a for a in airports if a['icao'] == arrival_icao.upper()), None)

        if not departure or not arrival:
            logger.error(f"Airport(s) not found: {departure_icao}, {arrival_icao}")
            return None

        distance = calculate_distance_nm(
            departure['lat'], departure['lon'],
            arrival['lat'], arrival['lon']
        )
    else:
        # Random selection
        selected = get_random_airports(
            count=2,
            continent=continent,
            country=country,
            min_distance_nm=min_distance,
            max_distance_nm=max_distance
        )

        if len(selected) < 2:
            return None

        departure, arrival = selected
        distance = calculate_distance_nm(
            departure['lat'], departure['lon'],
            arrival['lat'], arrival['lon']
        )

    logger.info(f"Mission: {departure['icao']} ({departure['name']}) -> {arrival['icao']} ({arrival['name']}) - {distance:.0f}nm")

    # 2. Get weather
    dep_weather = get_weather_info(departure['icao'])
    arr_weather = get_weather_info(arrival['icao'])

    # 3. Calculate optimal runways
    dep_runway = calculate_optimal_runway(departure['icao'], dep_weather.get('wind'))
    arr_runway = calculate_optimal_runway(arrival['icao'], arr_weather.get('wind'))

    # 4. Build result
    mission_data = {
        "departure": {
            **departure,
            "weather": dep_weather,
            "runway": dep_runway
        },
        "arrival": {
            **arrival,
            "weather": arr_weather,
            "runway": arr_runway
        },
        "distance_nm": distance,
        "generated_at": None  # Will be filled by caller
    }

    return mission_data


# ============================================================================
# GEOCODING (with cache)
# ============================================================================

def geocode_location(query: str) -> Optional[Dict]:
    """
    Geocode a location name to coordinates (with cache)

    Args:
        query: Location name (city, airport, etc.)

    Returns:
        {"lat": float, "lon": float, "name": str} or None
    """
    cache_key = f"geocode_{query.lower().replace(' ', '_')}"

    # Check cache
    if OPTIMIZATION_AVAILABLE:
        cache = get_cache()
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

    try:
        # Use Nominatim (OpenStreetMap) for geocoding
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 1
        }
        headers = {"User-Agent": "MSFS-MissionGenerator/2.0"}

        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            results = response.json()
            if results:
                result = {
                    "lat": float(results[0]["lat"]),
                    "lon": float(results[0]["lon"]),
                    "name": results[0].get("display_name", query)
                }

                # Cache for 24 hours
                if OPTIMIZATION_AVAILABLE:
                    cache = get_cache()
                    cache.set(cache_key, result, ttl=86400)

                return result
    except Exception as e:
        logger.warning(f"Geocoding error for '{query}': {e}")

    return None


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("=== Aviation API V2 Test ===\n")

    # Test METAR
    print("1. METAR test LFPG:")
    weather = get_weather_info("LFPG")
    print(f"   METAR: {weather['metar']}")
    print(f"   Wind: {weather['wind_description']}")
    print(f"   Visibility: {weather.get('visibility_sm', 'N/A')} SM")

    # Test runways
    print("\n2. Runways test LFPG:")
    runways = get_airport_runways("LFPG")
    for rwy in runways[:4]:
        print(f"   Runway {rwy['ident']}: hdg {rwy['heading']:.0f}, length {rwy['length_ft']}ft")

    # Test optimal runway
    print("\n3. Optimal runway test:")
    if weather['wind']:
        best = calculate_optimal_runway("LFPG", weather['wind'])
        if best:
            print(f"   Best runway: {best['ident']}")

    # Test random mission
    print("\n4. Random European mission test:")
    mission = prepare_mission_data(continent="EU", min_distance=200, max_distance=800)
    if mission:
        dep = mission['departure']
        arr = mission['arrival']
        print(f"   Departure: {dep['icao']} - {dep['name']}")
        print(f"   Departure runway: {dep['runway']['ident'] if dep['runway'] else 'N/A'}")
        print(f"   Departure weather: {dep['weather']['wind_description']}")
        print(f"   Arrival: {arr['icao']} - {arr['name']}")
        print(f"   Arrival runway: {arr['runway']['ident'] if arr['runway'] else 'N/A'}")
        print(f"   Arrival weather: {arr['weather']['wind_description']}")
        print(f"   Distance: {mission['distance_nm']:.0f} nm")

    # Test nearby airports
    print("\n5. Airports near Paris test:")
    nearby = find_airports_near(48.8566, 2.3522, radius_nm=50)
    for apt in nearby[:5]:
        print(f"   {apt['icao']} - {apt['name']} ({apt.get('distance_nm', 0):.1f} nm)")
