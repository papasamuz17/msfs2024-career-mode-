"""
ATC Radio Simulation for V2 Copilot
Simulates realistic ATC communications
"""

import logging
import random
from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Copilot.ATC")


class ATCFacility(Enum):
    """Types of ATC facilities"""
    DELIVERY = "delivery"       # Clearance delivery
    GROUND = "ground"           # Ground control
    TOWER = "tower"             # Tower
    DEPARTURE = "departure"     # Departure control
    CENTER = "center"           # En-route center
    APPROACH = "approach"       # Approach control
    ATIS = "atis"               # ATIS


@dataclass
class ATCMessage:
    """ATC message"""
    facility: ATCFacility
    callsign: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    is_pilot: bool = False      # True if from pilot, False if from ATC
    frequency: str = ""


class ATCSimulator:
    """Simulates ATC communications"""

    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._callsign = "Fox Alpha Bravo Charlie Delta"
        self._squawk = "1200"
        self._messages: List[ATCMessage] = []
        self._callbacks: List[Callable[[ATCMessage], None]] = []

        # Current state
        self._current_facility = ATCFacility.GROUND
        self._clearance_received = False
        self._taxi_clearance = ""
        self._departure_clearance = ""
        self._assigned_altitude = 0
        self._assigned_heading = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def set_callsign(self, callsign: str) -> None:
        """Set aircraft callsign"""
        self._callsign = callsign

    def set_squawk(self, squawk: str) -> None:
        """Set assigned squawk code"""
        self._squawk = squawk

    def register_callback(self, callback: Callable[[ATCMessage], None]) -> None:
        """Register callback for ATC messages"""
        self._callbacks.append(callback)

    def _add_message(self, message: ATCMessage) -> None:
        """Add a message to history and notify callbacks"""
        self._messages.append(message)

        for callback in self._callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"ATC callback error: {e}")

    def generate_clearance(self, departure_icao: str, arrival_icao: str,
                          cruise_altitude: int, sid: str = "DIRECT") -> str:
        """Generate IFR clearance"""
        self._clearance_received = True
        self._assigned_altitude = cruise_altitude

        clearance = (
            f"{self._callsign}, cleared to {arrival_icao} airport, "
            f"via {sid} departure, "
            f"climb and maintain {cruise_altitude // 100} thousand, "
            f"squawk {self._squawk}."
        )

        self._departure_clearance = clearance

        message = ATCMessage(
            facility=ATCFacility.DELIVERY,
            callsign=self._callsign,
            message=clearance
        )
        self._add_message(message)

        return clearance

    def generate_taxi_clearance(self, runway: str, via: str = "") -> str:
        """Generate taxi clearance"""
        via_text = f" via {via}" if via else ""
        clearance = f"{self._callsign}, taxi to runway {runway}{via_text}, hold short."

        self._taxi_clearance = clearance

        message = ATCMessage(
            facility=ATCFacility.GROUND,
            callsign=self._callsign,
            message=clearance
        )
        self._add_message(message)

        return clearance

    def generate_takeoff_clearance(self, runway: str, wind: str = "") -> str:
        """Generate takeoff clearance"""
        wind_text = f" Wind {wind}." if wind else ""
        clearance = f"{self._callsign}, runway {runway}, cleared for takeoff.{wind_text}"

        message = ATCMessage(
            facility=ATCFacility.TOWER,
            callsign=self._callsign,
            message=clearance
        )
        self._add_message(message)

        return clearance

    def generate_departure_contact(self, frequency: str) -> str:
        """Generate frequency change to departure"""
        msg = f"{self._callsign}, contact departure on {frequency}. Good day."

        message = ATCMessage(
            facility=ATCFacility.TOWER,
            callsign=self._callsign,
            message=msg
        )
        self._add_message(message)

        return msg

    def generate_altitude_assignment(self, altitude: int) -> str:
        """Generate altitude assignment"""
        self._assigned_altitude = altitude

        if altitude >= 18000:
            alt_str = f"flight level {altitude // 100}"
        else:
            alt_str = f"{altitude // 100} thousand"

        msg = f"{self._callsign}, climb and maintain {alt_str}."

        message = ATCMessage(
            facility=self._current_facility,
            callsign=self._callsign,
            message=msg
        )
        self._add_message(message)

        return msg

    def generate_heading_assignment(self, heading: int) -> str:
        """Generate heading assignment"""
        self._assigned_heading = heading

        msg = f"{self._callsign}, turn heading {heading:03d}."

        message = ATCMessage(
            facility=self._current_facility,
            callsign=self._callsign,
            message=msg
        )
        self._add_message(message)

        return msg

    def generate_approach_clearance(self, approach_type: str, runway: str) -> str:
        """Generate approach clearance"""
        msg = f"{self._callsign}, cleared {approach_type} approach runway {runway}."

        message = ATCMessage(
            facility=ATCFacility.APPROACH,
            callsign=self._callsign,
            message=msg
        )
        self._add_message(message)

        return msg

    def generate_landing_clearance(self, runway: str, wind: str = "") -> str:
        """Generate landing clearance"""
        wind_text = f" Wind {wind}." if wind else ""
        msg = f"{self._callsign}, runway {runway}, cleared to land.{wind_text}"

        message = ATCMessage(
            facility=ATCFacility.TOWER,
            callsign=self._callsign,
            message=msg
        )
        self._add_message(message)

        return msg

    def generate_taxi_to_parking(self, gate: str = "parking") -> str:
        """Generate taxi to parking clearance"""
        msg = f"{self._callsign}, taxi to {gate}. Contact ground point one for any assistance."

        message = ATCMessage(
            facility=ATCFacility.TOWER,
            callsign=self._callsign,
            message=msg
        )
        self._add_message(message)

        return msg

    def generate_atis(self, airport_icao: str, info_letter: str,
                     wind: str, visibility: str, ceiling: str,
                     temperature: str, altimeter: str, runway: str) -> str:
        """Generate ATIS message"""
        atis = (
            f"{airport_icao} information {info_letter}. "
            f"Wind {wind}. Visibility {visibility}. {ceiling}. "
            f"Temperature {temperature}. Altimeter {altimeter}. "
            f"Landing and departing runway {runway}. "
            f"Advise on initial contact you have information {info_letter}."
        )

        message = ATCMessage(
            facility=ATCFacility.ATIS,
            callsign=airport_icao,
            message=atis
        )
        self._add_message(message)

        return atis

    def generate_for_phase(self, phase: str, **kwargs) -> Optional[str]:
        """Generate appropriate ATC message for flight phase"""
        if not self._enabled:
            return None

        if phase == "taxi_out":
            runway = kwargs.get('runway', '27')
            return self.generate_taxi_clearance(runway)

        elif phase == "takeoff_roll":
            runway = kwargs.get('runway', '27')
            wind = kwargs.get('wind', '')
            return self.generate_takeoff_clearance(runway, wind)

        elif phase == "initial_climb":
            return self.generate_departure_contact("125.85")

        elif phase == "approach":
            approach = kwargs.get('approach_type', 'ILS')
            runway = kwargs.get('runway', '27')
            return self.generate_approach_clearance(approach, runway)

        elif phase == "short_final":
            runway = kwargs.get('runway', '27')
            wind = kwargs.get('wind', '')
            return self.generate_landing_clearance(runway, wind)

        elif phase == "taxi_in":
            return self.generate_taxi_to_parking()

        return None

    def reset(self) -> None:
        """Reset ATC simulator"""
        self._messages.clear()
        self._clearance_received = False
        self._taxi_clearance = ""
        self._departure_clearance = ""
        self._assigned_altitude = 0
        self._assigned_heading = 0
        logger.info("ATC simulator reset")

    def get_messages(self, last_n: int = 10) -> List[ATCMessage]:
        """Get recent messages"""
        return self._messages[-last_n:]

    def get_stats(self) -> Dict:
        """Get ATC statistics"""
        return {
            'total_messages': len(self._messages),
            'current_facility': self._current_facility.value,
            'clearance_received': self._clearance_received,
            'assigned_altitude': self._assigned_altitude,
            'enabled': self._enabled
        }


# Global ATC simulator instance
_atc_simulator: Optional[ATCSimulator] = None

def get_atc_simulator() -> ATCSimulator:
    """Get or create global ATC simulator"""
    global _atc_simulator
    if _atc_simulator is None:
        _atc_simulator = ATCSimulator()
    return _atc_simulator
