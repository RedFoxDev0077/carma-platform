"""The advisor engine: enforces the 15-message limit and the UX guardrail."""
from __future__ import annotations

import re

from app.ai.prompts import build_system_prompt
from app.config import settings
from app.schemas.chat import ChatMessage, ChatState
from app.schemas.knowledge import KnowledgeEntry
from app.schemas.report import ReportData

_REFUND_RE = re.compile(
    r"\b(reembolso|devoluci[oó]n|estafa|no sirve|no funciona|fraude|molesto|enojad)",
    re.IGNORECASE,
)


class Advisor:
    def __init__(self) -> None:
        self._client = None
        if settings.anthropic_api_key:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def reply(
        self, state: ChatState, user_text: str, report: ReportData, knowledge: KnowledgeEntry
    ) -> tuple[str, ChatState]:
        """Return (assistant_text, updated_state). Enforces limit + guardrail."""
        if state.closed or state.remaining <= 0:
            state.closed = True
            return (
                "Tu sesión de asesoría ha finalizado (límite de "
                f"{state.limit} preguntas). ¡Gracias por usar CARMA! 🚗",
                state,
            )

        # UX guardrail — frustration / refund intent
        if _REFUND_RE.search(user_text):
            state.history.append(ChatMessage(role="user", content=user_text))
            msg = (
                "Lamento mucho el inconveniente y entiendo tu molestia. 🙏 "
                "Nuestro equipo puede ayudarte directamente: escríbenos a "
                f"{settings.support_email} con tu placa y con gusto lo revisamos."
            )
            state.history.append(ChatMessage(role="assistant", content=msg))
            return msg, state

        state.user_turns_used += 1
        state.history.append(ChatMessage(role="user", content=user_text))

        answer = await self._generate(state, report, knowledge)

        # append the closing notice on the final allowed turn
        if state.remaining <= 0:
            state.closed = True
            answer += (
                f"\n\n— Esta fue tu última pregunta ({state.limit}/{state.limit}). "
                "¡Éxitos con tu compra! 🤝"
            )
        elif state.remaining <= 2:
            answer += f"\n\n(Te quedan {state.remaining} preguntas)"

        state.history.append(ChatMessage(role="assistant", content=answer))
        return answer, state

    async def _generate(self, state: ChatState, report: ReportData, knowledge: KnowledgeEntry) -> str:
        system = build_system_prompt(report, knowledge, state.remaining)
        messages = [{"role": m.role, "content": m.content} for m in state.history
                    if m.role in ("user", "assistant")]

        if self._client is None:
            # deterministic fallback so the flow works without an API key (CI/local)
            return self._fallback(state, report)

        resp = await self._client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=system,
            messages=messages,
        )
        return "".join(block.text for block in resp.content if block.type == "text").strip()

    @staticmethod
    def _fallback(state: ChatState, report: ReportData) -> str:
        t = report.technical
        flags = ", ".join(t.red_flags) if t.red_flags else "sin alertas graves"
        return (
            f"Sobre tu {t.brand} {t.model} {t.year or ''}: score {report.score or 's/d'}/10. "
            f"Puntos a vigilar: {flags}. "
            f"Papeletas por S/ {t.fines_total_soles:.0f}. "
            "Úsalos para negociar el precio a la baja."
        )


advisor = Advisor()
