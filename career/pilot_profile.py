"""
Pilot Profile Management for V2
Handles pilot licenses, flight hours, ratings, and achievements
"""

import json
import logging
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("MissionGenerator.Pilot")


class License(Enum):
    """Pilot license types"""
    STUDENT = "Student"
    PPL = "PPL"      # Private Pilot License
    CPL = "CPL"      # Commercial Pilot License
    ATPL = "ATPL"    # Airline Transport Pilot License


class Rating(Enum):
    """Additional ratings"""
    IR = "IR"              # Instrument Rating
    MEP = "MEP"            # Multi-Engine Piston
    MET = "MET"            # Multi-Engine Turbine
    TYPE_A320 = "A320"     # Type rating A320
    TYPE_737 = "737"       # Type rating 737
    TYPE_747 = "747"       # Type rating 747
    HELICOPTER = "HELI"    # Helicopter rating


# License requirements
LICENSE_REQUIREMENTS = {
    License.STUDENT: {
        'total_hours': 0,
        'previous_license': None,
        'required_categories': {}
    },
    License.PPL: {
        'total_hours': 40,
        'previous_license': License.STUDENT,
        'required_categories': {
            'light_piston': 35
        }
    },
    License.CPL: {
        'total_hours': 200,
        'previous_license': License.PPL,
        'required_categories': {
            'light_piston': 100,
            'twin_piston': 20
        }
    },
    License.ATPL: {
        'total_hours': 1500,
        'previous_license': License.CPL,
        'required_categories': {
            'turboprop': 100,
            'jet': 200
        }
    }
}

# Aircraft categories hierarchy
AIRCRAFT_CATEGORIES = [
    'light_piston',
    'twin_piston',
    'single_turboprop',
    'turboprop',
    'light_jet',
    'jet',
    'heavy_jet',
    'helicopter'
]


@dataclass
class PilotProfile:
    """Complete pilot profile with all career data"""

    name: str = "Pilote"
    license: License = License.STUDENT
    total_hours: float = 0.0
    hours_by_category: Dict[str, float] = field(default_factory=lambda: {
        cat: 0.0 for cat in AIRCRAFT_CATEGORIES
    })
    ratings: Set[Rating] = field(default_factory=set)
    achievements: List[str] = field(default_factory=list)
    home_base: str = "LFPG"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_flight: Optional[str] = None

    # Statistics
    total_landings: int = 0
    perfect_landings: int = 0  # < 100 fpm
    total_distance_nm: float = 0.0
    longest_flight_nm: float = 0.0

    def add_flight_time(self, hours: float, category: str) -> None:
        """Add flight time to profile"""
        self.total_hours += hours

        if category in self.hours_by_category:
            self.hours_by_category[category] += hours
        else:
            self.hours_by_category[category] = hours

        self.last_flight = datetime.now().isoformat()
        logger.debug(f"Added {hours:.2f}h to {category}, total: {self.total_hours:.1f}h")

    def add_landing(self, vertical_speed_fpm: float) -> None:
        """Record a landing"""
        self.total_landings += 1
        if abs(vertical_speed_fpm) < 100:
            self.perfect_landings += 1
            logger.info(f"Perfect landing recorded! ({vertical_speed_fpm:.0f} fpm)")

    def add_distance(self, distance_nm: float) -> None:
        """Record flight distance"""
        self.total_distance_nm += distance_nm
        if distance_nm > self.longest_flight_nm:
            self.longest_flight_nm = distance_nm

    def add_achievement(self, achievement: str) -> bool:
        """Add achievement if not already earned"""
        if achievement not in self.achievements:
            self.achievements.append(achievement)
            logger.info(f"Achievement unlocked: {achievement}")
            return True
        return False

    def add_rating(self, rating: Rating) -> bool:
        """Add a rating to the pilot"""
        if rating not in self.ratings:
            self.ratings.add(rating)
            logger.info(f"Rating added: {rating.value}")
            return True
        return False

    def can_upgrade_license(self) -> Optional[License]:
        """Check if pilot can upgrade to next license"""
        # Determine next license level
        license_order = [License.STUDENT, License.PPL, License.CPL, License.ATPL]
        current_idx = license_order.index(self.license)

        if current_idx >= len(license_order) - 1:
            return None  # Already at max

        next_license = license_order[current_idx + 1]
        requirements = LICENSE_REQUIREMENTS[next_license]

        # Check total hours
        if self.total_hours < requirements['total_hours']:
            return None

        # Check category hours
        for category, required_hours in requirements['required_categories'].items():
            if self.hours_by_category.get(category, 0) < required_hours:
                return None

        return next_license

    def upgrade_license(self) -> bool:
        """Attempt to upgrade to next license"""
        next_license = self.can_upgrade_license()
        if next_license:
            old_license = self.license
            self.license = next_license
            logger.info(f"License upgraded: {old_license.value} -> {next_license.value}")
            self.add_achievement(f"License_{next_license.value}")
            return True
        return False

    def get_available_categories(self) -> List[str]:
        """Get aircraft categories available based on current license"""
        available = []

        if self.license == License.STUDENT:
            available = ['light_piston']
        elif self.license == License.PPL:
            available = ['light_piston', 'twin_piston', 'helicopter']
        elif self.license == License.CPL:
            available = ['light_piston', 'twin_piston', 'single_turboprop',
                        'turboprop', 'helicopter']
        elif self.license == License.ATPL:
            available = AIRCRAFT_CATEGORIES.copy()

        # Add type-rated aircraft
        if Rating.TYPE_A320 in self.ratings:
            if 'jet' not in available:
                available.append('jet')
        if Rating.TYPE_747 in self.ratings:
            if 'heavy_jet' not in available:
                available.append('heavy_jet')

        return available

    def can_fly_category(self, category: str) -> bool:
        """Check if pilot can fly a specific aircraft category"""
        return category in self.get_available_categories()

    def get_next_license_progress(self) -> Dict:
        """Get progress towards next license"""
        license_order = [License.STUDENT, License.PPL, License.CPL, License.ATPL]
        current_idx = license_order.index(self.license)

        if current_idx >= len(license_order) - 1:
            return {
                'next_license': None,
                'progress_percent': 100,
                'requirements_met': True
            }

        next_license = license_order[current_idx + 1]
        requirements = LICENSE_REQUIREMENTS[next_license]

        # Calculate progress
        hours_progress = min(100, (self.total_hours / requirements['total_hours']) * 100)

        category_progress = {}
        for category, required in requirements['required_categories'].items():
            current = self.hours_by_category.get(category, 0)
            category_progress[category] = {
                'current': current,
                'required': required,
                'percent': min(100, (current / required) * 100)
            }

        overall_progress = hours_progress
        if category_progress:
            cat_percents = [cp['percent'] for cp in category_progress.values()]
            overall_progress = (hours_progress + sum(cat_percents)) / (1 + len(cat_percents))

        return {
            'next_license': next_license.value,
            'total_hours_required': requirements['total_hours'],
            'total_hours_current': self.total_hours,
            'hours_progress': hours_progress,
            'category_requirements': category_progress,
            'progress_percent': overall_progress,
            'requirements_met': overall_progress >= 100
        }

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'license': self.license.value,
            'total_hours': self.total_hours,
            'hours_by_category': self.hours_by_category,
            'ratings': [r.value for r in self.ratings],
            'achievements': self.achievements,
            'home_base': self.home_base,
            'created_at': self.created_at,
            'last_flight': self.last_flight,
            'total_landings': self.total_landings,
            'perfect_landings': self.perfect_landings,
            'total_distance_nm': self.total_distance_nm,
            'longest_flight_nm': self.longest_flight_nm
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'PilotProfile':
        """Create from dictionary"""
        profile = cls()
        profile.name = data.get('name', 'Pilote')
        profile.license = License(data.get('license', 'Student'))
        profile.total_hours = data.get('total_hours', 0.0)
        profile.hours_by_category = data.get('hours_by_category', {
            cat: 0.0 for cat in AIRCRAFT_CATEGORIES
        })
        profile.ratings = {Rating(r) for r in data.get('ratings', [])}
        profile.achievements = data.get('achievements', [])
        profile.home_base = data.get('home_base', 'LFPG')
        profile.created_at = data.get('created_at', datetime.now().isoformat())
        profile.last_flight = data.get('last_flight')
        profile.total_landings = data.get('total_landings', 0)
        profile.perfect_landings = data.get('perfect_landings', 0)
        profile.total_distance_nm = data.get('total_distance_nm', 0.0)
        profile.longest_flight_nm = data.get('longest_flight_nm', 0.0)
        return profile


# Global pilot instance
_pilot_profile: Optional[PilotProfile] = None

def get_pilot() -> PilotProfile:
    """Get or create global pilot profile"""
    global _pilot_profile
    if _pilot_profile is None:
        _pilot_profile = PilotProfile()
    return _pilot_profile

def set_pilot(profile: PilotProfile) -> None:
    """Set global pilot profile"""
    global _pilot_profile
    _pilot_profile = profile

def load_pilot(save_data: Dict) -> PilotProfile:
    """Load pilot from save data"""
    global _pilot_profile
    pilot_data = save_data.get('pilot', {})
    _pilot_profile = PilotProfile.from_dict(pilot_data)
    return _pilot_profile
