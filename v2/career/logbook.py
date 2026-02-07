"""
Flight Logbook System for V2
Automatic flight logging with CSV export capability
"""

import csv
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("MissionGenerator.Logbook")


@dataclass
class LogEntry:
    """Single logbook entry for a flight"""

    # Flight identification
    id: str = ""
    date: str = ""
    timestamp: str = ""

    # Route
    departure_icao: str = ""
    departure_name: str = ""
    arrival_icao: str = ""
    arrival_name: str = ""
    distance_nm: float = 0.0

    # Time
    block_off: str = ""      # Engine start time
    takeoff: str = ""        # Actual takeoff time
    landing: str = ""        # Actual landing time
    block_on: str = ""       # Engine shutdown time
    flight_time_hours: float = 0.0
    block_time_hours: float = 0.0

    # Aircraft
    aircraft_title: str = ""
    aircraft_category: str = ""
    aircraft_registration: str = ""

    # Performance
    landing_vs_fpm: float = 0.0
    landing_quality: str = ""
    constraints_violated: int = 0
    mission_score: float = 0.0

    # Weather
    departure_metar: str = ""
    arrival_metar: str = ""
    wind_departure: str = ""
    wind_arrival: str = ""
    flight_conditions: str = "VFR"  # VFR, IFR, MVFR

    # Financial
    earnings: float = 0.0
    fuel_cost: float = 0.0
    net_income: float = 0.0

    # Company
    company_id: str = ""
    company_name: str = ""

    # Notes
    notes: str = ""
    waypoints: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not self.date:
            self.date = datetime.now().strftime("%Y-%m-%d")
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'LogEntry':
        """Create from dictionary"""
        # Handle waypoints field
        if 'waypoints' in data and isinstance(data['waypoints'], str):
            data['waypoints'] = data['waypoints'].split(',') if data['waypoints'] else []
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def get_summary(self) -> str:
        """Get short summary of the flight"""
        return (f"{self.date} | {self.departure_icao} -> {self.arrival_icao} | "
                f"{self.flight_time_hours:.1f}h | {self.aircraft_category} | "
                f"{self.landing_quality} | {self.net_income:+.2f} EUR")


class LogBook:
    """Flight logbook manager with CSV export"""

    def __init__(self, save_file: Optional[Path] = None):
        self._entries: List[LogEntry] = []
        self._save_file = save_file

        # Statistics
        self._stats = {
            'total_flights': 0,
            'total_hours': 0.0,
            'total_distance_nm': 0.0,
            'total_earnings': 0.0,
            'perfect_landings': 0
        }

    @property
    def entries(self) -> List[LogEntry]:
        return self._entries.copy()

    @property
    def total_flights(self) -> int:
        return len(self._entries)

    def add_entry(self, entry: LogEntry) -> None:
        """Add a new logbook entry"""
        self._entries.append(entry)
        self._update_stats()
        logger.info(f"Logbook: Added flight {entry.departure_icao} -> {entry.arrival_icao}")

    def get_entry(self, entry_id: str) -> Optional[LogEntry]:
        """Get entry by ID"""
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None

    def get_recent(self, count: int = 10) -> List[LogEntry]:
        """Get most recent entries"""
        return self._entries[-count:][::-1]

    def get_by_date_range(self, start_date: str, end_date: str) -> List[LogEntry]:
        """Get entries within date range"""
        return [
            e for e in self._entries
            if start_date <= e.date <= end_date
        ]

    def get_by_aircraft(self, category: str) -> List[LogEntry]:
        """Get entries for specific aircraft category"""
        return [e for e in self._entries if e.aircraft_category == category]

    def get_by_airport(self, icao: str) -> List[LogEntry]:
        """Get entries involving specific airport"""
        icao = icao.upper()
        return [
            e for e in self._entries
            if e.departure_icao == icao or e.arrival_icao == icao
        ]

    def get_hours_by_category(self) -> Dict[str, float]:
        """Get flight hours grouped by aircraft category"""
        hours = {}
        for entry in self._entries:
            cat = entry.aircraft_category
            hours[cat] = hours.get(cat, 0) + entry.flight_time_hours
        return hours

    def get_stats(self) -> Dict:
        """Get logbook statistics"""
        self._update_stats()
        return self._stats.copy()

    def _update_stats(self) -> None:
        """Update statistics from entries"""
        self._stats['total_flights'] = len(self._entries)
        self._stats['total_hours'] = sum(e.flight_time_hours for e in self._entries)
        self._stats['total_distance_nm'] = sum(e.distance_nm for e in self._entries)
        self._stats['total_earnings'] = sum(e.net_income for e in self._entries)
        self._stats['perfect_landings'] = sum(
            1 for e in self._entries
            if abs(e.landing_vs_fpm) < 100
        )

    def export_csv(self, filepath: Path) -> bool:
        """Export logbook to CSV file"""
        if not self._entries:
            logger.warning("Logbook is empty, nothing to export")
            return False

        try:
            fieldnames = [
                'date', 'departure_icao', 'departure_name',
                'arrival_icao', 'arrival_name', 'distance_nm',
                'takeoff', 'landing', 'flight_time_hours',
                'aircraft_title', 'aircraft_category',
                'landing_vs_fpm', 'landing_quality',
                'earnings', 'fuel_cost', 'net_income',
                'company_name', 'notes'
            ]

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()

                for entry in self._entries:
                    writer.writerow(entry.to_dict())

            logger.info(f"Logbook exported to {filepath} ({len(self._entries)} entries)")
            return True

        except Exception as e:
            logger.error(f"Failed to export logbook: {e}")
            return False

    def import_csv(self, filepath: Path) -> int:
        """Import entries from CSV file"""
        if not filepath.exists():
            logger.error(f"CSV file not found: {filepath}")
            return 0

        try:
            imported = 0
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    entry = LogEntry.from_dict(row)
                    self._entries.append(entry)
                    imported += 1

            self._update_stats()
            logger.info(f"Imported {imported} entries from {filepath}")
            return imported

        except Exception as e:
            logger.error(f"Failed to import logbook: {e}")
            return 0

    def to_save_dict(self) -> List[Dict]:
        """Convert to save format"""
        return [e.to_dict() for e in self._entries]

    def load_from_save(self, save_data: List[Dict]) -> None:
        """Load from save data"""
        self._entries.clear()

        for entry_data in save_data:
            try:
                entry = LogEntry.from_dict(entry_data)
                self._entries.append(entry)
            except Exception as e:
                logger.warning(f"Failed to load logbook entry: {e}")

        self._update_stats()
        logger.info(f"Loaded {len(self._entries)} logbook entries")

    def create_entry_from_mission(
        self,
        departure: Dict,
        arrival: Dict,
        aircraft_info: Dict,
        flight_data: Dict,
        company: Optional[Dict] = None
    ) -> LogEntry:
        """Create a logbook entry from mission completion data"""

        entry = LogEntry(
            departure_icao=departure.get('icao', ''),
            departure_name=departure.get('name', ''),
            arrival_icao=arrival.get('icao', ''),
            arrival_name=arrival.get('name', ''),
            distance_nm=flight_data.get('distance_nm', 0),

            takeoff=flight_data.get('takeoff_time', ''),
            landing=flight_data.get('landing_time', ''),
            flight_time_hours=flight_data.get('flight_time_hours', 0),

            aircraft_title=aircraft_info.get('title', ''),
            aircraft_category=aircraft_info.get('category', ''),

            landing_vs_fpm=flight_data.get('landing_vs', 0),
            landing_quality=self._rate_landing(flight_data.get('landing_vs', 0)),
            constraints_violated=flight_data.get('constraint_violations', 0),
            mission_score=flight_data.get('mission_score', 0),

            departure_metar=departure.get('weather', {}).get('metar', ''),
            arrival_metar=arrival.get('weather', {}).get('metar', ''),
            wind_departure=departure.get('weather', {}).get('wind_description', ''),
            wind_arrival=arrival.get('weather', {}).get('wind_description', ''),

            earnings=flight_data.get('earnings', 0),
            fuel_cost=flight_data.get('fuel_cost', 0),
            net_income=flight_data.get('net_income', 0),

            company_id=company.get('id', '') if company else '',
            company_name=company.get('name', '') if company else ''
        )

        self.add_entry(entry)
        return entry

    def _rate_landing(self, vs_fpm: float) -> str:
        """Rate landing quality based on vertical speed"""
        vs = abs(vs_fpm)
        if vs < 60:
            return "Butter"
        elif vs < 100:
            return "Excellent"
        elif vs < 150:
            return "Good"
        elif vs < 200:
            return "Normal"
        elif vs < 300:
            return "Firm"
        elif vs < 500:
            return "Hard"
        else:
            return "Very Hard"

    def add_entry_from_mission(self, mission_data: Dict) -> LogEntry:
        """
        Add a logbook entry from simplified mission data

        Args:
            mission_data: Dict with keys: departure, arrival, aircraft, flight_time, distance, landing_vs

        Returns:
            Created LogEntry
        """
        departure = mission_data.get('departure', {})
        arrival = mission_data.get('arrival', {})
        aircraft = mission_data.get('aircraft', {})

        flight_data = {
            'distance_nm': mission_data.get('distance', 0),
            'flight_time_hours': mission_data.get('flight_time', 0),
            'landing_vs': mission_data.get('landing_vs', 0),
            'takeoff_time': '',
            'landing_time': ''
        }

        return self.create_entry_from_mission(
            departure=departure,
            arrival=arrival,
            aircraft_info=aircraft,
            flight_data=flight_data
        )


# Global logbook instance
_logbook: Optional[LogBook] = None

def get_logbook() -> LogBook:
    """Get or create global logbook"""
    global _logbook
    if _logbook is None:
        _logbook = LogBook()
    return _logbook
