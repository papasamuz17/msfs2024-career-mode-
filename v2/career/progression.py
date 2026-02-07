"""
Progression System for V2
Manages unlocks, achievements, and career progression
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Progression")


class UnlockType(Enum):
    """Types of unlockable content"""
    AIRCRAFT_CATEGORY = "aircraft"
    MISSION_TYPE = "mission"
    COMPANY = "company"
    FEATURE = "feature"
    ACHIEVEMENT = "achievement"


@dataclass
class Requirement:
    """Requirement for an unlock"""
    type: str                    # hours, flights, license, reputation, landing_score, etc.
    target: str                  # Category or specific value name
    value: float                 # Required value
    description: str = ""

    def check(self, pilot_data: Dict, company_data: Dict) -> bool:
        """Check if requirement is met"""
        if self.type == "total_hours":
            return pilot_data.get('total_hours', 0) >= self.value
        elif self.type == "category_hours":
            hours = pilot_data.get('hours_by_category', {})
            return hours.get(self.target, 0) >= self.value
        elif self.type == "license":
            return pilot_data.get('license', 'Student') == self.target
        elif self.type == "license_min":
            license_order = ['Student', 'PPL', 'CPL', 'ATPL']
            current = pilot_data.get('license', 'Student')
            return license_order.index(current) >= license_order.index(self.target)
        elif self.type == "missions":
            return pilot_data.get('missions_completed', 0) >= self.value
        elif self.type == "reputation":
            rep = company_data.get(self.target, {}).get('reputation', 0)
            return rep >= self.value
        elif self.type == "perfect_landings":
            return pilot_data.get('perfect_landings', 0) >= self.value
        elif self.type == "total_distance":
            return pilot_data.get('total_distance_nm', 0) >= self.value
        return False


@dataclass
class Unlock:
    """Unlockable content"""
    id: str
    name: str
    description: str
    unlock_type: UnlockType
    requirements: List[Requirement]
    rewards: Dict = field(default_factory=dict)
    unlocked: bool = False
    unlocked_at: Optional[str] = None

    def check_requirements(self, pilot_data: Dict, company_data: Dict) -> bool:
        """Check if all requirements are met"""
        return all(req.check(pilot_data, company_data) for req in self.requirements)

    def unlock(self) -> None:
        """Mark as unlocked"""
        self.unlocked = True
        self.unlocked_at = datetime.now().isoformat()


@dataclass
class Achievement:
    """Special achievement"""
    id: str
    name: str
    description: str
    icon: str = ""
    points: int = 0
    secret: bool = False
    earned: bool = False
    earned_at: Optional[str] = None

    def earn(self) -> None:
        """Mark achievement as earned"""
        self.earned = True
        self.earned_at = datetime.now().isoformat()


# Default unlocks configuration
DEFAULT_UNLOCKS: List[Unlock] = [
    # Aircraft category unlocks
    Unlock(
        id="unlock_twin_piston",
        name="Bimoteur Piston",
        description="Debloquer les bimoteurs a pistons (Baron, DA62)",
        unlock_type=UnlockType.AIRCRAFT_CATEGORY,
        requirements=[
            Requirement("license_min", "PPL", 0, "Licence PPL requise"),
            Requirement("category_hours", "light_piston", 25, "25h sur monomoteur")
        ],
        rewards={"aircraft_category": "twin_piston"}
    ),
    Unlock(
        id="unlock_turboprop",
        name="Turbopropulseur",
        description="Debloquer les turbopropulseurs (TBM, PC-12)",
        unlock_type=UnlockType.AIRCRAFT_CATEGORY,
        requirements=[
            Requirement("license_min", "CPL", 0, "Licence CPL requise"),
            Requirement("total_hours", "", 100, "100h de vol total")
        ],
        rewards={"aircraft_category": "single_turboprop"}
    ),
    Unlock(
        id="unlock_jet",
        name="Jet",
        description="Debloquer les jets commerciaux",
        unlock_type=UnlockType.AIRCRAFT_CATEGORY,
        requirements=[
            Requirement("license_min", "ATPL", 0, "Licence ATPL requise"),
            Requirement("category_hours", "turboprop", 50, "50h sur turboprop")
        ],
        rewards={"aircraft_category": "jet"}
    ),
    Unlock(
        id="unlock_heavy",
        name="Gros Porteur",
        description="Debloquer les gros porteurs (747, A380)",
        unlock_type=UnlockType.AIRCRAFT_CATEGORY,
        requirements=[
            Requirement("license_min", "ATPL", 0, "Licence ATPL requise"),
            Requirement("category_hours", "jet", 200, "200h sur jet")
        ],
        rewards={"aircraft_category": "heavy_jet"}
    ),

    # Company unlocks
    Unlock(
        id="unlock_air_france",
        name="Air France",
        description="Debloquer les missions Air France",
        unlock_type=UnlockType.COMPANY,
        requirements=[
            Requirement("license_min", "CPL", 0, "Licence CPL requise"),
            Requirement("total_hours", "", 200, "200h de vol total")
        ],
        rewards={"company": "air_france"}
    ),

    # Feature unlocks
    Unlock(
        id="unlock_ifr",
        name="Vol IFR",
        description="Debloquer les missions en conditions IFR",
        unlock_type=UnlockType.FEATURE,
        requirements=[
            Requirement("total_hours", "", 50, "50h de vol total"),
            Requirement("missions", "", 10, "10 missions completees")
        ],
        rewards={"feature": "ifr_flights"}
    ),
    Unlock(
        id="unlock_long_haul",
        name="Long-Courrier",
        description="Debloquer les missions long-courrier (>1000nm)",
        unlock_type=UnlockType.FEATURE,
        requirements=[
            Requirement("license_min", "ATPL", 0, "Licence ATPL requise"),
            Requirement("total_distance", "", 10000, "10,000nm parcourus")
        ],
        rewards={"feature": "long_haul"}
    )
]

# Default achievements
DEFAULT_ACHIEVEMENTS: List[Achievement] = [
    Achievement("first_flight", "Premier Vol", "Completez votre premier vol", points=10),
    Achievement("first_perfect_landing", "Atterrissage Parfait", "Atterrissez a moins de 60 fpm", points=25),
    Achievement("100_hours", "Centenaire", "Accumulez 100 heures de vol", points=50),
    Achievement("500_hours", "Veteran", "Accumulez 500 heures de vol", points=100),
    Achievement("1000_hours", "Expert", "Accumulez 1000 heures de vol", points=200),
    Achievement("butter_master", "Maitre du Beurre", "10 atterrissages parfaits", points=75),
    Achievement("globe_trotter", "Globe-Trotter", "Parcourez 50,000 nm", points=100),
    Achievement("all_licenses", "Pilote Complet", "Obtenez toutes les licences", points=150),
    Achievement("night_owl", "Hibou", "10 vols de nuit", points=50),
    Achievement("weather_warrior", "Guerrier Meteo", "10 vols en mauvaise meteo", points=75),
    Achievement("crosswind_master", "Maitre du Vent", "10 atterrissages avec vent traversier > 15kt", points=100),
    Achievement("challenge_king", "Roi des Challenges", "Completez 50 challenges d'atterrissage", points=150, secret=True),
]


class ProgressionManager:
    """Manages career progression, unlocks, and achievements"""

    def __init__(self):
        self._unlocks: Dict[str, Unlock] = {}
        self._achievements: Dict[str, Achievement] = {}
        self._callbacks: List[Callable] = []

        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize default unlocks and achievements"""
        for unlock in DEFAULT_UNLOCKS:
            self._unlocks[unlock.id] = unlock

        for achievement in DEFAULT_ACHIEVEMENTS:
            self._achievements[achievement.id] = achievement

    def register_callback(self, callback: Callable) -> None:
        """Register callback for unlock/achievement events"""
        self._callbacks.append(callback)

    def _notify(self, event_type: str, item: any) -> None:
        """Notify callbacks of an event"""
        for callback in self._callbacks:
            try:
                callback(event_type, item)
            except Exception as e:
                logger.error(f"Progression callback error: {e}")

    def check_unlocks(self, pilot_data: Dict, company_data: Dict) -> List[Unlock]:
        """Check and process any new unlocks"""
        newly_unlocked = []

        for unlock in self._unlocks.values():
            if not unlock.unlocked:
                if unlock.check_requirements(pilot_data, company_data):
                    unlock.unlock()
                    newly_unlocked.append(unlock)
                    logger.info(f"Unlocked: {unlock.name}")
                    self._notify("unlock", unlock)

        return newly_unlocked

    def check_achievement(self, achievement_id: str, condition: bool) -> bool:
        """Check and award a specific achievement"""
        if achievement_id not in self._achievements:
            return False

        achievement = self._achievements[achievement_id]

        if not achievement.earned and condition:
            achievement.earn()
            logger.info(f"Achievement earned: {achievement.name}")
            self._notify("achievement", achievement)
            return True

        return False

    def check_all_achievements(self, pilot_data: Dict, logbook_data: Dict) -> List[Achievement]:
        """Check all achievements based on current data"""
        newly_earned = []

        # First flight
        if self.check_achievement("first_flight", pilot_data.get('total_flights', 0) >= 1):
            newly_earned.append(self._achievements["first_flight"])

        # Perfect landing
        if self.check_achievement("first_perfect_landing", pilot_data.get('perfect_landings', 0) >= 1):
            newly_earned.append(self._achievements["first_perfect_landing"])

        # Hour milestones
        total_hours = pilot_data.get('total_hours', 0)
        if self.check_achievement("100_hours", total_hours >= 100):
            newly_earned.append(self._achievements["100_hours"])
        if self.check_achievement("500_hours", total_hours >= 500):
            newly_earned.append(self._achievements["500_hours"])
        if self.check_achievement("1000_hours", total_hours >= 1000):
            newly_earned.append(self._achievements["1000_hours"])

        # Butter master
        if self.check_achievement("butter_master", pilot_data.get('perfect_landings', 0) >= 10):
            newly_earned.append(self._achievements["butter_master"])

        # Globe trotter
        if self.check_achievement("globe_trotter", pilot_data.get('total_distance_nm', 0) >= 50000):
            newly_earned.append(self._achievements["globe_trotter"])

        # All licenses
        if self.check_achievement("all_licenses", pilot_data.get('license') == 'ATPL'):
            newly_earned.append(self._achievements["all_licenses"])

        return newly_earned

    def get_unlock(self, unlock_id: str) -> Optional[Unlock]:
        """Get unlock by ID"""
        return self._unlocks.get(unlock_id)

    def get_achievement(self, achievement_id: str) -> Optional[Achievement]:
        """Get achievement by ID"""
        return self._achievements.get(achievement_id)

    def get_all_unlocks(self) -> List[Unlock]:
        """Get all unlocks"""
        return list(self._unlocks.values())

    def get_unlocked(self) -> List[Unlock]:
        """Get all unlocked items"""
        return [u for u in self._unlocks.values() if u.unlocked]

    def get_locked(self) -> List[Unlock]:
        """Get all locked items"""
        return [u for u in self._unlocks.values() if not u.unlocked]

    def get_all_achievements(self) -> List[Achievement]:
        """Get all achievements"""
        return list(self._achievements.values())

    def get_earned_achievements(self) -> List[Achievement]:
        """Get earned achievements"""
        return [a for a in self._achievements.values() if a.earned]

    def get_achievement_points(self) -> int:
        """Get total achievement points earned"""
        return sum(a.points for a in self._achievements.values() if a.earned)

    def to_save_dict(self) -> Dict:
        """Convert to save format"""
        return {
            'unlocks': {
                uid: {'unlocked': u.unlocked, 'unlocked_at': u.unlocked_at}
                for uid, u in self._unlocks.items()
            },
            'achievements': {
                aid: {'earned': a.earned, 'earned_at': a.earned_at}
                for aid, a in self._achievements.items()
            }
        }

    def load_from_save(self, save_data: Dict) -> None:
        """Load from save data"""
        unlocks_data = save_data.get('unlocks', {})
        for uid, data in unlocks_data.items():
            if uid in self._unlocks:
                self._unlocks[uid].unlocked = data.get('unlocked', False)
                self._unlocks[uid].unlocked_at = data.get('unlocked_at')

        achievements_data = save_data.get('achievements', {})
        for aid, data in achievements_data.items():
            if aid in self._achievements:
                self._achievements[aid].earned = data.get('earned', False)
                self._achievements[aid].earned_at = data.get('earned_at')

        logger.info(f"Loaded progression: {len(self.get_unlocked())} unlocks, {len(self.get_earned_achievements())} achievements")


# Global progression manager instance
_progression_manager: Optional[ProgressionManager] = None

def get_progression() -> ProgressionManager:
    """Get or create global progression manager"""
    global _progression_manager
    if _progression_manager is None:
        _progression_manager = ProgressionManager()
    return _progression_manager
