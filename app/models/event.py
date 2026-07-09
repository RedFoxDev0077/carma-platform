"""Operational telemetry: portal health (semáforo) and user feedback votes."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PortalHealthEvent(Base):
    """One row per scrape attempt against a portal — powers the RPA semáforo."""
    __tablename__ = "portal_health_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    portal: Mapped[str] = mapped_column(String(32), index=True)   # sunarp/sat/sutran/...
    ok: Mapped[bool] = mapped_column(Boolean)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (Index("ix_portal_health_portal_time", "portal", "created_at"),)


class FeedbackVote(Base):
    __tablename__ = "feedback_votes"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    liked: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
