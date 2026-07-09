"""The Order is the spine of a single report request lifecycle."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import String, Float, Enum as SAEnum, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OrderStatus(str, enum.Enum):
    NEW = "new"                      # plate received, awaiting payment
    AWAITING_PAYMENT = "awaiting_payment"
    PAID = "paid"
    SCRAPING = "scraping"
    REPORT_SENT = "report_sent"
    CHAT_OPEN = "chat_open"          # AI advisor session active
    CHAT_CLOSED = "chat_closed"
    ABANDONED = "abandoned"          # dropped before paying
    FAILED = "failed"
    REFUND_REQUESTED = "refund_requested"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(16), index=True)
    wa_phone: Mapped[str] = mapped_column(String(32), index=True)

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus), default=OrderStatus.NEW, index=True
    )

    # money (soles)
    price_soles: Mapped[float] = mapped_column(Float, default=0.0)
    rpa_cost_soles: Mapped[float] = mapped_column(Float, default=0.0)
    payment_provider: Mapped[str] = mapped_column(String(32), default="")
    payment_ref: Mapped[str] = mapped_column(String(128), default="")

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    pdf_path: Mapped[str] = mapped_column(String(255), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    report_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    chat_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_orders_status_created", "status", "created_at"),
    )

    @property
    def net_margin_soles(self) -> float:
        """Real-time net margin used by the Finanzas dashboard tab."""
        return round(self.price_soles - self.rpa_cost_soles, 2)
