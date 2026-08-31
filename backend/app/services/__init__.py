"""Domain services for Ocean Forensics backend."""

from .investigation_service import InvestigationService
from .historical_investigation_service import HistoricalInvestigationService

__all__ = ["InvestigationService", "HistoricalInvestigationService"]
