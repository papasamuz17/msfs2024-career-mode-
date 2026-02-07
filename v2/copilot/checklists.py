"""
Interactive Checklists for V2 Copilot
Voice-enabled checklists for different flight phases
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Copilot.Checklists")


class ChecklistPhase(Enum):
    """Checklist phases"""
    BEFORE_START = "before_start"
    AFTER_START = "after_start"
    BEFORE_TAXI = "before_taxi"
    BEFORE_TAKEOFF = "before_takeoff"
    AFTER_TAKEOFF = "after_takeoff"
    CRUISE = "cruise"
    DESCENT = "descent"
    APPROACH = "approach"
    BEFORE_LANDING = "before_landing"
    AFTER_LANDING = "after_landing"
    SHUTDOWN = "shutdown"


class ItemStatus(Enum):
    """Checklist item status"""
    PENDING = "pending"
    CHECKED = "checked"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class ChecklistItem:
    """Single checklist item"""
    id: str
    challenge: str           # What copilot says
    response: str            # Expected response
    action: str = ""         # What to do
    auto_check: bool = False  # Can be auto-verified
    auto_check_var: str = ""  # SimConnect variable to check
    auto_check_value: float = 0  # Expected value
    status: ItemStatus = ItemStatus.PENDING
    checked_at: Optional[str] = None


@dataclass
class Checklist:
    """Complete checklist"""
    id: str
    phase: ChecklistPhase
    name: str
    description: str
    items: List[ChecklistItem] = field(default_factory=list)
    active: bool = False
    current_item_index: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @property
    def current_item(self) -> Optional[ChecklistItem]:
        if 0 <= self.current_item_index < len(self.items):
            return self.items[self.current_item_index]
        return None

    @property
    def progress(self) -> float:
        if not self.items:
            return 0.0
        checked = sum(1 for i in self.items if i.status in [ItemStatus.CHECKED, ItemStatus.SKIPPED])
        return (checked / len(self.items)) * 100

    @property
    def is_complete(self) -> bool:
        return all(i.status in [ItemStatus.CHECKED, ItemStatus.SKIPPED] for i in self.items)

    def start(self) -> None:
        self.active = True
        self.started_at = datetime.now().isoformat()
        self.current_item_index = 0
        for item in self.items:
            item.status = ItemStatus.PENDING
        logger.info(f"Checklist started: {self.name}")

    def check_current(self) -> bool:
        """Mark current item as checked and move to next"""
        item = self.current_item
        if item:
            item.status = ItemStatus.CHECKED
            item.checked_at = datetime.now().isoformat()
            self.current_item_index += 1
            return True
        return False

    def skip_current(self) -> bool:
        """Skip current item and move to next"""
        item = self.current_item
        if item:
            item.status = ItemStatus.SKIPPED
            item.checked_at = datetime.now().isoformat()
            self.current_item_index += 1
            return True
        return False

    def complete(self) -> None:
        self.active = False
        self.completed_at = datetime.now().isoformat()
        logger.info(f"Checklist completed: {self.name}")


# ==================== SIMCONNECT VARIABLE CHECKS ====================
# Each auto-check item defines:
# - auto_check_var: SimConnect variable name
# - auto_check_value: Expected value (or threshold)
# - auto_check_op: Comparison operator ("eq", "gt", "lt", "gte", "lte", "range")
# For "range", auto_check_value should be a tuple (min, max)

@dataclass
class AutoCheckConfig:
    """Configuration for automatic item verification"""
    var: str                    # SimConnect variable
    expected: float             # Expected value
    op: str = "eq"              # Comparison: eq, gt, lt, gte, lte, neq
    tolerance: float = 0.1      # Tolerance for equality checks
    response_ok: str = ""       # Response when check passes
    response_fail: str = ""     # Response when check fails


# ==================== DEFAULT CHECKLISTS ====================

def create_before_start_checklist() -> Checklist:
    return Checklist(
        id="before_start",
        phase=ChecklistPhase.BEFORE_START,
        name="Before Start",
        description="Checklist avant demarrage moteur",
        items=[
            ChecklistItem("parking_brake", "Frein de parking", "SERRE",
                          auto_check=True, auto_check_var="BRAKE_PARKING_POSITION", auto_check_value=1),
            ChecklistItem("throttle", "Manette des gaz", "RALENTI",
                          auto_check=True, auto_check_var="GENERAL_ENG_THROTTLE_LEVER_POSITION:1", auto_check_value=0),
            ChecklistItem("mixture", "Mixture", "RICHE",
                          auto_check=True, auto_check_var="GENERAL_ENG_MIXTURE_LEVER_POSITION:1", auto_check_value=100),
            ChecklistItem("fuel_selector", "Selecteur carburant", "VERIFIE"),
            ChecklistItem("master_switch", "Battery Master", "ON",
                          auto_check=True, auto_check_var="ELECTRICAL_MASTER_BATTERY", auto_check_value=1),
            ChecklistItem("avionics", "Avionique", "OFF",
                          auto_check=True, auto_check_var="AVIONICS_MASTER_SWITCH", auto_check_value=0),
            ChecklistItem("beacon", "Beacon", "ON",
                          auto_check=True, auto_check_var="LIGHT_BEACON", auto_check_value=1),
            ChecklistItem("fuel_pump", "Pompe carburant", "VERIFIEE"),
        ]
    )


def create_before_takeoff_checklist() -> Checklist:
    return Checklist(
        id="before_takeoff",
        phase=ChecklistPhase.BEFORE_TAKEOFF,
        name="Before Takeoff",
        description="Checklist avant decollage",
        items=[
            ChecklistItem("flight_controls", "Commandes de vol", "LIBRES"),
            ChecklistItem("instruments", "Instruments", "VERIFIES"),
            ChecklistItem("fuel", "Carburant", "SUFFISANT",
                          auto_check=True, auto_check_var="FUEL_TOTAL_QUANTITY_WEIGHT", auto_check_value=50),  # > 50 lbs
            ChecklistItem("trim", "Trim", "DECOLLAGE"),
            ChecklistItem("flaps", "Volets", "POSITION DECOLLAGE",
                          auto_check=True, auto_check_var="FLAPS_HANDLE_PERCENT", auto_check_value=15),  # ~10-20%
            ChecklistItem("transponder", "Transpondeur", "ON",
                          auto_check=True, auto_check_var="TRANSPONDER_STATE", auto_check_value=1),
            ChecklistItem("lights", "Landing et Strobes", "ON",
                          auto_check=True, auto_check_var="LIGHT_LANDING", auto_check_value=1),
            ChecklistItem("doors", "Portes et verriere", "FERMEES",
                          auto_check=True, auto_check_var="CANOPY_OPEN", auto_check_value=0),
        ]
    )


def create_approach_checklist() -> Checklist:
    return Checklist(
        id="approach",
        phase=ChecklistPhase.APPROACH,
        name="Approach",
        description="Checklist approche",
        items=[
            ChecklistItem("altimeter", "Altimetre", "CALE"),
            ChecklistItem("nav_aids", "Aides navigation", "SELECTIONNEES"),
            ChecklistItem("approach_brief", "Briefing approche", "COMPLETE"),
            ChecklistItem("fuel", "Carburant", "VERIFIE",
                          auto_check=True, auto_check_var="FUEL_TOTAL_QUANTITY_WEIGHT", auto_check_value=30),
            ChecklistItem("seat_belts", "Ceintures", "ATTACHEES"),
        ]
    )


def create_before_landing_checklist() -> Checklist:
    return Checklist(
        id="before_landing",
        phase=ChecklistPhase.BEFORE_LANDING,
        name="Before Landing",
        description="Checklist avant atterrissage",
        items=[
            ChecklistItem("gear", "Train", "SORTI VERROUILLE",
                          auto_check=True, auto_check_var="GEAR_HANDLE_POSITION", auto_check_value=1),
            ChecklistItem("flaps", "Volets", "ATTERRISSAGE",
                          auto_check=True, auto_check_var="FLAPS_HANDLE_PERCENT", auto_check_value=50),  # > 50%
            ChecklistItem("speed", "Vitesse", "STABLE",
                          auto_check=True, auto_check_var="AIRSPEED_INDICATED", auto_check_value=80),  # < 150kts approach
            ChecklistItem("mixture", "Mixture", "RICHE",
                          auto_check=True, auto_check_var="GENERAL_ENG_MIXTURE_LEVER_POSITION:1", auto_check_value=100),
            ChecklistItem("lights", "Landing lights", "ON",
                          auto_check=True, auto_check_var="LIGHT_LANDING", auto_check_value=1),
            ChecklistItem("autopilot", "Pilote auto", "OFF",
                          auto_check=True, auto_check_var="AUTOPILOT_MASTER", auto_check_value=0),
        ]
    )


def create_after_landing_checklist() -> Checklist:
    return Checklist(
        id="after_landing",
        phase=ChecklistPhase.AFTER_LANDING,
        name="After Landing",
        description="Checklist apres atterrissage",
        items=[
            ChecklistItem("flaps", "Volets", "RENTRES",
                          auto_check=True, auto_check_var="FLAPS_HANDLE_PERCENT", auto_check_value=0),
            ChecklistItem("transponder", "Transpondeur", "STANDBY"),
            ChecklistItem("landing_lights", "Landing lights", "OFF",
                          auto_check=True, auto_check_var="LIGHT_LANDING", auto_check_value=0),
            ChecklistItem("strobes", "Strobes", "OFF",
                          auto_check=True, auto_check_var="LIGHT_STROBE", auto_check_value=0),
            ChecklistItem("taxi_light", "Feu taxi", "ON",
                          auto_check=True, auto_check_var="LIGHT_TAXI", auto_check_value=1),
        ]
    )


def create_shutdown_checklist() -> Checklist:
    return Checklist(
        id="shutdown",
        phase=ChecklistPhase.SHUTDOWN,
        name="Shutdown",
        description="Checklist arret moteur",
        items=[
            ChecklistItem("parking_brake", "Frein de parking", "SERRE",
                          auto_check=True, auto_check_var="BRAKE_PARKING_POSITION", auto_check_value=1),
            ChecklistItem("throttle", "Manette gaz", "RALENTI",
                          auto_check=True, auto_check_var="GENERAL_ENG_THROTTLE_LEVER_POSITION:1", auto_check_value=0),
            ChecklistItem("avionics", "Avionique", "OFF",
                          auto_check=True, auto_check_var="AVIONICS_MASTER_SWITCH", auto_check_value=0),
            ChecklistItem("mixture", "Mixture", "COUPE",
                          auto_check=True, auto_check_var="GENERAL_ENG_MIXTURE_LEVER_POSITION:1", auto_check_value=0),
            ChecklistItem("magnetos", "Magnetos", "OFF"),
            ChecklistItem("master", "Master switch", "OFF",
                          auto_check=True, auto_check_var="ELECTRICAL_MASTER_BATTERY", auto_check_value=0),
            ChecklistItem("fuel_selector", "Selecteur carburant", "FERME"),
            ChecklistItem("lights", "Tous feux", "OFF",
                          auto_check=True, auto_check_var="LIGHT_NAV", auto_check_value=0),
        ]
    )


class ChecklistManager:
    """Manages interactive checklists"""

    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._checklists: Dict[str, Checklist] = {}
        self._active_checklist: Optional[Checklist] = None
        self._callbacks: List[Callable] = []
        self._history: List[Dict] = []

        self._initialize_checklists()

    def _initialize_checklists(self) -> None:
        """Initialize all default checklists"""
        checklists = [
            create_before_start_checklist(),
            create_before_takeoff_checklist(),
            create_approach_checklist(),
            create_before_landing_checklist(),
            create_after_landing_checklist(),
            create_shutdown_checklist()
        ]

        for cl in checklists:
            self._checklists[cl.id] = cl

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def active_checklist(self) -> Optional[Checklist]:
        return self._active_checklist

    def register_callback(self, callback: Callable) -> None:
        """Register callback for checklist events"""
        self._callbacks.append(callback)

    def get_checklist(self, checklist_id: str) -> Optional[Checklist]:
        """Get checklist by ID"""
        return self._checklists.get(checklist_id)

    def get_checklist_for_phase(self, phase: ChecklistPhase) -> Optional[Checklist]:
        """Get checklist for a specific flight phase"""
        for cl in self._checklists.values():
            if cl.phase == phase:
                return cl
        return None

    def start_checklist(self, checklist_id: str) -> Optional[Checklist]:
        """Start a specific checklist"""
        if not self._enabled:
            return None

        if checklist_id not in self._checklists:
            logger.warning(f"Checklist not found: {checklist_id}")
            return None

        # Create a fresh copy
        template = self._checklists[checklist_id]
        checklist = Checklist(
            id=template.id,
            phase=template.phase,
            name=template.name,
            description=template.description,
            items=[ChecklistItem(
                id=item.id,
                challenge=item.challenge,
                response=item.response,
                action=item.action,
                auto_check=item.auto_check,
                auto_check_var=item.auto_check_var,
                auto_check_value=item.auto_check_value
            ) for item in template.items]
        )

        checklist.start()
        self._active_checklist = checklist

        self._notify("checklist_started", checklist)
        return checklist

    def check_item(self) -> Optional[ChecklistItem]:
        """Check current item and move to next"""
        if not self._active_checklist:
            return None

        item = self._active_checklist.current_item
        if item:
            self._active_checklist.check_current()
            self._notify("item_checked", item)

            if self._active_checklist.is_complete:
                self._complete_checklist()

            return item
        return None

    def skip_item(self) -> Optional[ChecklistItem]:
        """Skip current item"""
        if not self._active_checklist:
            return None

        item = self._active_checklist.current_item
        if item:
            self._active_checklist.skip_current()
            self._notify("item_skipped", item)

            if self._active_checklist.is_complete:
                self._complete_checklist()

            return item
        return None

    def _complete_checklist(self) -> None:
        """Complete the active checklist"""
        if not self._active_checklist:
            return

        self._active_checklist.complete()

        self._history.append({
            'checklist_id': self._active_checklist.id,
            'name': self._active_checklist.name,
            'completed_at': self._active_checklist.completed_at,
            'items_checked': sum(1 for i in self._active_checklist.items
                                 if i.status == ItemStatus.CHECKED),
            'items_skipped': sum(1 for i in self._active_checklist.items
                                 if i.status == ItemStatus.SKIPPED)
        })

        self._notify("checklist_completed", self._active_checklist)
        self._active_checklist = None

    def cancel_checklist(self) -> None:
        """Cancel the active checklist"""
        if self._active_checklist:
            logger.info(f"Checklist cancelled: {self._active_checklist.name}")
            self._notify("checklist_cancelled", self._active_checklist)
            self._active_checklist = None

    def get_current_challenge(self) -> Optional[str]:
        """Get current item challenge text"""
        if self._active_checklist and self._active_checklist.current_item:
            item = self._active_checklist.current_item
            return f"{item.challenge}... {item.response}"
        return None

    def _notify(self, event: str, data: any) -> None:
        """Notify callbacks"""
        for callback in self._callbacks:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"Checklist callback error: {e}")

    def get_available_checklists(self) -> List[str]:
        """Get list of available checklist IDs"""
        return list(self._checklists.keys())

    def get_stats(self) -> Dict:
        """Get checklist statistics"""
        return {
            'total_completed': len(self._history),
            'active': self._active_checklist.name if self._active_checklist else None,
            'enabled': self._enabled
        }

    # ==================== AUTO-CHECK FUNCTIONALITY ====================

    def verify_item(self, item: ChecklistItem, sim_data: Dict[str, float]) -> tuple:
        """
        Verify a checklist item against SimConnect data

        Args:
            item: The checklist item to verify
            sim_data: Dictionary of SimConnect variable values

        Returns:
            (passed: bool, actual_value: float or None, message: str)
        """
        if not item.auto_check or not item.auto_check_var:
            return (None, None, "Manuel")  # Cannot auto-verify

        var_name = item.auto_check_var
        expected = item.auto_check_value

        # Get actual value from sim data
        actual = sim_data.get(var_name)
        if actual is None:
            return (None, None, f"Variable {var_name} non disponible")

        # Determine check type based on expected value and item context
        # Most checks are equality with tolerance, but some need special handling
        tolerance = 15  # Default tolerance for percentage values

        # Special cases based on variable type
        if "POSITION" in var_name or "HANDLE" in var_name:
            # Binary switches: 0 or 1
            passed = (actual > 0.5) == (expected > 0.5)
        elif "LIGHT_" in var_name or "MASTER" in var_name or "SWITCH" in var_name:
            # Binary on/off
            passed = (actual > 0.5) == (expected > 0.5)
        elif "PERCENT" in var_name:
            # Percentage values - check within tolerance
            passed = abs(actual - expected) <= tolerance
        elif "QUANTITY" in var_name or "WEIGHT" in var_name:
            # Fuel quantity - check if above minimum
            passed = actual >= expected
        elif "AIRSPEED" in var_name:
            # Speed check - typically we want it below a max for landing
            passed = actual <= 150  # Reasonable approach speed
        elif "THROTTLE" in var_name:
            # Throttle - check if near expected (0 = idle, 100 = full)
            passed = abs(actual - expected) <= 10
        elif "MIXTURE" in var_name:
            # Mixture lever position
            if expected >= 90:  # "Rich"
                passed = actual >= 80
            elif expected <= 10:  # "Cutoff"
                passed = actual <= 20
            else:
                passed = abs(actual - expected) <= 20
        elif "TRANSPONDER" in var_name:
            # Transponder state (0=off, 1=standby, 2=test, 3=on, 4=alt)
            passed = actual >= 1  # At least standby
        elif "CANOPY" in var_name:
            # Canopy/door: 0 = closed
            passed = actual < 0.1
        elif "AUTOPILOT" in var_name:
            # Autopilot master
            passed = (actual > 0.5) == (expected > 0.5)
        elif "FLAPS" in var_name:
            # Flaps - check if at least at expected percentage
            if expected == 0:
                passed = actual <= 5  # Retracted
            else:
                passed = actual >= expected - 10  # Within range
        else:
            # Default: equality with tolerance
            passed = abs(actual - expected) <= tolerance

        status = "OK" if passed else "A VERIFIER"
        return (passed, actual, status)

    def auto_check_current_item(self, sim_data: Dict[str, float]) -> Optional[Dict]:
        """
        Automatically check the current item if it has auto_check enabled

        Args:
            sim_data: Dictionary of SimConnect variable values

        Returns:
            Dict with check result or None if no active checklist
        """
        if not self._active_checklist:
            return None

        item = self._active_checklist.current_item
        if not item:
            return None

        passed, actual, message = self.verify_item(item, sim_data)

        result = {
            'item_id': item.id,
            'challenge': item.challenge,
            'response': item.response,
            'auto_check': item.auto_check,
            'passed': passed,
            'actual_value': actual,
            'message': message
        }

        # If auto-check passed, automatically check the item
        if passed is True:
            self._active_checklist.check_current()
            self._notify("item_auto_checked", result)

            if self._active_checklist.is_complete:
                self._complete_checklist()
            else:
                # Notify about next item
                next_item = self._active_checklist.current_item
                if next_item:
                    self._notify("item_next", next_item)

        return result

    def run_auto_checklist(self, checklist_id: str, sim_data: Dict[str, float],
                           speak_callback: Callable[[str], None] = None,
                           delay_between_items: float = 2.0) -> Dict:
        """
        Run through an entire checklist automatically, checking items against sim data

        Args:
            checklist_id: ID of checklist to run
            sim_data: Dictionary of SimConnect variable values
            speak_callback: Optional callback to speak items/results
            delay_between_items: Delay in seconds between items (for TTS)

        Returns:
            Summary of checklist run
        """
        checklist = self.start_checklist(checklist_id)
        if not checklist:
            return {'error': f'Checklist {checklist_id} not found'}

        results = []
        failed_items = []

        while checklist.current_item:
            item = checklist.current_item

            # Speak the challenge
            if speak_callback:
                speak_callback(f"{item.challenge}")

            # Check the item
            passed, actual, message = self.verify_item(item, sim_data)

            result = {
                'item': item.challenge,
                'expected': item.response,
                'passed': passed,
                'actual': actual,
                'message': message
            }
            results.append(result)

            if passed is True:
                # Auto-verified
                if speak_callback:
                    speak_callback(f"{item.response}. Verifie.")
                checklist.check_current()
            elif passed is False:
                # Failed verification
                failed_items.append(item.challenge)
                if speak_callback:
                    speak_callback(f"{item.response}. A verifier!")
                checklist.skip_current()  # Skip and continue
            else:
                # Manual check required
                if speak_callback:
                    speak_callback(f"{item.response}. Manuel.")
                checklist.check_current()  # Assume OK for manual items

            if checklist.is_complete:
                break

        self._complete_checklist()

        summary = {
            'checklist': checklist_id,
            'total_items': len(results),
            'passed': sum(1 for r in results if r['passed'] is True),
            'failed': len(failed_items),
            'manual': sum(1 for r in results if r['passed'] is None),
            'failed_items': failed_items,
            'results': results
        }

        if speak_callback:
            if failed_items:
                speak_callback(f"Checklist terminee. {len(failed_items)} items a verifier: {', '.join(failed_items)}")
            else:
                speak_callback("Checklist complete. Tous les items verifies.")

        return summary


# Global checklist manager instance
_checklist_manager: Optional[ChecklistManager] = None

def get_checklist_manager() -> ChecklistManager:
    """Get or create global checklist manager"""
    global _checklist_manager
    if _checklist_manager is None:
        _checklist_manager = ChecklistManager()
    return _checklist_manager
