"""
Flight Recorder for V2
Records flight trajectory for replay and export
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Utils.FlightRecorder")


@dataclass
class TrackPoint:
    """Single recorded point in the flight track"""
    timestamp: str
    latitude: float
    longitude: float
    altitude_ft: float
    altitude_agl_ft: float
    heading: float
    airspeed_kts: float
    ground_speed_kts: float
    vertical_speed_fpm: float
    bank_angle: float
    pitch_angle: float
    flight_phase: str = ""
    on_ground: bool = False


@dataclass
class FlightTrack:
    """Complete recorded flight track"""
    id: str
    departure_icao: str
    departure_name: str
    arrival_icao: str
    arrival_name: str
    aircraft: str
    aircraft_category: str

    # Time
    start_time: str = ""
    end_time: str = ""

    # Track data
    points: List[TrackPoint] = field(default_factory=list)

    # Statistics (calculated)
    total_distance_nm: float = 0.0
    max_altitude_ft: float = 0.0
    max_speed_kts: float = 0.0
    flight_time_hours: float = 0.0

    def add_point(self, point: TrackPoint) -> None:
        """Add a track point"""
        self.points.append(point)

        # Update statistics
        if point.altitude_ft > self.max_altitude_ft:
            self.max_altitude_ft = point.altitude_ft
        if point.ground_speed_kts > self.max_speed_kts:
            self.max_speed_kts = point.ground_speed_kts

    def calculate_statistics(self) -> None:
        """Calculate final statistics"""
        if not self.points:
            return

        # Distance
        from .distance import calculate_distance_nm
        total_dist = 0.0
        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            total_dist += calculate_distance_nm(p1.latitude, p1.longitude,
                                                p2.latitude, p2.longitude)
        self.total_distance_nm = total_dist

        # Flight time
        if self.start_time and self.end_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.flight_time_hours = (end - start).total_seconds() / 3600

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'departure_icao': self.departure_icao,
            'departure_name': self.departure_name,
            'arrival_icao': self.arrival_icao,
            'arrival_name': self.arrival_name,
            'aircraft': self.aircraft,
            'aircraft_category': self.aircraft_category,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'total_distance_nm': self.total_distance_nm,
            'max_altitude_ft': self.max_altitude_ft,
            'max_speed_kts': self.max_speed_kts,
            'flight_time_hours': self.flight_time_hours,
            'num_points': len(self.points)
        }

    def export_kml(self, filepath: Path) -> bool:
        """
        Export track to KML format (Google Earth)

        Args:
            filepath: Output file path

        Returns:
            True if successful
        """
        if not self.points:
            logger.warning("No track points to export")
            return False

        try:
            coordinates = []
            for point in self.points:
                # KML uses lon,lat,altitude format
                alt_meters = point.altitude_ft * 0.3048
                coordinates.append(f"{point.longitude},{point.latitude},{alt_meters:.0f}")

            coord_string = " ".join(coordinates)

            kml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <name>Flight {self.departure_icao} to {self.arrival_icao}</name>
    <description>Recorded flight track</description>
    <Style id="flightPath">
        <LineStyle>
            <color>ff0000ff</color>
            <width>3</width>
        </LineStyle>
    </Style>
    <Placemark>
        <name>Flight Path</name>
        <description>
            Aircraft: {self.aircraft}
            Distance: {self.total_distance_nm:.1f} nm
            Max altitude: {self.max_altitude_ft:.0f} ft
            Duration: {self.flight_time_hours:.2f} hours
        </description>
        <styleUrl>#flightPath</styleUrl>
        <LineString>
            <extrude>1</extrude>
            <tessellate>1</tessellate>
            <altitudeMode>absolute</altitudeMode>
            <coordinates>{coord_string}</coordinates>
        </LineString>
    </Placemark>
    <Placemark>
        <name>Departure: {self.departure_icao}</name>
        <Point>
            <coordinates>{self.points[0].longitude},{self.points[0].latitude},0</coordinates>
        </Point>
    </Placemark>
    <Placemark>
        <name>Arrival: {self.arrival_icao}</name>
        <Point>
            <coordinates>{self.points[-1].longitude},{self.points[-1].latitude},0</coordinates>
        </Point>
    </Placemark>
</Document>
</kml>'''

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(kml_content)

            logger.info(f"Track exported to KML: {filepath}")
            return True

        except Exception as e:
            logger.error(f"KML export failed: {e}")
            return False

    def export_gpx(self, filepath: Path) -> bool:
        """
        Export track to GPX format

        Args:
            filepath: Output file path

        Returns:
            True if successful
        """
        if not self.points:
            logger.warning("No track points to export")
            return False

        try:
            trackpoints = []
            for point in self.points:
                trkpt = f'''      <trkpt lat="{point.latitude}" lon="{point.longitude}">
        <ele>{point.altitude_ft * 0.3048:.1f}</ele>
        <time>{point.timestamp}</time>
        <extensions>
          <speed>{point.ground_speed_kts * 0.514444:.1f}</speed>
          <course>{point.heading:.1f}</course>
        </extensions>
      </trkpt>'''
                trackpoints.append(trkpt)

            gpx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="MSFS Mission Generator V2">
  <metadata>
    <name>Flight {self.departure_icao} to {self.arrival_icao}</name>
    <desc>Aircraft: {self.aircraft}</desc>
    <time>{self.start_time}</time>
  </metadata>
  <trk>
    <name>Flight Track</name>
    <trkseg>
{chr(10).join(trackpoints)}
    </trkseg>
  </trk>
</gpx>'''

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(gpx_content)

            logger.info(f"Track exported to GPX: {filepath}")
            return True

        except Exception as e:
            logger.error(f"GPX export failed: {e}")
            return False

    def export_json(self, filepath: Path) -> bool:
        """Export track to JSON format"""
        try:
            data = {
                **self.to_dict(),
                'points': [asdict(p) for p in self.points]
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Track exported to JSON: {filepath}")
            return True

        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            return False


class FlightRecorder:
    """Records flight data during flight"""

    def __init__(self, output_dir: Path = None):
        self._output_dir = output_dir or Path("flightplans")
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._current_track: Optional[FlightTrack] = None
        self._recording = False
        self._record_interval = 5.0  # seconds between recordings
        self._last_record_time = 0.0

        # Recorded tracks
        self._tracks: List[FlightTrack] = []

    @property
    def recording(self) -> bool:
        return self._recording

    @property
    def current_track(self) -> Optional[FlightTrack]:
        return self._current_track

    def set_record_interval(self, seconds: float) -> None:
        """Set recording interval"""
        self._record_interval = max(1.0, seconds)

    def start_recording(self, departure: Dict, arrival: Dict, aircraft: Dict) -> FlightTrack:
        """
        Start recording a new flight

        Args:
            departure: Departure airport info
            arrival: Arrival airport info
            aircraft: Aircraft info

        Returns:
            New FlightTrack
        """
        self._current_track = FlightTrack(
            id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            departure_icao=departure.get('icao', ''),
            departure_name=departure.get('name', ''),
            arrival_icao=arrival.get('icao', ''),
            arrival_name=arrival.get('name', ''),
            aircraft=aircraft.get('title', ''),
            aircraft_category=aircraft.get('category', ''),
            start_time=datetime.now().isoformat()
        )

        self._recording = True
        self._last_record_time = 0.0

        logger.info(f"Flight recording started: {self._current_track.departure_icao} -> {self._current_track.arrival_icao}")

        return self._current_track

    def record_point(self, latitude: float, longitude: float, altitude: float,
                     altitude_agl: float, heading: float, airspeed: float,
                     ground_speed: float, vertical_speed: float, bank: float,
                     pitch: float, flight_phase: str, on_ground: bool,
                     current_time: float = None) -> bool:
        """
        Record a track point

        Args:
            latitude, longitude: Position
            altitude: Altitude MSL (ft)
            altitude_agl: Altitude AGL (ft)
            heading: Heading (degrees)
            airspeed: Indicated airspeed (kts)
            ground_speed: Ground speed (kts)
            vertical_speed: Vertical speed (fpm)
            bank: Bank angle (degrees)
            pitch: Pitch angle (degrees)
            flight_phase: Current flight phase
            on_ground: True if on ground
            current_time: Current timestamp (optional)

        Returns:
            True if point was recorded
        """
        if not self._recording or not self._current_track:
            return False

        # Check interval
        import time
        now = current_time or time.time()
        if now - self._last_record_time < self._record_interval:
            return False

        point = TrackPoint(
            timestamp=datetime.now().isoformat(),
            latitude=latitude,
            longitude=longitude,
            altitude_ft=altitude,
            altitude_agl_ft=altitude_agl,
            heading=heading,
            airspeed_kts=airspeed,
            ground_speed_kts=ground_speed,
            vertical_speed_fpm=vertical_speed,
            bank_angle=bank,
            pitch_angle=pitch,
            flight_phase=flight_phase,
            on_ground=on_ground
        )

        self._current_track.add_point(point)
        self._last_record_time = now

        return True

    def stop_recording(self) -> Optional[FlightTrack]:
        """
        Stop recording and finalize track

        Returns:
            Completed FlightTrack
        """
        if not self._recording or not self._current_track:
            return None

        self._recording = False
        self._current_track.end_time = datetime.now().isoformat()
        self._current_track.calculate_statistics()

        self._tracks.append(self._current_track)

        logger.info(f"Flight recording stopped: {len(self._current_track.points)} points, "
                   f"{self._current_track.total_distance_nm:.1f} nm")

        track = self._current_track
        self._current_track = None

        return track

    def save_current_track(self, format: str = 'kml') -> Optional[Path]:
        """
        Save current or last track to file

        Args:
            format: Export format ('kml', 'gpx', 'json')

        Returns:
            Path to saved file
        """
        track = self._current_track or (self._tracks[-1] if self._tracks else None)

        if not track:
            logger.warning("No track to save")
            return None

        filename = f"track_{track.id}.{format}"
        filepath = self._output_dir / filename

        if format == 'kml':
            success = track.export_kml(filepath)
        elif format == 'gpx':
            success = track.export_gpx(filepath)
        elif format == 'json':
            success = track.export_json(filepath)
        else:
            logger.error(f"Unknown export format: {format}")
            return None

        return filepath if success else None

    def get_all_tracks(self) -> List[Dict]:
        """Get summary of all recorded tracks"""
        return [track.to_dict() for track in self._tracks]

    def get_stats(self) -> Dict:
        """Get recorder statistics"""
        total_points = sum(len(t.points) for t in self._tracks)
        total_distance = sum(t.total_distance_nm for t in self._tracks)

        return {
            'total_tracks': len(self._tracks),
            'total_points': total_points,
            'total_distance_nm': total_distance,
            'recording': self._recording,
            'current_track_points': len(self._current_track.points) if self._current_track else 0
        }


# Global flight recorder instance
_flight_recorder: Optional[FlightRecorder] = None

def get_flight_recorder() -> FlightRecorder:
    """Get or create global flight recorder"""
    global _flight_recorder
    if _flight_recorder is None:
        _flight_recorder = FlightRecorder()
    return _flight_recorder
