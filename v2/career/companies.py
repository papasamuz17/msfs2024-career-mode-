"""
Company Reputation System for V2
Manages airline companies, reputation levels, and mission multipliers
"""

import json
import logging
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Companies")


class ReputationLevel(Enum):
    """Reputation level thresholds"""
    BLACKLISTED = "Blacklisted"    # < 20
    POOR = "Poor"                   # 20-39
    NEUTRAL = "Neutral"             # 40-59
    GOOD = "Good"                   # 60-79
    EXCELLENT = "Excellent"         # 80-94
    ELITE = "Elite"                 # 95-100


# Reputation level bonuses
REPUTATION_MULTIPLIERS = {
    ReputationLevel.BLACKLISTED: 0.0,    # Can't work for them
    ReputationLevel.POOR: 0.8,            # 20% penalty
    ReputationLevel.NEUTRAL: 1.0,         # Base rate
    ReputationLevel.GOOD: 1.15,           # 15% bonus
    ReputationLevel.EXCELLENT: 1.30,      # 30% bonus
    ReputationLevel.ELITE: 1.50           # 50% bonus
}


@dataclass
class Company:
    """Airline company with reputation tracking"""

    id: str
    name: str
    short_name: str
    hub_icao: str
    country: str
    reputation: float = 50.0
    missions_completed: int = 0
    missions_failed: int = 0
    total_earnings: float = 0.0
    preferred_aircraft: List[str] = field(default_factory=list)
    description: str = ""

    @property
    def reputation_level(self) -> ReputationLevel:
        """Get current reputation level"""
        if self.reputation < 20:
            return ReputationLevel.BLACKLISTED
        elif self.reputation < 40:
            return ReputationLevel.POOR
        elif self.reputation < 60:
            return ReputationLevel.NEUTRAL
        elif self.reputation < 80:
            return ReputationLevel.GOOD
        elif self.reputation < 95:
            return ReputationLevel.EXCELLENT
        else:
            return ReputationLevel.ELITE

    @property
    def pay_multiplier(self) -> float:
        """Get pay multiplier based on reputation"""
        return REPUTATION_MULTIPLIERS[self.reputation_level]

    @property
    def can_work(self) -> bool:
        """Check if pilot can work for this company"""
        return self.reputation >= 20

    def add_reputation(self, amount: float) -> float:
        """Add reputation (positive or negative)"""
        old_rep = self.reputation
        self.reputation = max(0, min(100, self.reputation + amount))

        # Check for level change
        old_level = self._get_level_for_value(old_rep)
        new_level = self.reputation_level

        if old_level != new_level:
            logger.info(f"{self.name}: Reputation level changed to {new_level.value}")

        return self.reputation

    def complete_mission(self, earnings: float, performance_score: float = 1.0) -> float:
        """
        Record a completed mission

        Args:
            earnings: Mission earnings
            performance_score: 0.0-1.0 score for mission performance

        Returns:
            Reputation change
        """
        self.missions_completed += 1
        self.total_earnings += earnings

        # Reputation gain based on performance
        # Perfect mission: +2 rep, poor mission: +0.5 rep
        rep_gain = 0.5 + (performance_score * 1.5)
        self.add_reputation(rep_gain)

        logger.debug(f"{self.name}: Mission completed, +{rep_gain:.1f} rep (now {self.reputation:.1f})")
        return rep_gain

    def fail_mission(self, reason: str = "unknown") -> float:
        """
        Record a failed mission

        Args:
            reason: Failure reason

        Returns:
            Reputation change (negative)
        """
        self.missions_failed += 1

        # Reputation loss based on failure type
        rep_loss = -5.0
        if reason == "crash":
            rep_loss = -15.0
        elif reason == "abandoned":
            rep_loss = -10.0
        elif reason == "timeout":
            rep_loss = -3.0

        self.add_reputation(rep_loss)

        logger.warning(f"{self.name}: Mission failed ({reason}), {rep_loss:.1f} rep (now {self.reputation:.1f})")
        return rep_loss

    def _get_level_for_value(self, value: float) -> ReputationLevel:
        """Get reputation level for a specific value"""
        if value < 20:
            return ReputationLevel.BLACKLISTED
        elif value < 40:
            return ReputationLevel.POOR
        elif value < 60:
            return ReputationLevel.NEUTRAL
        elif value < 80:
            return ReputationLevel.GOOD
        elif value < 95:
            return ReputationLevel.EXCELLENT
        else:
            return ReputationLevel.ELITE

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'reputation': self.reputation,
            'missions_completed': self.missions_completed,
            'missions_failed': self.missions_failed,
            'total_earnings': self.total_earnings
        }

    def load_from_dict(self, data: Dict) -> None:
        """Load saved data"""
        self.reputation = data.get('reputation', 50.0)
        self.missions_completed = data.get('missions_completed', 0)
        self.missions_failed = data.get('missions_failed', 0)
        self.total_earnings = data.get('total_earnings', 0.0)


# Default companies
DEFAULT_COMPANIES = [
    Company(
        id="air_france",
        name="Air France",
        short_name="AFR",
        hub_icao="LFPG",
        country="FR",
        preferred_aircraft=["jet", "heavy_jet"],
        description="Compagnie nationale francaise"
    ),
    Company(
        id="lufthansa",
        name="Lufthansa",
        short_name="DLH",
        hub_icao="EDDF",
        country="DE",
        preferred_aircraft=["jet", "heavy_jet", "turboprop"],
        description="Compagnie allemande premium"
    ),
    Company(
        id="british_airways",
        name="British Airways",
        short_name="BAW",
        hub_icao="EGLL",
        country="GB",
        preferred_aircraft=["jet", "heavy_jet"],
        description="Compagnie britannique historique"
    ),
    Company(
        id="easyjet",
        name="easyJet",
        short_name="EZY",
        hub_icao="EGKK",
        country="GB",
        preferred_aircraft=["jet"],
        description="Low-cost europeenne"
    ),
    Company(
        id="private_charter",
        name="Private Charter",
        short_name="PVT",
        hub_icao="LFPB",
        country="FR",
        preferred_aircraft=["light_jet", "turboprop", "twin_piston"],
        description="Vols prives et business aviation"
    ),
    Company(
        id="cargo_express",
        name="Cargo Express",
        short_name="CGX",
        hub_icao="LFLL",
        country="FR",
        preferred_aircraft=["turboprop", "jet"],
        description="Fret et courrier express"
    ),
    Company(
        id="flight_school",
        name="Flying Academy",
        short_name="FLY",
        hub_icao="LFOB",
        country="FR",
        preferred_aircraft=["light_piston", "twin_piston"],
        description="Ecole de pilotage - missions d'entrainement"
    )
]


class CompanyManager:
    """Manages all companies and their reputations"""

    def __init__(self):
        self._companies: Dict[str, Company] = {}
        self._initialize_companies()

    def _initialize_companies(self) -> None:
        """Initialize default companies"""
        for company in DEFAULT_COMPANIES:
            self._companies[company.id] = company

    def get_company(self, company_id: str) -> Optional[Company]:
        """Get company by ID"""
        return self._companies.get(company_id)

    def get_all_companies(self) -> List[Company]:
        """Get all companies"""
        return list(self._companies.values())

    def get_available_companies(self) -> List[Company]:
        """Get companies the pilot can work for"""
        return [c for c in self._companies.values() if c.can_work]

    def get_best_company(self) -> Optional[Company]:
        """Get company with highest reputation"""
        available = self.get_available_companies()
        if not available:
            return None
        return max(available, key=lambda c: c.reputation)

    def get_companies_for_aircraft(self, aircraft_category: str) -> List[Company]:
        """Get companies that use a specific aircraft type"""
        return [
            c for c in self._companies.values()
            if aircraft_category in c.preferred_aircraft and c.can_work
        ]

    def select_random_company(self, aircraft_category: str = None) -> Optional[Company]:
        """Select a random available company"""
        import random

        if aircraft_category:
            candidates = self.get_companies_for_aircraft(aircraft_category)
        else:
            candidates = self.get_available_companies()

        if not candidates:
            return None

        # Weight by reputation (higher rep = more likely)
        weights = [c.reputation for c in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    def load_from_save(self, save_data: Dict) -> None:
        """Load company data from save file"""
        companies_data = save_data.get('companies', {})

        for company_id, company_save in companies_data.items():
            if company_id in self._companies:
                self._companies[company_id].load_from_dict(company_save)

        logger.info(f"Loaded {len(companies_data)} company reputations")

    def to_save_dict(self) -> Dict:
        """Convert to save format"""
        return {
            company_id: company.to_dict()
            for company_id, company in self._companies.items()
        }

    def get_stats(self) -> Dict:
        """Get overall company statistics"""
        total_missions = sum(c.missions_completed for c in self._companies.values())
        total_earnings = sum(c.total_earnings for c in self._companies.values())
        avg_reputation = sum(c.reputation for c in self._companies.values()) / len(self._companies)

        return {
            'total_companies': len(self._companies),
            'available_companies': len(self.get_available_companies()),
            'total_missions': total_missions,
            'total_earnings': total_earnings,
            'average_reputation': avg_reputation,
            'best_company': self.get_best_company().name if self.get_best_company() else None
        }


# Global company manager instance
_company_manager: Optional[CompanyManager] = None

def get_company_manager() -> CompanyManager:
    """Get or create global company manager"""
    global _company_manager
    if _company_manager is None:
        _company_manager = CompanyManager()
    return _company_manager
