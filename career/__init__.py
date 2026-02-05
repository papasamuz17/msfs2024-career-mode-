"""
V2 Career Module
Pilot profile, company reputation, logbook, and progression systems
"""

from .pilot_profile import PilotProfile, License, get_pilot, load_pilot, set_pilot
from .companies import Company, CompanyManager, get_company_manager
from .logbook import LogBook, LogEntry, get_logbook
from .progression import ProgressionManager, Requirement, get_progression

__all__ = [
    'PilotProfile',
    'License',
    'get_pilot',
    'load_pilot',
    'set_pilot',
    'Company',
    'CompanyManager',
    'get_company_manager',
    'LogBook',
    'LogEntry',
    'get_logbook',
    'ProgressionManager',
    'Requirement',
    'get_progression'
]
