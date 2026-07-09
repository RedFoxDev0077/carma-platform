"""JSON 2 — proprietary per-model intelligence entry."""
from __future__ import annotations

from pydantic import BaseModel, Field


class KnowledgeEntry(BaseModel):
    brand: str = ""
    model: str = ""
    year_from: int | None = None
    year_to: int | None = None
    safety_score: float | None = None
    reliability_score: float | None = None
    known_defects: list[str] = Field(default_factory=list)
    recalls: list[str] = Field(default_factory=list)
    market_notes: str = ""
    avg_price_soles: float | None = None
    structural_metrics: dict = Field(default_factory=dict)

    @classmethod
    def empty(cls) -> KnowledgeEntry:
        return cls()
