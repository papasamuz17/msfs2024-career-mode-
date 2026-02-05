"""
Checkride (Pilot Examination) System for V2
Simulates pilot practical tests for license upgrades
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Checkride")


class CheckrideType(Enum):
    """Types of checkrides"""
    PPL = "ppl"              # Private Pilot License
    CPL = "cpl"              # Commercial Pilot License
    IR = "ir"                # Instrument Rating
    MEP = "mep"              # Multi-Engine Piston
    ATPL = "atpl"            # Airline Transport Pilot License


class TaskStatus(Enum):
    """Status of a checkride task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"


@dataclass
class CheckrideTask:
    """Individual task within a checkride"""
    id: str
    name: str
    description: str
    criteria: Dict[str, float]      # Key: metric name, Value: required value
    status: TaskStatus = TaskStatus.PENDING
    score: float = 0.0
    feedback: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def start(self) -> None:
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now().isoformat()

    def complete(self, passed: bool, score: float, feedback: str = "") -> None:
        self.status = TaskStatus.PASSED if passed else TaskStatus.FAILED
        self.score = score
        self.feedback = feedback
        self.completed_at = datetime.now().isoformat()


@dataclass
class CheckrideResult:
    """Result of a completed checkride"""
    checkride_type: CheckrideType
    passed: bool
    overall_score: float
    task_results: List[Dict]
    examiner_feedback: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_minutes: float = 0.0


@dataclass
class Checkride:
    """A complete checkride examination"""
    id: str
    checkride_type: CheckrideType
    name: str
    description: str
    tasks: List[CheckrideTask] = field(default_factory=list)

    # Requirements
    required_hours: float = 0.0
    required_license: str = ""
    passing_score: float = 80.0

    # State
    active: bool = False
    started_at: Optional[str] = None
    current_task_index: int = 0
    result: Optional[CheckrideResult] = None

    @property
    def current_task(self) -> Optional[CheckrideTask]:
        if 0 <= self.current_task_index < len(self.tasks):
            return self.tasks[self.current_task_index]
        return None

    @property
    def progress(self) -> float:
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.status in [TaskStatus.PASSED, TaskStatus.FAILED])
        return (completed / len(self.tasks)) * 100

    def start(self) -> None:
        self.active = True
        self.started_at = datetime.now().isoformat()
        self.current_task_index = 0
        for task in self.tasks:
            task.status = TaskStatus.PENDING
            task.score = 0.0
        if self.tasks:
            self.tasks[0].start()
        logger.info(f"Checkride started: {self.name}")

    def advance_task(self) -> Optional[CheckrideTask]:
        """Move to the next task"""
        self.current_task_index += 1
        if self.current_task_index < len(self.tasks):
            self.tasks[self.current_task_index].start()
            return self.tasks[self.current_task_index]
        return None

    def complete_current_task(self, metrics: Dict[str, float]) -> bool:
        """
        Complete current task with provided metrics

        Args:
            metrics: Dict of metric name -> achieved value

        Returns:
            True if task passed
        """
        task = self.current_task
        if not task:
            return False

        # Evaluate task
        passed = True
        score = 100.0

        for criterion, required in task.criteria.items():
            achieved = metrics.get(criterion, 0.0)

            # Check if criterion is met
            if criterion.endswith('_max'):
                # Maximum limit
                if achieved > required:
                    passed = False
                    score -= 20
            elif criterion.endswith('_min'):
                # Minimum required
                if achieved < required:
                    passed = False
                    score -= 20
            else:
                # Target value (within 10% tolerance)
                tolerance = required * 0.1
                if abs(achieved - required) > tolerance:
                    passed = False
                    score -= 15

        score = max(0, score)
        feedback = "Task completed successfully" if passed else "Task not completed to standard"

        task.complete(passed, score, feedback)
        logger.info(f"Task {task.name}: {'PASSED' if passed else 'FAILED'} ({score:.0f}%)")

        return passed

    def finish(self) -> CheckrideResult:
        """Complete the checkride and calculate result"""
        # Calculate overall score
        if not self.tasks:
            overall_score = 0.0
        else:
            scores = [t.score for t in self.tasks]
            overall_score = sum(scores) / len(scores)

        # Check if passed
        failed_tasks = [t for t in self.tasks if t.status == TaskStatus.FAILED]
        passed = len(failed_tasks) == 0 and overall_score >= self.passing_score

        # Calculate duration
        duration = 0.0
        if self.started_at:
            start = datetime.fromisoformat(self.started_at)
            duration = (datetime.now() - start).total_seconds() / 60

        # Generate feedback
        if passed:
            feedback = f"Congratulations! You have passed the {self.name}."
        else:
            feedback = f"Unfortunately, you did not pass. Failed tasks: {', '.join(t.name for t in failed_tasks)}"

        self.result = CheckrideResult(
            checkride_type=self.checkride_type,
            passed=passed,
            overall_score=overall_score,
            task_results=[{
                'name': t.name,
                'status': t.status.value,
                'score': t.score,
                'feedback': t.feedback
            } for t in self.tasks],
            examiner_feedback=feedback,
            duration_minutes=duration
        )

        self.active = False
        logger.info(f"Checkride {self.name}: {'PASSED' if passed else 'FAILED'} ({overall_score:.1f}%)")

        return self.result


# Predefined checkrides
def create_ppl_checkride() -> Checkride:
    """Create PPL checkride"""
    return Checkride(
        id="ppl_checkride",
        checkride_type=CheckrideType.PPL,
        name="Private Pilot License Checkride",
        description="Demonstrate proficiency for PPL certification",
        required_hours=40.0,
        required_license="Student",
        tasks=[
            CheckrideTask(
                id="preflight",
                name="Preflight Inspection",
                description="Complete thorough preflight inspection",
                criteria={"completion": 100.0}
            ),
            CheckrideTask(
                id="takeoff",
                name="Normal Takeoff",
                description="Execute a normal takeoff",
                criteria={"centerline_deviation_max": 10.0, "rotation_speed_min": 55.0}
            ),
            CheckrideTask(
                id="straight_level",
                name="Straight and Level Flight",
                description="Maintain altitude within 100ft and heading within 10 degrees",
                criteria={"altitude_deviation_max": 100.0, "heading_deviation_max": 10.0}
            ),
            CheckrideTask(
                id="turns",
                name="Steep Turns",
                description="Execute 45-degree bank turns maintaining altitude",
                criteria={"bank_angle_min": 40.0, "bank_angle_max": 50.0, "altitude_deviation_max": 100.0}
            ),
            CheckrideTask(
                id="slow_flight",
                name="Slow Flight",
                description="Maintain control at minimum controllable airspeed",
                criteria={"airspeed_min": 50.0, "altitude_deviation_max": 100.0}
            ),
            CheckrideTask(
                id="stalls",
                name="Stall Recovery",
                description="Demonstrate proper stall recognition and recovery",
                criteria={"recovery_altitude_loss_max": 500.0}
            ),
            CheckrideTask(
                id="pattern",
                name="Traffic Pattern",
                description="Fly proper traffic pattern",
                criteria={"pattern_altitude_deviation_max": 100.0}
            ),
            CheckrideTask(
                id="landing",
                name="Normal Landing",
                description="Execute a safe normal landing",
                criteria={"vertical_speed_max": 300.0, "centerline_deviation_max": 30.0}
            )
        ]
    )


def create_ir_checkride() -> Checkride:
    """Create Instrument Rating checkride"""
    return Checkride(
        id="ir_checkride",
        checkride_type=CheckrideType.IR,
        name="Instrument Rating Checkride",
        description="Demonstrate proficiency for IR certification",
        required_hours=50.0,
        required_license="PPL",
        tasks=[
            CheckrideTask(
                id="holding",
                name="Holding Pattern",
                description="Execute standard holding pattern",
                criteria={"entry_correct": 1.0, "altitude_deviation_max": 100.0}
            ),
            CheckrideTask(
                id="vor_approach",
                name="VOR Approach",
                description="Execute VOR approach to minimums",
                criteria={"course_deviation_max": 5.0, "altitude_deviation_max": 50.0}
            ),
            CheckrideTask(
                id="ils_approach",
                name="ILS Approach",
                description="Execute precision ILS approach",
                criteria={
                    "localizer_deviation_max": 1.0,
                    "glideslope_deviation_max": 1.0,
                    "vertical_speed_max": 250.0
                }
            ),
            CheckrideTask(
                id="missed_approach",
                name="Missed Approach",
                description="Execute published missed approach procedure",
                criteria={"climb_initiated_timely": 1.0}
            )
        ]
    )


class CheckrideManager:
    """Manages checkride examinations"""

    def __init__(self):
        self._available_checkrides: Dict[str, Callable[[], Checkride]] = {
            'ppl': create_ppl_checkride,
            'ir': create_ir_checkride
        }
        self._active_checkride: Optional[Checkride] = None
        self._completed_checkrides: List[CheckrideResult] = []

    def get_available_types(self) -> List[str]:
        """Get available checkride types"""
        return list(self._available_checkrides.keys())

    def start_checkride(self, checkride_type: str, pilot_hours: float = 0,
                       pilot_license: str = "Student") -> Optional[Checkride]:
        """Start a checkride if requirements are met"""
        if checkride_type not in self._available_checkrides:
            logger.warning(f"Unknown checkride type: {checkride_type}")
            return None

        if self._active_checkride:
            logger.warning("A checkride is already in progress")
            return None

        # Create checkride
        checkride = self._available_checkrides[checkride_type]()

        # Check requirements
        if pilot_hours < checkride.required_hours:
            logger.warning(f"Insufficient hours: {pilot_hours:.1f} < {checkride.required_hours}")
            return None

        self._active_checkride = checkride
        checkride.start()
        return checkride

    def complete_task(self, metrics: Dict[str, float]) -> bool:
        """Complete current task with metrics"""
        if not self._active_checkride:
            return False
        return self._active_checkride.complete_current_task(metrics)

    def advance_task(self) -> Optional[CheckrideTask]:
        """Advance to next task"""
        if not self._active_checkride:
            return None
        return self._active_checkride.advance_task()

    def finish_checkride(self) -> Optional[CheckrideResult]:
        """Finish the active checkride"""
        if not self._active_checkride:
            return None

        result = self._active_checkride.finish()
        self._completed_checkrides.append(result)
        self._active_checkride = None

        return result

    def cancel_checkride(self) -> None:
        """Cancel the active checkride"""
        if self._active_checkride:
            logger.info(f"Checkride cancelled: {self._active_checkride.name}")
            self._active_checkride = None

    @property
    def active_checkride(self) -> Optional[Checkride]:
        return self._active_checkride

    def get_stats(self) -> Dict:
        """Get checkride statistics"""
        if not self._completed_checkrides:
            return {'total': 0, 'passed': 0}

        return {
            'total': len(self._completed_checkrides),
            'passed': sum(1 for r in self._completed_checkrides if r.passed),
            'average_score': sum(r.overall_score for r in self._completed_checkrides) / len(self._completed_checkrides)
        }


# Global checkride manager instance
_checkride_manager: Optional[CheckrideManager] = None

def get_checkride_manager() -> CheckrideManager:
    """Get or create global checkride manager"""
    global _checkride_manager
    if _checkride_manager is None:
        _checkride_manager = CheckrideManager()
    return _checkride_manager
