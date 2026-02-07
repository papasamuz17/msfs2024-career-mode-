"""
SimConnect Weather System for V2
Reads weather data directly from the simulator instead of external METAR
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Weather")

# Try to import SimConnect
try:
    from SimConnect import SimConnect, AircraftRequests
    SIMCONNECT_AVAILABLE = True
except ImportError:
    SIMCONNECT_AVAILABLE = False


@dataclass
class SimWeather:
    """Weather data from SimConnect"""
    # Temperature
    ambient_temperature_c: float = 15.0
    ambient_temperature_f: float = 59.0

    # Pressure
    barometric_pressure_mb: float = 1013.25
    sea_level_pressure_mb: float = 1013.25

    # Wind
    ambient_wind_velocity_kts: float = 0.0
    ambient_wind_direction_deg: float = 0.0
    aircraft_wind_x: float = 0.0  # Headwind component
    aircraft_wind_z: float = 0.0  # Crosswind component

    # Visibility
    ambient_visibility_m: float = 10000.0
    ambient_visibility_sm: float = 6.2  # Statute miles

    # Precipitation
    ambient_precip_state: int = 0  # 0=None, 1=Rain, 2=Snow
    ambient_precip_rate: float = 0.0

    # Clouds
    ambient_in_cloud: bool = False
    cloud_layer_1_top_ft: float = 0.0
    cloud_layer_1_base_ft: float = 0.0

    # Time
    local_time: str = ""
    zulu_time: str = ""

    # Derived
    is_day: bool = True
    flight_conditions: str = "VFR"  # VFR, MVFR, IFR, LIFR

    # V2 Enhanced data
    density_altitude_ft: float = 0.0    # DENSITY_ALTITUDE - critical for performance
    structural_ice_pct: float = 0.0     # STRUCTURAL_ICE_PCT - icing accumulation (0-1)
    pitot_ice_pct: float = 0.0          # PITOT_ICE_PCT - pitot icing (0-1)
    pressure_altitude_ft: float = 0.0   # PRESSURE_ALTITUDE - altitude from 1013mb
    total_air_temp_c: float = 15.0      # TOTAL_AIR_TEMPERATURE - with ram air effect

    def to_metar_string(self) -> str:
        """Generate a METAR-like string from SimConnect data"""
        # Wind
        wind_dir = int(self.ambient_wind_direction_deg)
        wind_spd = int(self.ambient_wind_velocity_kts)
        wind_str = f"{wind_dir:03d}{wind_spd:02d}KT"

        # Visibility
        vis_sm = self.ambient_visibility_sm
        if vis_sm >= 10:
            vis_str = "P6SM"
        else:
            vis_str = f"{vis_sm:.0f}SM"

        # Precipitation
        precip_str = ""
        if self.ambient_precip_state == 1:
            precip_str = "RA"
        elif self.ambient_precip_state == 2:
            precip_str = "SN"

        # Temperature
        temp_c = int(self.ambient_temperature_c)
        temp_str = f"M{abs(temp_c):02d}" if temp_c < 0 else f"{temp_c:02d}"

        # Altimeter (convert mb to inHg)
        altim_inhg = self.barometric_pressure_mb * 0.02953
        altim_str = f"A{int(altim_inhg * 100):04d}"

        return f"{wind_str} {vis_str} {precip_str} {temp_str}/{temp_str} {altim_str}".strip()

    def get_flight_conditions(self) -> str:
        """Determine flight conditions (VFR/MVFR/IFR/LIFR)"""
        vis_sm = self.ambient_visibility_sm
        ceiling_ft = self.cloud_layer_1_base_ft if self.cloud_layer_1_base_ft > 0 else 99999

        if vis_sm >= 5 and ceiling_ft >= 3000:
            return "VFR"
        elif vis_sm >= 3 and ceiling_ft >= 1000:
            return "MVFR"
        elif vis_sm >= 1 and ceiling_ft >= 500:
            return "IFR"
        else:
            return "LIFR"


class WeatherSimConnect:
    """Reads weather data from SimConnect"""

    # SimConnect weather variables
    WEATHER_VARS = [
        "AMBIENT_TEMPERATURE",
        "BAROMETER_PRESSURE",
        "SEA_LEVEL_PRESSURE",
        "AMBIENT_WIND_VELOCITY",
        "AMBIENT_WIND_DIRECTION",
        "AIRCRAFT_WIND_X",
        "AIRCRAFT_WIND_Z",
        "AMBIENT_VISIBILITY",
        "AMBIENT_PRECIP_STATE",
        "AMBIENT_PRECIP_RATE",
        "AMBIENT_IN_CLOUD",
        "LOCAL_TIME",
        "ZULU_TIME",
        # V2 Enhanced weather variables
        "DENSITY_ALTITUDE",
        "STRUCTURAL_ICE_PCT",
        "PITOT_ICE_PCT",
        "PRESSURE_ALTITUDE",
        "TOTAL_AIR_TEMPERATURE"
    ]

    def __init__(self, sim: 'SimConnect' = None, requests: 'AircraftRequests' = None):
        self._sim = sim
        self._requests = requests
        self._last_weather: Optional[SimWeather] = None
        self._last_update = 0.0

    def set_connection(self, sim: 'SimConnect', requests: 'AircraftRequests') -> None:
        """Set SimConnect connection"""
        self._sim = sim
        self._requests = requests

    def is_connected(self) -> bool:
        """Check if SimConnect is available"""
        return self._sim is not None and self._requests is not None

    def get_weather(self, use_cache: bool = True, max_age_seconds: float = 60) -> Optional[SimWeather]:
        """
        Get current weather from SimConnect

        Args:
            use_cache: Use cached data if fresh enough
            max_age_seconds: Maximum cache age

        Returns:
            SimWeather object or None if unavailable
        """
        import time

        # Check cache
        if use_cache and self._last_weather:
            age = time.time() - self._last_update
            if age < max_age_seconds:
                return self._last_weather

        if not self.is_connected():
            logger.warning("SimConnect not connected for weather")
            return self._create_default_weather()

        try:
            weather = SimWeather()

            # Temperature
            temp = self._safe_get("AMBIENT_TEMPERATURE")
            if temp is not None:
                weather.ambient_temperature_c = float(temp)
                weather.ambient_temperature_f = weather.ambient_temperature_c * 9/5 + 32

            # Pressure
            pressure = self._safe_get("BAROMETER_PRESSURE")
            if pressure is not None:
                # SimConnect returns pressure in inHg * 16, convert to mb
                weather.barometric_pressure_mb = float(pressure) / 16 * 33.8639

            # Wind
            wind_vel = self._safe_get("AMBIENT_WIND_VELOCITY")
            wind_dir = self._safe_get("AMBIENT_WIND_DIRECTION")
            if wind_vel is not None:
                weather.ambient_wind_velocity_kts = float(wind_vel)
            if wind_dir is not None:
                weather.ambient_wind_direction_deg = float(wind_dir)

            # Aircraft-relative wind
            wind_x = self._safe_get("AIRCRAFT_WIND_X")
            wind_z = self._safe_get("AIRCRAFT_WIND_Z")
            if wind_x is not None:
                weather.aircraft_wind_x = float(wind_x)  # Headwind
            if wind_z is not None:
                weather.aircraft_wind_z = float(wind_z)  # Crosswind

            # Visibility
            vis = self._safe_get("AMBIENT_VISIBILITY")
            if vis is not None:
                weather.ambient_visibility_m = float(vis)
                weather.ambient_visibility_sm = weather.ambient_visibility_m / 1609.34

            # Precipitation
            precip = self._safe_get("AMBIENT_PRECIP_STATE")
            if precip is not None:
                weather.ambient_precip_state = int(precip)

            # Clouds
            in_cloud = self._safe_get("AMBIENT_IN_CLOUD")
            if in_cloud is not None:
                weather.ambient_in_cloud = bool(in_cloud)

            # Time
            local_time = self._safe_get("LOCAL_TIME")
            if local_time is not None:
                # Convert seconds since midnight to time string
                hours = int(local_time // 3600)
                minutes = int((local_time % 3600) // 60)
                weather.local_time = f"{hours:02d}:{minutes:02d}"
                weather.is_day = 6 <= hours < 21

            # ==================== V2 ENHANCED WEATHER ====================

            # Density altitude - critical for takeoff/landing performance
            density_alt = self._safe_get("DENSITY_ALTITUDE")
            if density_alt is not None:
                weather.density_altitude_ft = float(density_alt)

            # Pressure altitude
            pressure_alt = self._safe_get("PRESSURE_ALTITUDE")
            if pressure_alt is not None:
                weather.pressure_altitude_ft = float(pressure_alt)

            # Icing data
            structural_ice = self._safe_get("STRUCTURAL_ICE_PCT")
            if structural_ice is not None:
                weather.structural_ice_pct = float(structural_ice)

            pitot_ice = self._safe_get("PITOT_ICE_PCT")
            if pitot_ice is not None:
                weather.pitot_ice_pct = float(pitot_ice)

            # Total air temperature (with ram rise)
            total_temp = self._safe_get("TOTAL_AIR_TEMPERATURE")
            if total_temp is not None:
                # SimConnect returns in Kelvin
                weather.total_air_temp_c = float(total_temp) - 273.15

            # Calculate flight conditions
            weather.flight_conditions = weather.get_flight_conditions()

            # Cache
            self._last_weather = weather
            self._last_update = time.time()

            return weather

        except Exception as e:
            logger.error(f"Error reading SimConnect weather: {e}")
            return self._create_default_weather()

    def _safe_get(self, variable: str):
        """Safely get a SimConnect variable"""
        try:
            return self._requests.get(variable)
        except Exception:
            return None

    def _create_default_weather(self) -> SimWeather:
        """Create default weather when SimConnect unavailable"""
        return SimWeather(
            ambient_temperature_c=15.0,
            ambient_wind_velocity_kts=5.0,
            ambient_wind_direction_deg=270.0,
            ambient_visibility_sm=10.0,
            flight_conditions="VFR"
        )

    def get_wind_description(self) -> str:
        """Get human-readable wind description"""
        weather = self.get_weather()
        if not weather:
            return "Vent inconnu"

        if weather.ambient_wind_velocity_kts < 3:
            return "Calme"

        dir_deg = int(weather.ambient_wind_direction_deg)
        speed_kts = int(weather.ambient_wind_velocity_kts)

        return f"{dir_deg:03d}/{speed_kts}kt"

    def get_crosswind_component(self, runway_heading: float) -> float:
        """
        Calculate crosswind component for a runway

        Args:
            runway_heading: Runway heading in degrees

        Returns:
            Crosswind component in knots (positive = from right)
        """
        import math

        weather = self.get_weather()
        if not weather:
            return 0.0

        wind_dir = weather.ambient_wind_direction_deg
        wind_speed = weather.ambient_wind_velocity_kts

        # Calculate angle between wind and runway
        angle_diff = wind_dir - runway_heading
        angle_rad = math.radians(angle_diff)

        # Crosswind component
        crosswind = wind_speed * math.sin(angle_rad)

        return crosswind

    def get_headwind_component(self, runway_heading: float) -> float:
        """
        Calculate headwind component for a runway

        Args:
            runway_heading: Runway heading in degrees

        Returns:
            Headwind component in knots (positive = headwind)
        """
        import math

        weather = self.get_weather()
        if not weather:
            return 0.0

        wind_dir = weather.ambient_wind_direction_deg
        wind_speed = weather.ambient_wind_velocity_kts

        # Calculate angle between wind and runway
        angle_diff = wind_dir - runway_heading
        angle_rad = math.radians(angle_diff)

        # Headwind component
        headwind = wind_speed * math.cos(angle_rad)

        return headwind

    def to_dict(self) -> Dict:
        """Get weather as dictionary"""
        weather = self.get_weather()
        if not weather:
            return {}

        return {
            'temperature_c': weather.ambient_temperature_c,
            'wind_direction': weather.ambient_wind_direction_deg,
            'wind_speed_kts': weather.ambient_wind_velocity_kts,
            'visibility_sm': weather.ambient_visibility_sm,
            'precipitation': weather.ambient_precip_state,
            'in_cloud': weather.ambient_in_cloud,
            'flight_conditions': weather.flight_conditions,
            'metar_string': weather.to_metar_string(),
            'wind_description': self.get_wind_description()
        }


# Global weather system instance
_weather_system: Optional[WeatherSimConnect] = None

def get_weather_system() -> WeatherSimConnect:
    """Get or create global weather system"""
    global _weather_system
    if _weather_system is None:
        _weather_system = WeatherSimConnect()
    return _weather_system
