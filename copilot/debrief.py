"""
Flight Debriefing System for V2 Copilot
Post-flight analysis and feedback
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Copilot.Debrief")


@dataclass
class FlightMetrics:
    """Collected flight metrics for debriefing"""
    # Duration
    total_time_minutes: float = 0.0
    time_on_ground: float = 0.0
    time_airborne: float = 0.0

    # Distance
    total_distance_nm: float = 0.0
    direct_distance_nm: float = 0.0

    # Performance
    max_altitude_ft: float = 0.0
    cruise_altitude_ft: float = 0.0
    max_speed_kts: float = 0.0
    average_speed_kts: float = 0.0

    # Landing
    landing_vs_fpm: float = 0.0
    landing_g_force: float = 0.0
    touchdown_distance_ft: float = 0.0
    centerline_deviation_ft: float = 0.0

    # Errors and events
    errors_detected: int = 0
    warnings_triggered: int = 0
    constraints_violated: int = 0
    go_arounds: int = 0

    # Fuel
    fuel_consumed_gal: float = 0.0
    fuel_efficiency_nm_per_gal: float = 0.0

    # Comfort (if passengers)
    passenger_comfort_score: float = 100.0


@dataclass
class DebriefSection:
    """Single section of the debrief"""
    title: str
    content: str
    rating: str = ""            # Excellent, Good, Fair, Poor
    score: float = 100.0        # 0-100
    feedback: List[str] = field(default_factory=list)


@dataclass
class FlightDebrief:
    """Complete flight debrief"""
    # Flight info
    flight_date: str
    departure_icao: str
    arrival_icao: str
    aircraft: str

    # Sections
    sections: List[DebriefSection] = field(default_factory=list)

    # Overall
    overall_score: float = 0.0
    overall_rating: str = ""
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)

    # Voice message
    voice_debrief: str = ""


class DebriefManager:
    """Manages flight debriefing"""

    def __init__(self):
        self._current_metrics = FlightMetrics()
        self._debriefs: List[FlightDebrief] = []
        self._recording = False

    def start_recording(self) -> None:
        """Start recording flight metrics"""
        self._current_metrics = FlightMetrics()
        self._recording = True
        logger.info("Debrief recording started")

    def stop_recording(self) -> None:
        """Stop recording flight metrics"""
        self._recording = False
        logger.info("Debrief recording stopped")

    def update_metrics(self, **kwargs) -> None:
        """Update metrics during flight"""
        if not self._recording:
            return

        for key, value in kwargs.items():
            if hasattr(self._current_metrics, key):
                setattr(self._current_metrics, key, value)

    def record_landing(self, vs_fpm: float, g_force: float = 1.0,
                      centerline_ft: float = 0.0, touchdown_ft: float = 0.0) -> None:
        """Record landing metrics"""
        self._current_metrics.landing_vs_fpm = vs_fpm
        self._current_metrics.landing_g_force = g_force
        self._current_metrics.centerline_deviation_ft = centerline_ft
        self._current_metrics.touchdown_distance_ft = touchdown_ft

    def record_error(self) -> None:
        """Record a detected error"""
        self._current_metrics.errors_detected += 1

    def record_warning(self) -> None:
        """Record a warning"""
        self._current_metrics.warnings_triggered += 1

    def record_go_around(self) -> None:
        """Record a go-around"""
        self._current_metrics.go_arounds += 1

    def generate_debrief(self, departure_icao: str, arrival_icao: str,
                        aircraft: str) -> FlightDebrief:
        """
        Generate flight debrief from collected metrics

        Args:
            departure_icao: Departure airport
            arrival_icao: Arrival airport
            aircraft: Aircraft used

        Returns:
            Complete FlightDebrief
        """
        metrics = self._current_metrics

        debrief = FlightDebrief(
            flight_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            departure_icao=departure_icao,
            arrival_icao=arrival_icao,
            aircraft=aircraft
        )

        # ==================== LANDING SECTION ====================
        landing_section = self._evaluate_landing(metrics)
        debrief.sections.append(landing_section)

        # ==================== FLIGHT MANAGEMENT SECTION ====================
        management_section = self._evaluate_flight_management(metrics)
        debrief.sections.append(management_section)

        # ==================== SAFETY SECTION ====================
        safety_section = self._evaluate_safety(metrics)
        debrief.sections.append(safety_section)

        # ==================== EFFICIENCY SECTION ====================
        efficiency_section = self._evaluate_efficiency(metrics)
        debrief.sections.append(efficiency_section)

        # ==================== PASSENGER COMFORT (if applicable) ====================
        if metrics.passenger_comfort_score < 100:
            comfort_section = self._evaluate_comfort(metrics)
            debrief.sections.append(comfort_section)

        # ==================== OVERALL SCORE ====================
        section_scores = [s.score for s in debrief.sections]
        debrief.overall_score = sum(section_scores) / len(section_scores) if section_scores else 0

        if debrief.overall_score >= 90:
            debrief.overall_rating = "Excellent"
        elif debrief.overall_score >= 75:
            debrief.overall_rating = "Good"
        elif debrief.overall_score >= 60:
            debrief.overall_rating = "Fair"
        else:
            debrief.overall_rating = "Needs Improvement"

        # Generate summary
        debrief.summary = self._generate_summary(debrief)
        debrief.recommendations = self._generate_recommendations(debrief)
        debrief.voice_debrief = self._generate_voice_debrief(debrief)

        self._debriefs.append(debrief)
        logger.info(f"Debrief generated: {debrief.overall_rating} ({debrief.overall_score:.1f}%)")

        return debrief

    def _evaluate_landing(self, metrics: FlightMetrics) -> DebriefSection:
        """Evaluate landing performance"""
        vs = abs(metrics.landing_vs_fpm)
        centerline = abs(metrics.centerline_deviation_ft)

        feedback = []
        score = 100.0

        # VS scoring
        if vs < 60:
            feedback.append("Butter landing! Excellent touchdown.")
            rating = "Excellent"
        elif vs < 100:
            feedback.append("Very smooth landing.")
            rating = "Excellent"
        elif vs < 150:
            feedback.append("Good landing, nicely controlled.")
            rating = "Good"
            score -= 10
        elif vs < 200:
            feedback.append("Normal landing.")
            rating = "Good"
            score -= 20
        elif vs < 300:
            feedback.append("Firm landing, consider a softer flare.")
            rating = "Fair"
            score -= 35
        elif vs < 500:
            feedback.append("Hard landing. Work on flare timing.")
            rating = "Poor"
            score -= 50
        else:
            feedback.append("Very hard landing! Risk of damage.")
            rating = "Poor"
            score -= 70

        # Centerline scoring
        if centerline < 10:
            feedback.append("Excellent centerline tracking.")
        elif centerline < 30:
            feedback.append("Good runway alignment.")
        elif centerline < 50:
            score -= 10
            feedback.append("Minor centerline deviation.")
        else:
            score -= 20
            feedback.append("Significant centerline deviation - practice alignment.")

        return DebriefSection(
            title="Landing Performance",
            content=f"Touchdown at {vs:.0f} fpm, {centerline:.0f} ft from centerline",
            rating=rating,
            score=max(0, score),
            feedback=feedback
        )

    def _evaluate_flight_management(self, metrics: FlightMetrics) -> DebriefSection:
        """Evaluate overall flight management"""
        feedback = []
        score = 100.0

        # Constraint violations
        if metrics.constraints_violated == 0:
            feedback.append("All constraints respected throughout flight.")
        elif metrics.constraints_violated < 3:
            score -= metrics.constraints_violated * 10
            feedback.append(f"{metrics.constraints_violated} minor constraint violation(s).")
        else:
            score -= min(50, metrics.constraints_violated * 10)
            feedback.append(f"{metrics.constraints_violated} constraint violations - needs improvement.")

        # Go-arounds
        if metrics.go_arounds > 0:
            feedback.append(f"{metrics.go_arounds} go-around(s) executed.")
            if metrics.go_arounds == 1:
                feedback.append("Good decision making on the go-around.")
            else:
                score -= (metrics.go_arounds - 1) * 15
                feedback.append("Multiple go-arounds suggest approach instability issues.")

        rating = "Excellent" if score >= 85 else "Good" if score >= 70 else "Fair" if score >= 50 else "Poor"

        return DebriefSection(
            title="Flight Management",
            content=f"Flight duration: {metrics.total_time_minutes:.0f} min",
            rating=rating,
            score=max(0, score),
            feedback=feedback
        )

    def _evaluate_safety(self, metrics: FlightMetrics) -> DebriefSection:
        """Evaluate safety record"""
        feedback = []
        score = 100.0

        # Errors
        if metrics.errors_detected == 0:
            feedback.append("No safety errors detected.")
        else:
            score -= metrics.errors_detected * 15
            feedback.append(f"{metrics.errors_detected} safety error(s) detected - review procedures.")

        # Warnings
        if metrics.warnings_triggered == 0:
            feedback.append("No warnings triggered.")
        elif metrics.warnings_triggered < 3:
            score -= metrics.warnings_triggered * 5
            feedback.append(f"{metrics.warnings_triggered} warning(s) triggered.")
        else:
            score -= min(30, metrics.warnings_triggered * 5)
            feedback.append(f"Multiple warnings ({metrics.warnings_triggered}) - maintain better awareness.")

        rating = "Excellent" if score >= 90 else "Good" if score >= 75 else "Fair" if score >= 50 else "Poor"

        return DebriefSection(
            title="Safety",
            content=f"Errors: {metrics.errors_detected}, Warnings: {metrics.warnings_triggered}",
            rating=rating,
            score=max(0, score),
            feedback=feedback
        )

    def _evaluate_efficiency(self, metrics: FlightMetrics) -> DebriefSection:
        """Evaluate fuel and route efficiency"""
        feedback = []
        score = 100.0

        # Fuel efficiency
        if metrics.fuel_consumed_gal > 0 and metrics.total_distance_nm > 0:
            nm_per_gal = metrics.total_distance_nm / metrics.fuel_consumed_gal
            metrics.fuel_efficiency_nm_per_gal = nm_per_gal

            if nm_per_gal > 4:
                feedback.append(f"Excellent fuel efficiency: {nm_per_gal:.1f} nm/gal")
            elif nm_per_gal > 3:
                feedback.append(f"Good fuel efficiency: {nm_per_gal:.1f} nm/gal")
            elif nm_per_gal > 2:
                feedback.append(f"Average fuel efficiency: {nm_per_gal:.1f} nm/gal")
                score -= 10
            else:
                feedback.append(f"Poor fuel efficiency: {nm_per_gal:.1f} nm/gal - consider power settings")
                score -= 25

        # Route efficiency (direct vs actual)
        if metrics.direct_distance_nm > 0 and metrics.total_distance_nm > 0:
            efficiency_ratio = metrics.direct_distance_nm / metrics.total_distance_nm
            if efficiency_ratio > 0.95:
                feedback.append("Very direct routing.")
            elif efficiency_ratio > 0.85:
                feedback.append("Reasonably efficient routing.")
            else:
                score -= 15
                feedback.append("Significant deviation from direct route.")

        rating = "Excellent" if score >= 90 else "Good" if score >= 75 else "Fair" if score >= 50 else "Poor"

        return DebriefSection(
            title="Efficiency",
            content=f"Fuel: {metrics.fuel_consumed_gal:.1f} gal for {metrics.total_distance_nm:.0f} nm",
            rating=rating,
            score=max(0, score),
            feedback=feedback
        )

    def _evaluate_comfort(self, metrics: FlightMetrics) -> DebriefSection:
        """Evaluate passenger comfort"""
        score = metrics.passenger_comfort_score
        feedback = []

        if score >= 90:
            feedback.append("Passengers are very satisfied with the flight.")
            rating = "Excellent"
        elif score >= 70:
            feedback.append("Passengers are satisfied overall.")
            rating = "Good"
        elif score >= 50:
            feedback.append("Some passenger discomfort reported.")
            rating = "Fair"
        else:
            feedback.append("Significant passenger complaints - smoother flying needed.")
            rating = "Poor"

        return DebriefSection(
            title="Passenger Comfort",
            content=f"Comfort score: {score:.0f}%",
            rating=rating,
            score=score,
            feedback=feedback
        )

    def _generate_summary(self, debrief: FlightDebrief) -> str:
        """Generate text summary"""
        return (f"Vol {debrief.departure_icao} vers {debrief.arrival_icao} "
               f"complete avec une note de {debrief.overall_score:.0f}% ({debrief.overall_rating}).")

    def _generate_recommendations(self, debrief: FlightDebrief) -> List[str]:
        """Generate recommendations based on debrief"""
        recommendations = []

        for section in debrief.sections:
            if section.score < 70:
                if "Landing" in section.title:
                    recommendations.append("Practice smooth flare technique on short flights.")
                elif "Safety" in section.title:
                    recommendations.append("Review standard operating procedures and checklists.")
                elif "Efficiency" in section.title:
                    recommendations.append("Review power settings for optimal fuel consumption.")
                elif "Comfort" in section.title:
                    recommendations.append("Practice smoother control inputs, especially during turbulence.")

        if not recommendations:
            recommendations.append("Maintain current performance standards.")

        return recommendations

    def _generate_voice_debrief(self, debrief: FlightDebrief) -> str:
        """Generate voice debrief message"""
        parts = [
            f"Debriefing du vol {debrief.departure_icao} vers {debrief.arrival_icao}.",
            f"Note globale: {debrief.overall_score:.0f} pourcent, {debrief.overall_rating}."
        ]

        # Landing feedback
        landing = next((s for s in debrief.sections if "Landing" in s.title), None)
        if landing and landing.feedback:
            parts.append(landing.feedback[0])

        # Main recommendation
        if debrief.recommendations:
            parts.append(f"Recommandation: {debrief.recommendations[0]}")

        return " ".join(parts)

    def get_last_debrief(self) -> Optional[FlightDebrief]:
        """Get the most recent debrief"""
        return self._debriefs[-1] if self._debriefs else None

    def get_stats(self) -> Dict:
        """Get debriefing statistics"""
        if not self._debriefs:
            return {'total_debriefs': 0}

        scores = [d.overall_score for d in self._debriefs]
        return {
            'total_debriefs': len(self._debriefs),
            'average_score': sum(scores) / len(scores),
            'best_score': max(scores),
            'worst_score': min(scores)
        }


# Global debrief manager instance
_debrief_manager: Optional[DebriefManager] = None

def get_debrief_manager() -> DebriefManager:
    """Get or create global debrief manager"""
    global _debrief_manager
    if _debrief_manager is None:
        _debrief_manager = DebriefManager()
    return _debrief_manager
