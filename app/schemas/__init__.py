"""Pydantic schemas — the three JSON contracts that flow through the pipeline.

JSON 1 — ReportData     : scraped report + valuation injected into PDF & AI prompt.
JSON 2 — KnowledgeEntry : proprietary per-model intelligence injected into AI prompt & PDF.
JSON 3 — ChatState      : conversation history + strict 15-message countdown.
"""
from app.schemas.report import (
    PortalResult,
    PersonalData,
    ReportData,
    VehicleTechnical,
)
from app.schemas.knowledge import KnowledgeEntry
from app.schemas.chat import ChatMessage, ChatState

__all__ = [
    "PortalResult",
    "PersonalData",
    "ReportData",
    "VehicleTechnical",
    "KnowledgeEntry",
    "ChatMessage",
    "ChatState",
]
