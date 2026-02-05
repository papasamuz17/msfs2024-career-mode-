"""
V2 Copilot Module
AI copilot with voice, LLM integration, callouts, checklists, and error detection
"""

from .phases import FlightPhaseDetector, FlightPhase, get_phase_detector
from .callouts import CalloutManager, get_callout_manager
from .errors import ErrorDetector, PilotError, get_error_detector
from .checklists import ChecklistManager, Checklist, get_checklist_manager
from .atc import ATCSimulator, get_atc_simulator
from .llm import CopilotLLM, get_copilot_llm
from .voice import VoiceSystem, get_voice_system
from .debrief import DebriefManager, get_debrief_manager

__all__ = [
    'FlightPhaseDetector',
    'FlightPhase',
    'get_phase_detector',
    'CalloutManager',
    'get_callout_manager',
    'ErrorDetector',
    'PilotError',
    'get_error_detector',
    'ChecklistManager',
    'Checklist',
    'get_checklist_manager',
    'ATCSimulator',
    'get_atc_simulator',
    'CopilotLLM',
    'get_copilot_llm',
    'VoiceSystem',
    'get_voice_system',
    'DebriefManager',
    'get_debrief_manager'
]
