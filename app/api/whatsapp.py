"""WhatsApp webhook: verification handshake + inbound message routing.

Inbound routing:
  * a plate-looking message with no open order  -> create order, send payment link
  * a message while chat session is open + valid -> AI advisor turn
  * a message after 30-min expiry / limit reached -> session closed notice
"""
from __future__ import annotations

import hashlib
import hmac
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Order, OrderStatus
from app.services import report as report_svc
from app.services.payment import get_provider
from app.services.whatsapp_client import whatsapp
from app.tasks.jobs import advisor_turn

router = APIRouter(prefix="/webhook/whatsapp", tags=["whatsapp"])

PLATE_RE = re.compile(r"^[A-Za-z]{1,3}-?\d{3,4}$")


@router.get("")
async def verify(
    mode: str = Query(alias="hub.mode", default=""),
    token: str = Query(alias="hub.verify_token", default=""),
    challenge: str = Query(alias="hub.challenge", default=""),
):
    """Meta verification handshake."""
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403)


def _valid_signature(raw: bytes, header: str | None) -> bool:
    if not settings.whatsapp_app_secret:
        return True  # not enforced when unset (local/CI)
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.whatsapp_app_secret.encode(), raw, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header.split("=", 1)[1])


@router.post("")
async def inbound(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    if not _valid_signature(raw, request.headers.get("X-Hub-Signature-256")):
        return Response(status_code=403)

    data = await request.json()
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                await _handle_message(db, message)
    return {"status": "ok"}


async def _handle_message(db: Session, msg: dict) -> None:
    if msg.get("type") != "text":
        return
    wa_phone = msg["from"]
    text = msg["text"]["body"].strip()

    # is there an open chat session for this phone?
    order = db.scalar(
        select(Order)
        .where(Order.wa_phone == wa_phone, Order.status == OrderStatus.CHAT_OPEN)
        .order_by(Order.id.desc())
    )
    if order:
        # 30-minute session close check
        now = datetime.now(timezone.utc)
        if order.chat_expires_at and now >= order.chat_expires_at:
            order.status = OrderStatus.CHAT_CLOSED
            db.commit()
            await whatsapp.send_text(
                wa_phone,
                "⌛ Tu sesión de asesoría (30 min) ha finalizado. "
                "Envía otra placa para un nuevo reporte. ¡Gracias por usar CARMA!",
            )
            return
        advisor_turn.delay(order.id, text)
        return

    # otherwise: treat as a new plate request
    if PLATE_RE.match(text):
        order = report_svc.create_order(db, text, wa_phone)
        link = get_provider().create_checkout(order.id, order.price_soles, order.plate)
        order.payment_provider = link.provider
        order.payment_ref = link.ref
        db.commit()
        await whatsapp.send_text(
            wa_phone,
            f"🚗 Reporte CARMA para *{order.plate}*.\n"
            f"Precio: S/ {order.price_soles:.2f}. Paga aquí para generarlo:\n{link.url}",
        )
    else:
        await whatsapp.send_text(
            wa_phone,
            "👋 Bienvenido a CARMA. Envíame la *placa* del vehículo "
            "(ej. ABC-123) y te preparo su reporte completo.",
        )
