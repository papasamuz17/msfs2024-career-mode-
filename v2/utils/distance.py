"""
Distance Calculation Utilities for V2
Accurate distance calculations via waypoints instead of direct
"""

import math
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger("MissionGenerator.Utils.Distance")


@dataclass
class Waypoint:
    """A geographic waypoint"""
    id: str
    lat: float
    lon: float
    name: str = ""
    altitude_ft: float = 0.0


def calculate_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great circle distance between two points in nautical miles

    Args:
        lat1, lon1: First point coordinates (degrees)
        lat2, lon2: Second point coordinates (degrees)

    Returns:
        Distance in nautical miles
    """
    R = 3440.065  # Earth radius in nautical miles

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate initial bearing from point 1 to point 2

    Args:
        lat1, lon1: Start point coordinates (degrees)
        lat2, lon2: End point coordinates (degrees)

    Returns:
        Bearing in degrees (0-360)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)

    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def calculate_distance_via_waypoints(waypoints: List[Waypoint]) -> Tuple[float, List[float]]:
    """
    Calculate total distance through a series of waypoints

    Args:
        waypoints: List of waypoints in order

    Returns:
        Tuple of (total_distance_nm, list of segment distances)
    """
    if len(waypoints) < 2:
        return 0.0, []

    segments = []
    total = 0.0

    for i in range(len(waypoints) - 1):
        wp1 = waypoints[i]
        wp2 = waypoints[i + 1]

        distance = calculate_distance_nm(wp1.lat, wp1.lon, wp2.lat, wp2.lon)
        segments.append(distance)
        total += distance

    return total, segments


def interpolate_position(lat1: float, lon1: float, lat2: float, lon2: float,
                        fraction: float) -> Tuple[float, float]:
    """
    Interpolate a position along a great circle route

    Args:
        lat1, lon1: Start point
        lat2, lon2: End point
        fraction: Fraction of distance (0-1)

    Returns:
        Tuple of (latitude, longitude)
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Calculate angular distance
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    angular_distance = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    if angular_distance == 0:
        return lat1, lon1

    # Calculate interpolated position
    A = math.sin((1 - fraction) * angular_distance) / math.sin(angular_distance)
    B = math.sin(fraction * angular_distance) / math.sin(angular_distance)

    x = A * math.cos(lat1_rad) * math.cos(lon1_rad) + B * math.cos(lat2_rad) * math.cos(lon2_rad)
    y = A * math.cos(lat1_rad) * math.sin(lon1_rad) + B * math.cos(lat2_rad) * math.sin(lon2_rad)
    z = A * math.sin(lat1_rad) + B * math.sin(lat2_rad)

    lat = math.degrees(math.atan2(z, math.sqrt(x * x + y * y)))
    lon = math.degrees(math.atan2(y, x))

    return lat, lon


class DistanceCalculator:
    """Advanced distance calculator with route optimization"""

    def __init__(self):
        self._navaids: List[Waypoint] = []

    def load_navaids(self, navaids_data: Dict) -> None:
        """Load navaids from JSON data"""
        self._navaids.clear()

        for vor in navaids_data.get('vors', []):
            self._navaids.append(Waypoint(
                id=vor['id'],
                lat=vor['lat'],
                lon=vor['lon'],
                name=vor.get('name', vor['id'])
            ))

        for fix in navaids_data.get('intersections', []):
            self._navaids.append(Waypoint(
                id=fix['id'],
                lat=fix['lat'],
                lon=fix['lon'],
                name=fix.get('name', fix['id'])
            ))

        logger.info(f"Loaded {len(self._navaids)} navaids for distance calculations")

    def calculate_route_distance(self, departure: Dict, arrival: Dict,
                                 via_waypoints: List[Dict] = None) -> Dict:
        """
        Calculate route distance with breakdown

        Args:
            departure: Departure airport dict with lat/lon
            arrival: Arrival airport dict with lat/lon
            via_waypoints: Optional list of waypoints to route through

        Returns:
            Dict with distance details
        """
        dep_lat = departure['lat']
        dep_lon = departure['lon']
        arr_lat = arrival['lat']
        arr_lon = arrival['lon']

        # Direct distance
        direct_distance = calculate_distance_nm(dep_lat, dep_lon, arr_lat, arr_lon)

        # Route distance
        if via_waypoints:
            waypoints = [Waypoint(id='DEP', lat=dep_lat, lon=dep_lon)]
            for wp in via_waypoints:
                waypoints.append(Waypoint(
                    id=wp.get('id', 'WPT'),
                    lat=wp['lat'],
                    lon=wp['lon']
                ))
            waypoints.append(Waypoint(id='ARR', lat=arr_lat, lon=arr_lon))

            route_distance, segments = calculate_distance_via_waypoints(waypoints)
        else:
            route_distance = direct_distance
            segments = [direct_distance]

        # Calculate efficiency
        efficiency = (direct_distance / route_distance * 100) if route_distance > 0 else 100

        return {
            'direct_distance_nm': direct_distance,
            'route_distance_nm': route_distance,
            'segments': segments,
            'num_waypoints': len(via_waypoints) if via_waypoints else 0,
            'efficiency_percent': efficiency,
            'extra_distance_nm': route_distance - direct_distance
        }

    def find_navaids_on_route(self, dep_lat: float, dep_lon: float,
                              arr_lat: float, arr_lon: float,
                              max_deviation_nm: float = 50) -> List[Waypoint]:
        """
        Find navaids that are close to the direct route

        Args:
            dep_lat, dep_lon: Departure coordinates
            arr_lat, arr_lon: Arrival coordinates
            max_deviation_nm: Maximum deviation from direct route

        Returns:
            List of navaids near the route, sorted by position along route
        """
        route_distance = calculate_distance_nm(dep_lat, dep_lon, arr_lat, arr_lon)

        if route_distance == 0:
            return []

        nearby = []

        for navaid in self._navaids:
            # Distance from departure
            dist_from_dep = calculate_distance_nm(dep_lat, dep_lon, navaid.lat, navaid.lon)

            # Skip if beyond arrival
            if dist_from_dep > route_distance:
                continue

            # Skip if too close to departure or arrival
            dist_to_arr = calculate_distance_nm(navaid.lat, navaid.lon, arr_lat, arr_lon)
            if dist_from_dep < 10 or dist_to_arr < 10:
                continue

            # Calculate cross-track distance (deviation from route)
            # Using simplified calculation
            progress = dist_from_dep / route_distance
            expected_lat, expected_lon = interpolate_position(
                dep_lat, dep_lon, arr_lat, arr_lon, progress
            )

            deviation = calculate_distance_nm(navaid.lat, navaid.lon, expected_lat, expected_lon)

            if deviation <= max_deviation_nm:
                nearby.append((navaid, dist_from_dep, deviation))

        # Sort by distance from departure
        nearby.sort(key=lambda x: x[1])

        return [n[0] for n in nearby]

    def calculate_estimated_time(self, distance_nm: float, ground_speed_kts: float) -> float:
        """
        Calculate estimated time enroute

        Args:
            distance_nm: Distance in nautical miles
            ground_speed_kts: Ground speed in knots

        Returns:
            Time in hours
        """
        if ground_speed_kts <= 0:
            return 0.0
        return distance_nm / ground_speed_kts

    def calculate_distance_remaining(self, current_lat: float, current_lon: float,
                                    destination_lat: float, destination_lon: float,
                                    via_waypoints: List[Waypoint] = None,
                                    current_waypoint_index: int = 0) -> float:
        """
        Calculate remaining distance to destination

        Args:
            current_lat, current_lon: Current position
            destination_lat, destination_lon: Destination
            via_waypoints: Remaining waypoints
            current_waypoint_index: Index of next waypoint

        Returns:
            Remaining distance in nautical miles
        """
        if not via_waypoints or current_waypoint_index >= len(via_waypoints):
            # Direct to destination
            return calculate_distance_nm(
                current_lat, current_lon,
                destination_lat, destination_lon
            )

        # Distance to next waypoint
        total = 0.0
        next_wp = via_waypoints[current_waypoint_index]
        total += calculate_distance_nm(current_lat, current_lon, next_wp.lat, next_wp.lon)

        # Distance through remaining waypoints
        for i in range(current_waypoint_index, len(via_waypoints) - 1):
            wp1 = via_waypoints[i]
            wp2 = via_waypoints[i + 1]
            total += calculate_distance_nm(wp1.lat, wp1.lon, wp2.lat, wp2.lon)

        # Distance from last waypoint to destination
        last_wp = via_waypoints[-1]
        total += calculate_distance_nm(last_wp.lat, last_wp.lon, destination_lat, destination_lon)

        return total
