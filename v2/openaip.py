"""
OpenAIP Integration for V2
Fetches real-world aviation data: airports, navaids, airspaces, and procedures
https://www.openaip.net/
"""

import logging
import json
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("MissionGenerator.OpenAIP")

# Try to import requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests module not available - OpenAIP disabled")


# OpenAIP API configuration
OPENAIP_BASE_URL = "https://api.core.openaip.net/api"
OPENAIP_API_KEY = ""  # Free tier - no key needed for basic queries

# Cache directory
CACHE_DIR = Path(__file__).parent / "cache" / "openaip"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Navaid:
    """Navigation aid (VOR, NDB, etc.)"""
    id: str
    name: str
    type: str  # VOR, VORDME, NDB, DME
    lat: float
    lon: float
    frequency: str
    identifier: str  # 3-letter identifier

    def to_waypoint(self) -> Dict:
        return {
            'id': self.identifier,
            'name': self.name,
            'lat': self.lat,
            'lon': self.lon,
            'type': self.type
        }


@dataclass
class Waypoint:
    """Navigation waypoint/fix"""
    id: str
    name: str
    lat: float
    lon: float
    type: str = "FIX"

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'lat': self.lat,
            'lon': self.lon,
            'type': self.type
        }


@dataclass
class ApproachProcedure:
    """Instrument approach procedure"""
    name: str
    runway: str
    type: str  # ILS, VOR, RNAV, NDB
    waypoints: List[Dict]


class OpenAIPClient:
    """Client for OpenAIP API"""

    def __init__(self, api_key: str = ""):
        self._api_key = api_key
        self._session = None
        self._cache: Dict = {}

        # Load cache from disk
        self._load_cache()

    def _get_session(self):
        """Get or create requests session"""
        if not REQUESTS_AVAILABLE:
            return None
        if self._session is None:
            self._session = requests.Session()
            if self._api_key:
                self._session.headers['x-openaip-api-key'] = self._api_key
        return self._session

    def _load_cache(self):
        """Load cache from disk"""
        cache_file = CACHE_DIR / "openaip_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                logger.info(f"OpenAIP cache loaded: {len(self._cache)} entries")
            except Exception as e:
                logger.warning(f"Failed to load OpenAIP cache: {e}")
                self._cache = {}

    def _save_cache(self):
        """Save cache to disk"""
        cache_file = CACHE_DIR / "openaip_cache.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f)
        except Exception as e:
            logger.warning(f"Failed to save OpenAIP cache: {e}")

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with caching"""
        session = self._get_session()
        if not session:
            return None

        # Create cache key
        cache_key = f"{endpoint}_{json.dumps(params or {}, sort_keys=True)}"

        # Check cache
        if cache_key in self._cache:
            logger.debug(f"OpenAIP cache hit: {endpoint}")
            return self._cache[cache_key]

        try:
            url = f"{OPENAIP_BASE_URL}/{endpoint}"
            response = session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self._cache[cache_key] = data
                self._save_cache()
                return data
            else:
                logger.warning(f"OpenAIP API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"OpenAIP request failed: {e}")
            return None

    def get_navaids_near(self, lat: float, lon: float, radius_nm: float = 50) -> List[Navaid]:
        """
        Get navaids near a position

        Args:
            lat, lon: Center position
            radius_nm: Search radius in nautical miles

        Returns:
            List of Navaid objects
        """
        # Convert nm to meters for API
        radius_m = radius_nm * 1852

        params = {
            'pos': f"{lon},{lat}",
            'dist': int(radius_m),
            'type': '0,1,2,3,4,5'  # All navaid types
        }

        data = self._make_request('navaids', params)
        if not data or 'items' not in data:
            return []

        navaids = []
        for item in data['items']:
            try:
                navaid = Navaid(
                    id=item.get('_id', ''),
                    name=item.get('name', ''),
                    type=self._navaid_type_name(item.get('type', 0)),
                    lat=item.get('geometry', {}).get('coordinates', [0, 0])[1],
                    lon=item.get('geometry', {}).get('coordinates', [0, 0])[0],
                    frequency=item.get('frequency', ''),
                    identifier=item.get('identifier', '')[:5]
                )
                navaids.append(navaid)
            except Exception as e:
                logger.debug(f"Failed to parse navaid: {e}")

        logger.info(f"Found {len(navaids)} navaids near {lat:.2f}, {lon:.2f}")
        return navaids

    def _navaid_type_name(self, type_code: int) -> str:
        """Convert navaid type code to name"""
        types = {
            0: 'DME',
            1: 'NDB',
            2: 'VOR',
            3: 'VORDME',
            4: 'VORTAC',
            5: 'TACAN'
        }
        return types.get(type_code, 'UNKNOWN')

    def get_waypoints_near(self, lat: float, lon: float, radius_nm: float = 50) -> List[Waypoint]:
        """
        Get reporting points/fixes near a position

        Args:
            lat, lon: Center position
            radius_nm: Search radius in nautical miles

        Returns:
            List of Waypoint objects
        """
        radius_m = radius_nm * 1852

        params = {
            'pos': f"{lon},{lat}",
            'dist': int(radius_m)
        }

        data = self._make_request('reporting-points', params)
        if not data or 'items' not in data:
            return []

        waypoints = []
        for item in data['items']:
            try:
                wpt = Waypoint(
                    id=item.get('identifier', item.get('name', ''))[:5],
                    name=item.get('name', ''),
                    lat=item.get('geometry', {}).get('coordinates', [0, 0])[1],
                    lon=item.get('geometry', {}).get('coordinates', [0, 0])[0],
                    type='FIX'
                )
                waypoints.append(wpt)
            except Exception as e:
                logger.debug(f"Failed to parse waypoint: {e}")

        logger.info(f"Found {len(waypoints)} waypoints near {lat:.2f}, {lon:.2f}")
        return waypoints

    def get_airport_info(self, icao: str) -> Optional[Dict]:
        """
        Get detailed airport information

        Args:
            icao: ICAO airport code

        Returns:
            Airport data dictionary
        """
        params = {'search': icao}
        data = self._make_request('airports', params)

        if not data or 'items' not in data:
            return None

        # Find exact match
        for item in data['items']:
            if item.get('icaoCode', '').upper() == icao.upper():
                return item

        return None

    def generate_approach_waypoints(self, arr_lat: float, arr_lon: float,
                                    runway_heading: float,
                                    search_radius_nm: float = 30) -> List[Dict]:
        """
        Generate realistic approach waypoints using real navaids and fixes

        Args:
            arr_lat, arr_lon: Arrival airport coordinates
            runway_heading: Runway heading in degrees
            search_radius_nm: Search radius for navaids

        Returns:
            List of waypoint dicts for the approach
        """
        approach_waypoints = []

        # Get navaids near the airport
        navaids = self.get_navaids_near(arr_lat, arr_lon, search_radius_nm)
        waypoints = self.get_waypoints_near(arr_lat, arr_lon, search_radius_nm)

        # Calculate approach course (opposite of runway heading)
        approach_course = (runway_heading + 180) % 360

        # Find best navaid/waypoint for IAF (10-15nm out on approach course)
        best_iaf = None
        best_iaf_score = float('inf')

        all_points = [(n.lat, n.lon, n.identifier, 'NAV') for n in navaids]
        all_points += [(w.lat, w.lon, w.id, 'FIX') for w in waypoints]

        for pt_lat, pt_lon, pt_id, pt_type in all_points:
            # Calculate distance and bearing from airport
            dist = self._haversine_nm(arr_lat, arr_lon, pt_lat, pt_lon)
            bearing = self._calculate_bearing(arr_lat, arr_lon, pt_lat, pt_lon)

            # Score: prefer points 8-15nm out, on the approach course (±30°)
            bearing_diff = abs((bearing - approach_course + 180) % 360 - 180)

            if 8 <= dist <= 20 and bearing_diff <= 45:
                score = abs(dist - 12) + bearing_diff * 0.5
                if score < best_iaf_score:
                    best_iaf_score = score
                    best_iaf = {
                        'id': pt_id,
                        'lat': pt_lat,
                        'lon': pt_lon,
                        'alt': 3000,
                        'type': pt_type
                    }

        # Find best FAF (4-6nm out)
        best_faf = None
        best_faf_score = float('inf')

        for pt_lat, pt_lon, pt_id, pt_type in all_points:
            dist = self._haversine_nm(arr_lat, arr_lon, pt_lat, pt_lon)
            bearing = self._calculate_bearing(arr_lat, arr_lon, pt_lat, pt_lon)
            bearing_diff = abs((bearing - approach_course + 180) % 360 - 180)

            if 3 <= dist <= 8 and bearing_diff <= 30:
                score = abs(dist - 5) + bearing_diff * 0.3
                if score < best_faf_score:
                    best_faf_score = score
                    best_faf = {
                        'id': pt_id,
                        'lat': pt_lat,
                        'lon': pt_lon,
                        'alt': 1500,
                        'type': pt_type
                    }

        # If we found real waypoints, use them
        if best_iaf:
            approach_waypoints.append(best_iaf)
            logger.info(f"Using real IAF: {best_iaf['id']}")

        if best_faf:
            approach_waypoints.append(best_faf)
            logger.info(f"Using real FAF: {best_faf['id']}")

        # If no real waypoints found, generate synthetic ones on centerline
        if not approach_waypoints:
            logger.info("No suitable navaids found, generating synthetic approach")
            approach_waypoints = self._generate_synthetic_approach(
                arr_lat, arr_lon, runway_heading
            )

        return approach_waypoints

    def _generate_synthetic_approach(self, arr_lat: float, arr_lon: float,
                                     runway_heading: float) -> List[Dict]:
        """Generate synthetic approach waypoints on extended centerline"""
        waypoints = []
        approach_course = (runway_heading + 180) % 360

        # IAF at 10nm
        iaf_pos = self._calculate_position(arr_lat, arr_lon, approach_course, 10)
        waypoints.append({
            'id': 'IAF',
            'lat': iaf_pos[0],
            'lon': iaf_pos[1],
            'alt': 3000,
            'type': 'USER'
        })

        # FAF at 5nm
        faf_pos = self._calculate_position(arr_lat, arr_lon, approach_course, 5)
        waypoints.append({
            'id': 'FAF',
            'lat': faf_pos[0],
            'lon': faf_pos[1],
            'alt': 1500,
            'type': 'USER'
        })

        return waypoints

    def _haversine_nm(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in nautical miles"""
        R = 3440.065  # Earth radius in nm

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing from point 1 to point 2"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon = math.radians(lon2 - lon1)

        x = math.sin(dlon) * math.cos(lat2_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)

        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360

    def _calculate_position(self, lat: float, lon: float, bearing: float, distance_nm: float) -> Tuple[float, float]:
        """Calculate position at bearing and distance from start point"""
        R = 3440.065  # Earth radius in nm

        lat_rad = math.radians(lat)
        bearing_rad = math.radians(bearing)
        d = distance_nm / R

        new_lat = math.asin(
            math.sin(lat_rad) * math.cos(d) +
            math.cos(lat_rad) * math.sin(d) * math.cos(bearing_rad)
        )
        new_lon = math.radians(lon) + math.atan2(
            math.sin(bearing_rad) * math.sin(d) * math.cos(lat_rad),
            math.cos(d) - math.sin(lat_rad) * math.sin(new_lat)
        )

        return (math.degrees(new_lat), math.degrees(new_lon))

    def build_flight_route(self, dep_lat: float, dep_lon: float,
                          arr_lat: float, arr_lon: float,
                          arr_runway_heading: float,
                          cruise_alt: int = 10000) -> List[Dict]:
        """
        Build a complete flight route using real navaids

        Args:
            dep_lat, dep_lon: Departure coordinates
            arr_lat, arr_lon: Arrival coordinates
            arr_runway_heading: Arrival runway heading
            cruise_alt: Cruise altitude in feet

        Returns:
            Complete list of waypoints for the route
        """
        route = []

        # Calculate total distance
        total_dist = self._haversine_nm(dep_lat, dep_lon, arr_lat, arr_lon)

        if total_dist < 10:
            # Short flight - just approach waypoints
            return self.generate_approach_waypoints(arr_lat, arr_lon, arr_runway_heading)

        # Get enroute navaids
        mid_lat = (dep_lat + arr_lat) / 2
        mid_lon = (dep_lon + arr_lon) / 2

        enroute_navaids = self.get_navaids_near(mid_lat, mid_lon, total_dist / 2)

        # Calculate direct track bearing
        track = self._calculate_bearing(dep_lat, dep_lon, arr_lat, arr_lon)

        # Find navaids along the route (within 20nm of track, spaced appropriately)
        route_navaids = []

        for navaid in enroute_navaids:
            # Check distance from departure
            dist_from_dep = self._haversine_nm(dep_lat, dep_lon, navaid.lat, navaid.lon)

            # Check bearing from departure
            bearing_to_nav = self._calculate_bearing(dep_lat, dep_lon, navaid.lat, navaid.lon)
            bearing_diff = abs((bearing_to_nav - track + 180) % 360 - 180)

            # Accept if roughly on track and not too close to airports
            if bearing_diff < 30 and 20 < dist_from_dep < (total_dist - 20):
                route_navaids.append((dist_from_dep, navaid))

        # Sort by distance and take up to 5 waypoints
        route_navaids.sort(key=lambda x: x[0])

        # Space them out (minimum 30nm apart)
        last_dist = 0
        for dist, navaid in route_navaids:
            if dist - last_dist >= 30 and len(route) < 5:
                route.append({
                    'id': navaid.identifier,
                    'lat': navaid.lat,
                    'lon': navaid.lon,
                    'alt': cruise_alt,
                    'type': navaid.type
                })
                last_dist = dist
                logger.info(f"Added enroute waypoint: {navaid.identifier} ({navaid.type})")

        # Add approach waypoints
        approach = self.generate_approach_waypoints(arr_lat, arr_lon, arr_runway_heading)
        route.extend(approach)

        return route


# Global client instance
_openaip_client: Optional[OpenAIPClient] = None

def get_openaip_client(api_key: str = None) -> OpenAIPClient:
    """Get or create global OpenAIP client"""
    global _openaip_client
    if _openaip_client is None:
        _openaip_client = OpenAIPClient(api_key=api_key or "")
    elif api_key and not _openaip_client._api_key:
        # Update API key if provided and not already set
        _openaip_client._api_key = api_key
        if _openaip_client._session:
            _openaip_client._session.headers['x-openaip-api-key'] = api_key
    return _openaip_client


def set_openaip_api_key(api_key: str) -> None:
    """Set or update the OpenAIP API key"""
    global _openaip_client
    if _openaip_client is not None:
        _openaip_client._api_key = api_key
        if _openaip_client._session:
            _openaip_client._session.headers['x-openaip-api-key'] = api_key
        logger.info("OpenAIP API key updated")
    else:
        # Create client with API key
        _openaip_client = OpenAIPClient(api_key=api_key)
        logger.info("OpenAIP client created with API key")
