"""Background jobs. Celery tasks are sync wrappers around async service code."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.config import settings
from app.database import SessionLocal
from app.models import Order, OrderStatus, Conversation, Message, MessageRole, VehicleRecord
from app.schemas.chat import ChatState, ChatMessage
from app.schemas.knowledge import KnowledgeEntry
from app.schemas.report import ReportData, VehicleTechnical
from app.services import report as report_svc
from app.services.whatsapp_client import whatsapp
from app.ai.advisor import advisor
from app.tasks.celery_app import celery


def _run(coro):
    return asyncio.run(coro)


@celery.task(name="app.tasks.jobs.run_report")
def run_report(order_id: int) -> None:
    """Scrape + build PDF + deliver for a paid order."""
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if not order or order.status not in (OrderStatus.PAID, OrderStatus.SCRAPING):
            return
        _run(report_svc.process_paid_order(db, order))


@celery.task(name="app.tasks.jobs.advisor_turn")
def advisor_turn(order_id: int, user_text: str) -> None:
    """One AI advisor turn. Rebuilds JSON 3 state from DB, replies, persists."""
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if not order:
            return

        convo = db.scalar(select(Conversation).where(Conversation.order_id == order_id))
        if convo is None:
            convo = Conversation(
                order_id=order_id, wa_phone=order.wa_phone,
                expires_at=order.chat_expires_at,
            )
            db.add(convo)
            db.commit()
            db.refresh(convo)

        state = ChatState(
            order_id=order_id, plate=order.plate,
            user_turns_used=convo.user_turns_used, closed=convo.closed,
            history=[ChatMessage(role=m.role.value, content=m.content) for m in convo.messages],
        )

        report = _rebuild_report(db, order)
        knowledge = report_svc._load_knowledge(db, report.technical.brand, report.technical.model)

        answer, state = _run(advisor.reply(state, user_text, report, knowledge))

        # persist the two new turns + counter
        db.add(Message(conversation_id=convo.id, role=MessageRole.USER, content=user_text))
        db.add(Message(conversation_id=convo.id, role=MessageRole.ASSISTANT, content=answer))
        convo.user_turns_used = state.user_turns_used
        convo.closed = state.closed
        if state.closed:
            order.status = OrderStatus.CHAT_CLOSED
        db.commit()

        _run(whatsapp.send_text(order.wa_phone, answer))


@celery.task(name="app.tasks.jobs.recover_abandoned")
def recover_abandoned() -> None:
    """Nudge users who started a query but never paid (client: recovery loop)."""
    cutoff_recent = datetime.now(timezone.utc) - timedelta(minutes=20)
    cutoff_old = datetime.now(timezone.utc) - timedelta(hours=24)
    with SessionLocal() as db:
        stale = db.scalars(
            select(Order).where(
                Order.status == OrderStatus.AWAITING_PAYMENT,
                Order.created_at < cutoff_recent,
                Order.created_at > cutoff_old,
            )
        ).all()
        for order in stale:
            _run(whatsapp.send_text(
                order.wa_phone,
                f"👋 ¿Sigues interesado en el reporte de *{order.plate}*? "
                "Tu solicitud sigue activa. Completa el pago y te lo envío en segundos. 🚗",
            ))
            order.status = OrderStatus.ABANDONED  # nudged once; won't spam again
        db.commit()


@celery.task(name="app.tasks.jobs.close_expired_chats")
def close_expired_chats() -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        db.execute(
            update(Order)
            .where(Order.status == OrderStatus.CHAT_OPEN, Order.chat_expires_at < now)
            .values(status=OrderStatus.CHAT_CLOSED)
        )
        db.commit()


@celery.task(name="app.tasks.jobs.refresh_knowledge_base")
def refresh_knowledge_base() -> None:
    """Bi-annual scan of external automotive sources feeding JSON 2.

    LIVE: scrape NeoAuto / Latin NCAP / OLX / recall DBs and upsert CarKnowledge.
    Scaffolded here as the scheduled entry point.
    """
    # TODO: implement authorized source ingestion.
    return None


def _rebuild_report(db, order: Order) -> ReportData:
    """Reconstruct JSON 1 from the persisted (non-personal) vehicle record."""
    vr = db.scalar(
        select(VehicleRecord).where(VehicleRecord.plate == order.plate)
        .order_by(VehicleRecord.id.desc())
    )
    if not vr:
        return ReportData(plate=order.plate, score=order.score)
    tech = VehicleTechnical(
        brand=vr.brand, model=vr.model, year=vr.year, body_style=vr.body_style,
        fuel=vr.fuel, mileage_km=vr.mileage_km, fines_total_soles=vr.fines_total_soles,
        tax_debt_soles=vr.tax_debt_soles, has_liens=vr.has_liens,
        has_capture_order=vr.has_capture_order, has_theft_report=vr.has_theft_report,
        soat_valid=vr.soat_valid, citv_valid=vr.citv_valid,
        total_loss_history=vr.total_loss_history,
        ownership_transfers_90d=vr.ownership_transfers_90d, red_flags=vr.red_flags or [],
    )
    return ReportData(plate=order.plate, technical=tech, score=order.score)
