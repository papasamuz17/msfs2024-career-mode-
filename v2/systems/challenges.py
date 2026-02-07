"""
Landing Challenges System for V2
Special landing challenges with scoring
"""

import logging
import random
from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Challenges")


class ChallengeType(Enum):
    """Types of landing challenges"""
    BUTTER = "butter"              # Smoothest possible landing
    SHORT_FIELD = "short_field"    # Land as short as possible
    CROSSWIND = "crosswind"        # Heavy crosswind landing
    NIGHT = "night"                # Night landing with limited visibility
    LOW_VISIBILITY = "low_vis"     # ILS approach in low visibility
    GUSTY = "gusty"                # Landing in gusty conditions
    MOUNTAIN = "mountain"          # High altitude airport
    CARRIER = "carrier"            # Precision landing (simulated carrier)
    PATTERN = "pattern"            # Fly perfect traffic pattern


class ChallengeDifficulty(Enum):
    """Challenge difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


@dataclass
class ChallengeResult:
    """Result of a challenge attempt"""
    challenge_id: str
    challenge_type: ChallengeType
    score: float               # 0-100
    rating: str                # S, A, B, C, D, F
    metrics: Dict              # Specific metrics achieved
    bonus_earned: float        # Bonus money earned
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    # V2 Enhanced metrics
    touchdown_velocity_fps: float = 0.0  # From SimConnect PLANE_TOUCHDOWN_NORMAL_VELOCITY
    g_force_at_landing: float = 1.0      # From SimConnect G_FORCE at touchdown

    @property
    def passed(self) -> bool:
        return self.score >= 60


@dataclass
class Challenge:
    """A landing challenge"""
    id: str
    challenge_type: ChallengeType
    difficulty: ChallengeDifficulty
    name: str
    description: str
    airport_icao: str
    runway: str

    # Requirements
    target_vs_fpm: float = 150.0       # Target vertical speed
    max_vs_fpm: float = 300.0          # Maximum allowed
    target_centerline_ft: float = 50   # Target from centerline
    max_centerline_ft: float = 150     # Maximum from centerline
    target_touchdown_ft: float = 500   # Target from threshold
    max_touchdown_ft: float = 1500     # Maximum from threshold

    # Conditions
    wind_speed_kts: int = 0
    wind_direction: int = 0
    crosswind_component: int = 0
    visibility_sm: float = 10.0
    is_night: bool = False

    # Scoring
    base_reward: float = 100.0
    difficulty_multiplier: float = 1.0

    # State
    active: bool = False
    started_at: Optional[str] = None
    completed: bool = False
    result: Optional[ChallengeResult] = None

    def start(self) -> None:
        """Start the challenge"""
        self.active = True
        self.started_at = datetime.now().isoformat()
        self.completed = False
        self.result = None
        logger.info(f"Challenge started: {self.name}")

    def calculate_score(self, actual_vs: float, actual_centerline: float,
                       actual_touchdown: float, additional_metrics: Dict = None,
                       # V2 Enhanced parameters
                       touchdown_velocity_fps: float = None,
                       g_force: float = None) -> ChallengeResult:
        """
        Calculate challenge score based on landing metrics

        V2 ENHANCED: Uses SimConnect touchdown velocity and G-force for
        more objective scoring when available.

        Args:
            actual_vs: Actual vertical speed at touchdown (fpm, positive = down)
            actual_centerline: Distance from centerline (ft)
            actual_touchdown: Distance from threshold (ft)
            additional_metrics: Type-specific metrics
            touchdown_velocity_fps: SimConnect PLANE_TOUCHDOWN_NORMAL_VELOCITY (ft/s)
            g_force: SimConnect G_FORCE at touchdown

        Returns:
            ChallengeResult with score and details
        """
        score = 100.0
        metrics = {
            'vertical_speed': actual_vs,
            'centerline_offset': actual_centerline,
            'touchdown_point': actual_touchdown
        }

        if additional_metrics:
            metrics.update(additional_metrics)

        # V2: Add enhanced metrics if available
        if touchdown_velocity_fps is not None:
            metrics['touchdown_velocity_fps'] = touchdown_velocity_fps
        if g_force is not None:
            metrics['g_force_at_landing'] = g_force

        # ==================== V2 ENHANCED SCORING ====================

        # V2: Use touchdown_velocity_fps if available (more accurate than VS)
        # Convert to similar scale: 1 ft/s ≈ 60 fpm
        if touchdown_velocity_fps is not None and touchdown_velocity_fps > 0:
            # SimConnect provides touchdown velocity in ft/s
            # Typical butter landing: < 1.5 ft/s (≈90 fpm)
            # Good landing: < 3 ft/s (≈180 fpm)
            # Hard landing: > 5 ft/s (≈300 fpm)
            vs_for_scoring = abs(touchdown_velocity_fps) * 60
        else:
            vs_for_scoring = abs(actual_vs)

        # V2: G-Force bonus/penalty for butter landings
        g_bonus = 0.0
        if g_force is not None:
            if self.challenge_type == ChallengeType.BUTTER:
                # For butter challenge, G-force is crucial
                # Perfect: G < 1.2, Good: G < 1.5, Acceptable: G < 2.0
                if g_force < 1.2:
                    g_bonus = 15  # Excellent - bonus points
                elif g_force < 1.5:
                    g_bonus = 5   # Good
                elif g_force > 2.0:
                    g_bonus = -10 # Hard landing penalty
                elif g_force > 2.5:
                    g_bonus = -20 # Very hard landing
                metrics['g_force_rating'] = 'excellent' if g_force < 1.2 else ('good' if g_force < 1.5 else 'hard')

        # Vertical speed scoring (40% of total)
        vs_abs = vs_for_scoring
        if vs_abs <= self.target_vs_fpm:
            vs_score = 40
        elif vs_abs <= self.max_vs_fpm:
            vs_score = 40 * (1 - (vs_abs - self.target_vs_fpm) / (self.max_vs_fpm - self.target_vs_fpm))
        else:
            vs_score = max(0, 40 - (vs_abs - self.max_vs_fpm) / 10)

        # Centerline scoring (30% of total)
        if actual_centerline <= self.target_centerline_ft:
            cl_score = 30
        elif actual_centerline <= self.max_centerline_ft:
            cl_score = 30 * (1 - (actual_centerline - self.target_centerline_ft) /
                            (self.max_centerline_ft - self.target_centerline_ft))
        else:
            cl_score = max(0, 30 - (actual_centerline - self.max_centerline_ft) / 20)

        # Touchdown point scoring (30% of total)
        if actual_touchdown <= self.target_touchdown_ft:
            td_score = 30
        elif actual_touchdown <= self.max_touchdown_ft:
            td_score = 30 * (1 - (actual_touchdown - self.target_touchdown_ft) /
                            (self.max_touchdown_ft - self.target_touchdown_ft))
        else:
            td_score = max(0, 30 - (actual_touchdown - self.max_touchdown_ft) / 50)

        # Challenge type specific adjustments
        if self.challenge_type == ChallengeType.BUTTER:
            # Butter challenge: VS is 70% of score + G-force bonus
            score = (vs_score * 1.75) + (cl_score * 0.5) + (td_score * 0.5) + g_bonus
        elif self.challenge_type == ChallengeType.SHORT_FIELD:
            # Short field: touchdown point is 60% of score
            score = (vs_score * 0.5) + (cl_score * 0.6) + (td_score * 2.0)
        elif self.challenge_type == ChallengeType.CROSSWIND:
            # Crosswind: centerline is critical
            score = (vs_score * 0.6) + (cl_score * 2.0) + (td_score * 0.4)
        else:
            score = vs_score + cl_score + td_score

        # Clamp score
        score = max(0, min(100, score))

        # Calculate rating
        if score >= 95:
            rating = "S"
        elif score >= 85:
            rating = "A"
        elif score >= 75:
            rating = "B"
        elif score >= 60:
            rating = "C"
        elif score >= 40:
            rating = "D"
        else:
            rating = "F"

        # Calculate bonus
        bonus = 0.0
        if score >= 60:
            bonus = self.base_reward * (score / 100) * self.difficulty_multiplier

        self.result = ChallengeResult(
            challenge_id=self.id,
            challenge_type=self.challenge_type,
            score=score,
            rating=rating,
            metrics=metrics,
            bonus_earned=bonus,
            # V2 Enhanced data
            touchdown_velocity_fps=touchdown_velocity_fps or 0.0,
            g_force_at_landing=g_force or 1.0
        )

        self.completed = True
        self.active = False

        # V2: Log enhanced metrics
        log_msg = f"Challenge completed: {self.name} - Score: {score:.1f} ({rating})"
        if touchdown_velocity_fps is not None:
            log_msg += f" [TD: {touchdown_velocity_fps:.1f}ft/s]"
        if g_force is not None:
            log_msg += f" [G: {g_force:.2f}]"
        logger.info(log_msg)

        return self.result


# Predefined challenges
AVAILABLE_CHALLENGES: List[Challenge] = [
    Challenge(
        id="butter_lfpg",
        challenge_type=ChallengeType.BUTTER,
        difficulty=ChallengeDifficulty.MEDIUM,
        name="Butter Landing - Paris CDG",
        description="Achieve the smoothest possible landing at Paris Charles de Gaulle",
        airport_icao="LFPG",
        runway="27R",
        target_vs_fpm=60,
        max_vs_fpm=150,
        base_reward=150
    ),
    Challenge(
        id="short_field_lfkc",
        challenge_type=ChallengeType.SHORT_FIELD,
        difficulty=ChallengeDifficulty.HARD,
        name="Short Field - Calvi",
        description="Land on the short runway at Calvi in Corsica",
        airport_icao="LFKC",
        runway="18",
        target_touchdown_ft=200,
        max_touchdown_ft=800,
        base_reward=200,
        difficulty_multiplier=1.5
    ),
    Challenge(
        id="crosswind_egll",
        challenge_type=ChallengeType.CROSSWIND,
        difficulty=ChallengeDifficulty.HARD,
        name="Crosswind Landing - Heathrow",
        description="Land at Heathrow with strong crosswind",
        airport_icao="EGLL",
        runway="27L",
        wind_speed_kts=25,
        wind_direction=310,
        crosswind_component=20,
        target_centerline_ft=30,
        max_centerline_ft=100,
        base_reward=250,
        difficulty_multiplier=1.75
    ),
    Challenge(
        id="night_lfmn",
        challenge_type=ChallengeType.NIGHT,
        difficulty=ChallengeDifficulty.MEDIUM,
        name="Night Landing - Nice",
        description="Land at Nice Cote d'Azur at night",
        airport_icao="LFMN",
        runway="04R",
        is_night=True,
        visibility_sm=5.0,
        base_reward=175
    ),
    Challenge(
        id="low_vis_eham",
        challenge_type=ChallengeType.LOW_VISIBILITY,
        difficulty=ChallengeDifficulty.EXPERT,
        name="CAT III - Amsterdam",
        description="CAT III ILS approach in minimum visibility",
        airport_icao="EHAM",
        runway="18R",
        visibility_sm=0.5,
        base_reward=350,
        difficulty_multiplier=2.0
    )
]


class ChallengeManager:
    """Manages landing challenges"""

    def __init__(self):
        self._available_challenges: Dict[str, Challenge] = {}
        self._active_challenge: Optional[Challenge] = None
        self._completed_challenges: List[ChallengeResult] = []
        self._callbacks: List[Callable] = []

        self._initialize_challenges()

    def _initialize_challenges(self) -> None:
        """Initialize available challenges"""
        for challenge in AVAILABLE_CHALLENGES:
            self._available_challenges[challenge.id] = challenge

    def register_callback(self, callback: Callable) -> None:
        """Register callback for challenge events"""
        self._callbacks.append(callback)

    def get_available_challenges(self, difficulty: ChallengeDifficulty = None) -> List[Challenge]:
        """Get available challenges, optionally filtered by difficulty"""
        challenges = list(self._available_challenges.values())
        if difficulty:
            challenges = [c for c in challenges if c.difficulty == difficulty]
        return challenges

    def get_random_challenge(self, difficulty: ChallengeDifficulty = None) -> Optional[Challenge]:
        """Get a random challenge"""
        challenges = self.get_available_challenges(difficulty)
        return random.choice(challenges) if challenges else None

    def start_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Start a specific challenge"""
        if challenge_id not in self._available_challenges:
            logger.warning(f"Challenge not found: {challenge_id}")
            return None

        if self._active_challenge:
            logger.warning("Another challenge is already active")
            return None

        # Create a copy of the challenge for this attempt
        template = self._available_challenges[challenge_id]
        self._active_challenge = Challenge(
            id=template.id,
            challenge_type=template.challenge_type,
            difficulty=template.difficulty,
            name=template.name,
            description=template.description,
            airport_icao=template.airport_icao,
            runway=template.runway,
            target_vs_fpm=template.target_vs_fpm,
            max_vs_fpm=template.max_vs_fpm,
            target_centerline_ft=template.target_centerline_ft,
            max_centerline_ft=template.max_centerline_ft,
            target_touchdown_ft=template.target_touchdown_ft,
            max_touchdown_ft=template.max_touchdown_ft,
            wind_speed_kts=template.wind_speed_kts,
            wind_direction=template.wind_direction,
            crosswind_component=template.crosswind_component,
            visibility_sm=template.visibility_sm,
            is_night=template.is_night,
            base_reward=template.base_reward,
            difficulty_multiplier=template.difficulty_multiplier
        )

        self._active_challenge.start()
        return self._active_challenge

    def complete_challenge(self, vs: float, centerline: float,
                          touchdown: float) -> Optional[ChallengeResult]:
        """Complete the active challenge with landing metrics"""
        if not self._active_challenge:
            logger.warning("No active challenge to complete")
            return None

        result = self._active_challenge.calculate_score(vs, centerline, touchdown)
        self._completed_challenges.append(result)
        self._active_challenge = None

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback("challenge_complete", result)
            except Exception as e:
                logger.error(f"Challenge callback error: {e}")

        return result

    def cancel_challenge(self) -> None:
        """Cancel the active challenge"""
        if self._active_challenge:
            logger.info(f"Challenge cancelled: {self._active_challenge.name}")
            self._active_challenge = None

    @property
    def active_challenge(self) -> Optional[Challenge]:
        return self._active_challenge

    def get_stats(self) -> Dict:
        """Get challenge statistics"""
        if not self._completed_challenges:
            return {
                'total_attempts': 0,
                'passed': 0,
                'average_score': 0,
                'total_bonus': 0
            }

        scores = [r.score for r in self._completed_challenges]
        bonuses = [r.bonus_earned for r in self._completed_challenges]

        return {
            'total_attempts': len(self._completed_challenges),
            'passed': sum(1 for r in self._completed_challenges if r.passed),
            'average_score': sum(scores) / len(scores),
            'best_score': max(scores),
            'total_bonus': sum(bonuses),
            's_ratings': sum(1 for r in self._completed_challenges if r.rating == 'S')
        }

    def get_leaderboard(self, challenge_id: str = None) -> List[ChallengeResult]:
        """Get top results for a challenge"""
        results = self._completed_challenges
        if challenge_id:
            results = [r for r in results if r.challenge_id == challenge_id]
        return sorted(results, key=lambda r: r.score, reverse=True)[:10]


# Global challenge manager instance
_challenge_manager: Optional[ChallengeManager] = None

def get_challenge_manager() -> ChallengeManager:
    """Get or create global challenge manager"""
    global _challenge_manager
    if _challenge_manager is None:
        _challenge_manager = ChallengeManager()
    return _challenge_manager
