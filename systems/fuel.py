"""
Fuel Management System for V2
Realistic fuel consumption, costs, and deduction from salary
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger("MissionGenerator.Fuel")

# Fuel prices (EUR per gallon)
FUEL_PRICES = {
    'avgas_100ll': 6.50,      # Aviation gasoline
    'jet_a': 4.50,            # Jet fuel
    'diesel': 5.00            # Jet-A alternative
}

# Fuel consumption rates by aircraft category (gallons per hour)
FUEL_CONSUMPTION_GPH = {
    'light_piston': 10,        # Cessna 172: ~10 GPH
    'twin_piston': 25,         # Baron: ~25 GPH
    'single_turboprop': 40,    # TBM: ~40 GPH
    'turboprop': 80,           # King Air: ~80 GPH
    'light_jet': 150,          # Citation: ~150 GPH
    'jet': 800,                # A320: ~800 GPH
    'heavy_jet': 2500,         # 747: ~2500 GPH
    'helicopter': 30           # R44: ~15 GPH, larger ~50 GPH
}

# Fuel type by aircraft category
FUEL_TYPE = {
    'light_piston': 'avgas_100ll',
    'twin_piston': 'avgas_100ll',
    'single_turboprop': 'jet_a',
    'turboprop': 'jet_a',
    'light_jet': 'jet_a',
    'jet': 'jet_a',
    'heavy_jet': 'jet_a',
    'helicopter': 'avgas_100ll'
}


@dataclass
class FuelData:
    """Current fuel state"""
    fuel_quantity_gallons: float = 0.0
    fuel_capacity_gallons: float = 0.0
    fuel_flow_gph: float = 0.0
    fuel_consumed_gallons: float = 0.0
    fuel_cost_total: float = 0.0
    fuel_type: str = 'avgas_100ll'
    # V2 Enhanced tracking
    fuel_flow_integrated: float = 0.0   # Integrated consumption from fuel flow
    last_update_time: float = 0.0       # Timestamp of last update
    use_flow_integration: bool = False  # True if using real-time flow data


class FuelManager:
    """Manages fuel consumption and costs"""

    def __init__(self, price_per_gallon: Optional[float] = None):
        self._current_fuel = FuelData()
        self._mission_start_fuel = 0.0
        self._custom_price = price_per_gallon
        self._deduct_from_salary = True

        # Stats
        self._total_fuel_consumed = 0.0
        self._total_fuel_cost = 0.0

    @property
    def current_fuel(self) -> FuelData:
        return self._current_fuel

    @property
    def fuel_consumed(self) -> float:
        """Fuel consumed during current mission"""
        return self._current_fuel.fuel_consumed_gallons

    @property
    def fuel_cost(self) -> float:
        """Cost of fuel consumed during current mission"""
        return self._current_fuel.fuel_cost_total

    def set_deduct_from_salary(self, deduct: bool) -> None:
        """Set whether to deduct fuel cost from salary"""
        self._deduct_from_salary = deduct

    def get_fuel_price(self, fuel_type: str) -> float:
        """Get price per gallon for fuel type"""
        if self._custom_price:
            return self._custom_price
        return FUEL_PRICES.get(fuel_type, FUEL_PRICES['avgas_100ll'])

    def start_mission(self, aircraft_category: str, initial_fuel_gallons: float = 0.0) -> None:
        """Start tracking fuel for a new mission"""
        import time
        fuel_type = FUEL_TYPE.get(aircraft_category, 'avgas_100ll')

        self._current_fuel = FuelData(
            fuel_quantity_gallons=initial_fuel_gallons,
            fuel_type=fuel_type,
            fuel_consumed_gallons=0.0,
            fuel_cost_total=0.0,
            # V2: Reset flow integration
            fuel_flow_integrated=0.0,
            last_update_time=time.time(),
            use_flow_integration=False
        )
        self._mission_start_fuel = initial_fuel_gallons

        logger.info(f"Fuel tracking started: {initial_fuel_gallons:.1f} gal ({fuel_type})")

    def update_fuel(self, current_fuel_gallons: float, fuel_flow_gph: float = 0.0) -> FuelData:
        """
        Update fuel state from SimConnect data

        V2 ENHANCED: Uses real fuel flow integration when available for
        more accurate consumption tracking that varies with throttle,
        altitude, and conditions.

        Args:
            current_fuel_gallons: Current total fuel quantity
            fuel_flow_gph: Current REAL fuel flow rate from SimConnect (ENG_FUEL_FLOW_GPH)

        Returns:
            Updated FuelData
        """
        import time
        current_time = time.time()

        # V2: Real-time fuel flow integration
        # If we have valid fuel flow data, integrate it for more accurate tracking
        if fuel_flow_gph > 0 and self._current_fuel.last_update_time > 0:
            dt_seconds = current_time - self._current_fuel.last_update_time
            if dt_seconds > 0 and dt_seconds < 10:  # Sanity check (max 10s gap)
                # Convert GPH to gallons for this time interval
                fuel_used = (fuel_flow_gph / 3600.0) * dt_seconds
                self._current_fuel.fuel_flow_integrated += fuel_used
                self._current_fuel.use_flow_integration = True

        self._current_fuel.last_update_time = current_time

        # Calculate consumption - prefer flow integration if available
        if self._mission_start_fuel > 0:
            if self._current_fuel.use_flow_integration and self._current_fuel.fuel_flow_integrated > 0:
                # V2: Use integrated fuel flow (more accurate)
                consumed = self._current_fuel.fuel_flow_integrated
            else:
                # Fallback: Use tank quantity difference
                consumed = self._mission_start_fuel - current_fuel_gallons

            if consumed > 0:
                self._current_fuel.fuel_consumed_gallons = consumed

                # Calculate cost
                price = self.get_fuel_price(self._current_fuel.fuel_type)
                self._current_fuel.fuel_cost_total = consumed * price

        self._current_fuel.fuel_quantity_gallons = current_fuel_gallons
        self._current_fuel.fuel_flow_gph = fuel_flow_gph

        return self._current_fuel

    def end_mission(self) -> Dict:
        """
        End mission and return fuel summary

        Returns:
            Dictionary with fuel consumption summary
        """
        consumed = self._current_fuel.fuel_consumed_gallons
        cost = self._current_fuel.fuel_cost_total

        # Update totals
        self._total_fuel_consumed += consumed
        self._total_fuel_cost += cost

        # V2: Track consumption method
        method = "flow_integration" if self._current_fuel.use_flow_integration else "tank_quantity"

        summary = {
            'fuel_consumed_gallons': consumed,
            'fuel_cost': cost,
            'fuel_type': self._current_fuel.fuel_type,
            'deduct_from_salary': self._deduct_from_salary,
            'salary_deduction': cost if self._deduct_from_salary else 0,
            # V2 Enhanced
            'tracking_method': method,
            'flow_integrated_gallons': self._current_fuel.fuel_flow_integrated
        }

        logger.info(f"Mission fuel: {consumed:.1f} gal = {cost:.2f} EUR (method: {method})")

        return summary

    def estimate_fuel_needed(self, aircraft_category: str, flight_time_hours: float,
                            reserve_percent: float = 0.1) -> Dict:
        """
        Estimate fuel needed for a flight

        Args:
            aircraft_category: Aircraft type
            flight_time_hours: Estimated flight time
            reserve_percent: Reserve fuel percentage (default 10%)

        Returns:
            Fuel estimation dictionary
        """
        consumption_gph = FUEL_CONSUMPTION_GPH.get(aircraft_category, 10)
        fuel_type = FUEL_TYPE.get(aircraft_category, 'avgas_100ll')

        # Calculate fuel needed
        trip_fuel = consumption_gph * flight_time_hours
        reserve_fuel = trip_fuel * reserve_percent
        total_fuel = trip_fuel + reserve_fuel

        # Calculate cost
        price = self.get_fuel_price(fuel_type)
        estimated_cost = total_fuel * price

        return {
            'trip_fuel_gallons': trip_fuel,
            'reserve_fuel_gallons': reserve_fuel,
            'total_fuel_gallons': total_fuel,
            'consumption_gph': consumption_gph,
            'fuel_type': fuel_type,
            'price_per_gallon': price,
            'estimated_cost': estimated_cost
        }

    def calculate_cost(self, distance_nm: float, flight_time_hours: float,
                       aircraft_category: str) -> float:
        """
        Calculate estimated fuel cost for a flight

        Args:
            distance_nm: Flight distance in nautical miles
            flight_time_hours: Flight time in hours
            aircraft_category: Aircraft category

        Returns:
            Estimated fuel cost in EUR
        """
        estimate = self.estimate_fuel_needed(aircraft_category, flight_time_hours)
        return estimate['estimated_cost']

    def get_stats(self) -> Dict:
        """Get total fuel statistics"""
        return {
            'total_fuel_consumed': self._total_fuel_consumed,
            'total_fuel_cost': self._total_fuel_cost,
            'average_cost_per_gallon': (
                self._total_fuel_cost / self._total_fuel_consumed
                if self._total_fuel_consumed > 0 else 0
            )
        }


# Global fuel manager instance
_fuel_manager: Optional[FuelManager] = None

def get_fuel_manager() -> FuelManager:
    """Get or create global fuel manager"""
    global _fuel_manager
    if _fuel_manager is None:
        _fuel_manager = FuelManager()
    return _fuel_manager
