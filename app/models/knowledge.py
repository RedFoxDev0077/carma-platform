"""Proprietary 150-car intelligence base — backs JSON 2.

Refreshed by a bi-annual scheduled scan (see app/tasks/jobs.py::refresh_knowledge_base).
Editable via the dashboard CRUD dictionary.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CarKnowledge(Base):
    __tablename__ = "car_knowledge"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(64), index=True)
    year_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_to: Mapped[int | None] = mapped_column(Integer, nullable=True)

    safety_score: Mapped[float | None] = mapped_column(Float, nullable=True)   # Latin NCAP etc.
    reliability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    known_defects: Mapped[list] = mapped_column(JSON, default=list)
    recalls: Mapped[list] = mapped_column(JSON, default=list)
    market_notes: Mapped[str] = mapped_column(String(1024), default="")
    avg_price_soles: Mapped[float | None] = mapped_column(Float, nullable=True)
    structural_metrics: Mapped[dict] = mapped_column(JSON, default=dict)

    source: Mapped[str] = mapped_column(String(64), default="manual")  # neoauto/latinncap/olx/recall
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("brand", "model", "year_from", name="uq_car_knowledge_bmy"),
    )
