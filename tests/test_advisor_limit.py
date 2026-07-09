"""15-message guardrail + UX refund guardrail (uses the no-API-key fallback)."""
import asyncio

from app.ai.advisor import Advisor
from app.config import settings
from app.schemas.chat import ChatState
from app.schemas.knowledge import KnowledgeEntry
from app.schemas.report import ReportData, VehicleTechnical


def _report():
    return ReportData(plate="ABC-123", technical=VehicleTechnical(brand="Kia", model="Rio"), score=8.0)


def test_counter_decrements_and_closes():
    adv = Advisor()
    adv._client = None  # force deterministic fallback
    state = ChatState(order_id=1, plate="ABC-123", limit=3)
    rep, kb = _report(), KnowledgeEntry.empty()

    for i in range(3):
        _, state = asyncio.run(adv.reply(state, f"pregunta {i}", rep, kb))
    assert state.user_turns_used == 3
    assert state.closed is True

    # further messages are refused
    msg, state = asyncio.run(adv.reply(state, "otra mas", rep, kb))
    assert "finalizado" in msg.lower()


def test_refund_intent_routes_to_support():
    adv = Advisor()
    adv._client = None
    state = ChatState(order_id=1, plate="ABC-123", limit=15)
    msg, state = asyncio.run(adv.reply(state, "esto es una estafa, quiero reembolso", _report(), KnowledgeEntry.empty()))
    assert settings.support_email in msg
    assert state.user_turns_used == 0  # refund path does not consume a turn


def test_limit_from_settings_default():
    state = ChatState(order_id=1, plate="X")
    assert state.limit == settings.ai_message_limit
