"""
Aircraft Maintenance System for V2
Tracks aircraft wear, maintenance status, and repair costs
"""

import logging
import random
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Maintenance")

# Wear rates per hour by category (percentage)
WEAR_RATES = {
    'light_piston': 0.05,      # 0.05% per hour
    'twin_piston': 0.04,
    'single_turboprop': 0.03,
    'turboprop': 0.025,
    'light_jet': 0.02,
    'jet': 0.015,
    'heavy_jet': 0.01,
    'helicopter': 0.06         # Higher due to rotor wear
}

# Repair costs per percentage point by category (EUR)
REPAIR_COSTS = {
    'light_piston': 50,
    'twin_piston': 100,
    'single_turboprop': 200,
    'turboprop': 350,
    'light_jet': 500,
    'jet': 800,
    'heavy_jet': 1500,
    'helicopter': 150
}

# Wear factors
WEAR_FACTORS = {
    'hard_landing': 1.5,       # Hard landing increases wear
    'rough_weather': 1.3,      # Turbulence
    'high_altitude': 0.9,      # Actually lower wear at altitude
    'hot_day': 1.2,            # High OAT
    'cold_day': 1.1            # Cold start wear
}


@dataclass
class MaintenanceLog:
    """Single maintenance record"""
    timestamp: str
    type: str                  # inspection, repair, overhaul
    description: str
    cost: float
    wear_before: float
    wear_after: float


@dataclass
class AircraftStatus:
    """Aircraft maintenance status"""
    aircraft_id: str           # Registration or identifier
    aircraft_title: str
    category: str

    # Wear tracking (0-100, 100 = needs immediate maintenance)
    wear_percent: float = 0.0
    total_hours: float = 0.0
    hours_since_maintenance: float = 0.0

    # Component status
    engine_hours: float = 0.0
    landing_gear_cycles: int = 0
    tires_wear: float = 0.0
    brakes_wear: float = 0.0

    # Maintenance history
    last_inspection: Optional[str] = None
    next_inspection_hours: float = 100.0
    maintenance_log: List[MaintenanceLog] = field(default_factory=list)

    # Financial
    total_maintenance_cost: float = 0.0

    # V2 Enhanced tracking
    engine_stress_accumulated: float = 0.0  # Accumulated stress from RPM overruns
    overtemp_events: int = 0                # Count of oil/ITT overtemp events
    max_g_recorded: float = 1.0             # Maximum G-force experienced

    def add_flight(self, flight_hours: float, landing_vs: float = 0,
                   factors: List[str] = None,
                   # V2 Enhanced parameters
                   avg_engine_rpm_pct: float = None,
                   max_engine_rpm_pct: float = None,
                   overtemp_occurred: bool = False,
                   max_g_force: float = None,
                   touchdown_velocity_fps: float = None) -> float:
        """
        Add flight wear to aircraft

        V2 ENHANCED: Uses real engine stress data from SimConnect for
        more accurate wear calculation based on actual operating conditions.

        Args:
            flight_hours: Duration of flight
            landing_vs: Landing vertical speed (fpm)
            factors: Additional wear factors
            avg_engine_rpm_pct: Average engine RPM % during flight (GENERAL_ENG_PCT_MAX_RPM)
            max_engine_rpm_pct: Maximum RPM % recorded during flight
            overtemp_occurred: True if oil/ITT overtemp was detected
            max_g_force: Maximum G-force during flight
            touchdown_velocity_fps: Touchdown velocity from SimConnect (more accurate than VS)

        Returns:
            Wear added (percentage)
        """
        # Base wear rate
        base_rate = WEAR_RATES.get(self.category, 0.03)
        wear = base_rate * flight_hours

        # Apply factors
        if factors:
            for factor in factors:
                wear *= WEAR_FACTORS.get(factor, 1.0)

        # ==================== V2 ENGINE STRESS WEAR ====================

        # V2: Dynamic engine wear based on actual RPM stress
        if max_engine_rpm_pct is not None and max_engine_rpm_pct > 100:
            # Engine overrev - significant additional wear
            overrev_time_estimate = flight_hours * 0.1  # Assume 10% of time at max
            overrev_wear = (max_engine_rpm_pct - 100) * 0.02 * overrev_time_estimate
            wear += overrev_wear
            self.engine_stress_accumulated += overrev_wear
            logger.debug(f"{self.aircraft_id}: Engine overrev (+{overrev_wear:.3f}% wear)")

        if avg_engine_rpm_pct is not None:
            # Adjust base wear by average power setting
            if avg_engine_rpm_pct > 90:
                # High power operation - 1.5x wear
                wear *= 1.5
            elif avg_engine_rpm_pct < 50:
                # Low power cruise - 0.8x wear (easier on engine)
                wear *= 0.8

        # V2: Overtemp events cause accelerated wear
        if overtemp_occurred:
            wear += 0.3  # Significant wear from overtemp
            self.overtemp_events += 1
            logger.warning(f"{self.aircraft_id}: Overtemp event recorded (+0.3% wear)")

        # V2: G-force structural wear
        if max_g_force is not None:
            self.max_g_recorded = max(self.max_g_recorded, max_g_force)
            if max_g_force > 3.0:
                # Excessive G = structural stress
                g_wear = (max_g_force - 3.0) * 0.2
                wear += g_wear
                logger.debug(f"{self.aircraft_id}: High G wear (+{g_wear:.3f}%)")

        # ==================== LANDING WEAR ====================

        # V2: Use touchdown velocity if available (more accurate)
        landing_wear = 0.0
        if touchdown_velocity_fps is not None and touchdown_velocity_fps > 0:
            # Touchdown velocity in ft/s: < 2 = butter, 2-4 = good, 4-6 = firm, > 6 = hard
            if touchdown_velocity_fps > 8:
                landing_wear = 0.8   # Very hard landing
            elif touchdown_velocity_fps > 6:
                landing_wear = 0.5   # Hard landing
            elif touchdown_velocity_fps > 4:
                landing_wear = 0.2   # Firm landing
            elif touchdown_velocity_fps > 2:
                landing_wear = 0.1   # Good landing
            # Butter landing (< 2 ft/s) = minimal extra wear
        elif landing_vs != 0:
            # Fallback to VS-based calculation
            vs_abs = abs(landing_vs)
            if vs_abs > 500:
                landing_wear = 0.5  # Hard landing
            elif vs_abs > 300:
                landing_wear = 0.2
            elif vs_abs > 200:
                landing_wear = 0.1

        wear += landing_wear

        # Update status
        self.wear_percent = min(100, self.wear_percent + wear)
        self.total_hours += flight_hours
        self.hours_since_maintenance += flight_hours
        self.engine_hours += flight_hours
        self.landing_gear_cycles += 1

        # Tire and brake wear from landing
        # V2: More tire wear for hard landings
        tire_wear_base = 0.3 if touchdown_velocity_fps and touchdown_velocity_fps < 3 else 0.5
        self.tires_wear = min(100, self.tires_wear + tire_wear_base + (landing_wear * 0.5))
        self.brakes_wear = min(100, self.brakes_wear + 0.3)

        logger.debug(f"{self.aircraft_id}: +{wear:.2f}% wear, total {self.wear_percent:.1f}%")

        return wear

    def needs_maintenance(self) -> bool:
        """Check if aircraft needs maintenance"""
        return (
            self.wear_percent >= 80 or
            self.hours_since_maintenance >= self.next_inspection_hours or
            self.tires_wear >= 90 or
            self.brakes_wear >= 90
        )

    def get_maintenance_status(self) -> str:
        """Get human-readable maintenance status"""
        if self.wear_percent >= 90:
            return "CRITICAL - Maintenance Required"
        elif self.wear_percent >= 80:
            return "WARNING - Schedule Maintenance"
        elif self.wear_percent >= 60:
            return "Fair - Monitor Closely"
        elif self.wear_percent >= 40:
            return "Good"
        else:
            return "Excellent"

    def get_repair_cost(self) -> float:
        """Calculate cost to repair to 0% wear"""
        cost_per_percent = REPAIR_COSTS.get(self.category, 100)
        return self.wear_percent * cost_per_percent

    def perform_maintenance(self, maintenance_type: str = "inspection") -> MaintenanceLog:
        """
        Perform maintenance on aircraft

        Args:
            maintenance_type: inspection, repair, or overhaul

        Returns:
            Maintenance log entry
        """
        wear_before = self.wear_percent
        cost = 0.0

        if maintenance_type == "inspection":
            # Inspection only, no repair
            cost = 100 + (50 * (REPAIR_COSTS.get(self.category, 100) / 100))
            self.hours_since_maintenance = 0
            self.next_inspection_hours = 100

        elif maintenance_type == "repair":
            # Repair to 20% wear
            wear_to_fix = max(0, self.wear_percent - 20)
            cost = wear_to_fix * REPAIR_COSTS.get(self.category, 100)
            self.wear_percent = 20
            self.hours_since_maintenance = 0
            self.tires_wear = 10
            self.brakes_wear = 10

        elif maintenance_type == "overhaul":
            # Full overhaul to 0% wear
            cost = self.get_repair_cost() * 1.5  # Premium for full overhaul
            self.wear_percent = 0
            self.hours_since_maintenance = 0
            self.engine_hours = 0  # Reset for overhaul
            self.tires_wear = 0
            self.brakes_wear = 0
            self.next_inspection_hours = 150  # Longer until next inspection

        # Create log entry
        log_entry = MaintenanceLog(
            timestamp=datetime.now().isoformat(),
            type=maintenance_type,
            description=f"{maintenance_type.capitalize()} - {self.aircraft_title}",
            cost=cost,
            wear_before=wear_before,
            wear_after=self.wear_percent
        )

        self.maintenance_log.append(log_entry)
        self.last_inspection = datetime.now().isoformat()
        self.total_maintenance_cost += cost

        logger.info(f"{self.aircraft_id}: {maintenance_type} - {wear_before:.1f}% -> {self.wear_percent:.1f}% ({cost:.2f} EUR)")

        return log_entry

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'aircraft_id': self.aircraft_id,
            'aircraft_title': self.aircraft_title,
            'category': self.category,
            'wear_percent': self.wear_percent,
            'total_hours': self.total_hours,
            'hours_since_maintenance': self.hours_since_maintenance,
            'engine_hours': self.engine_hours,
            'landing_gear_cycles': self.landing_gear_cycles,
            'tires_wear': self.tires_wear,
            'brakes_wear': self.brakes_wear,
            'last_inspection': self.last_inspection,
            'next_inspection_hours': self.next_inspection_hours,
            'total_maintenance_cost': self.total_maintenance_cost,
            # V2 Enhanced
            'engine_stress_accumulated': self.engine_stress_accumulated,
            'overtemp_events': self.overtemp_events,
            'max_g_recorded': self.max_g_recorded
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'AircraftStatus':
        """Create from dictionary"""
        status = cls(
            aircraft_id=data.get('aircraft_id', 'UNKNOWN'),
            aircraft_title=data.get('aircraft_title', 'Unknown Aircraft'),
            category=data.get('category', 'light_piston')
        )
        status.wear_percent = data.get('wear_percent', 0.0)
        status.total_hours = data.get('total_hours', 0.0)
        status.hours_since_maintenance = data.get('hours_since_maintenance', 0.0)
        status.engine_hours = data.get('engine_hours', 0.0)
        status.landing_gear_cycles = data.get('landing_gear_cycles', 0)
        status.tires_wear = data.get('tires_wear', 0.0)
        status.brakes_wear = data.get('brakes_wear', 0.0)
        status.last_inspection = data.get('last_inspection')
        status.next_inspection_hours = data.get('next_inspection_hours', 100.0)
        status.total_maintenance_cost = data.get('total_maintenance_cost', 0.0)
        # V2 Enhanced
        status.engine_stress_accumulated = data.get('engine_stress_accumulated', 0.0)
        status.overtemp_events = data.get('overtemp_events', 0)
        status.max_g_recorded = data.get('max_g_recorded', 1.0)
        return status


class MaintenanceManager:
    """Manages maintenance for all aircraft"""

    def __init__(self):
        self._aircraft: Dict[str, AircraftStatus] = {}

    def get_or_create_aircraft(self, aircraft_id: str, title: str = "",
                               category: str = "light_piston") -> AircraftStatus:
        """Get existing aircraft status or create new one"""
        if aircraft_id not in self._aircraft:
            self._aircraft[aircraft_id] = AircraftStatus(
                aircraft_id=aircraft_id,
                aircraft_title=title,
                category=category
            )
            logger.info(f"New aircraft tracked: {aircraft_id} ({category})")

        return self._aircraft[aircraft_id]

    def get_aircraft(self, aircraft_id: str) -> Optional[AircraftStatus]:
        """Get aircraft status by ID"""
        return self._aircraft.get(aircraft_id)

    def record_flight(self, aircraft_id: str, flight_hours: float,
                      landing_vs: float = 0, title: str = "",
                      category: str = "light_piston") -> AircraftStatus:
        """Record a flight for maintenance tracking"""
        aircraft = self.get_or_create_aircraft(aircraft_id, title, category)
        aircraft.add_flight(flight_hours, landing_vs)
        return aircraft

    def get_all_aircraft(self) -> List[AircraftStatus]:
        """Get all tracked aircraft"""
        return list(self._aircraft.values())

    def get_aircraft_needing_maintenance(self) -> List[AircraftStatus]:
        """Get aircraft that need maintenance"""
        return [a for a in self._aircraft.values() if a.needs_maintenance()]

    def to_save_dict(self) -> Dict:
        """Convert to save format"""
        return {
            aid: aircraft.to_dict()
            for aid, aircraft in self._aircraft.items()
        }

    def load_from_save(self, save_data: Dict) -> None:
        """Load from save data"""
        self._aircraft.clear()

        for aid, data in save_data.items():
            self._aircraft[aid] = AircraftStatus.from_dict(data)

        logger.info(f"Loaded {len(self._aircraft)} aircraft maintenance records")


# Global maintenance manager instance
_maintenance_manager: Optional[MaintenanceManager] = None

def get_maintenance() -> MaintenanceManager:
    """Get or create global maintenance manager"""
    global _maintenance_manager
    if _maintenance_manager is None:
        _maintenance_manager = MaintenanceManager()
    return _maintenance_manager
