"""JSON 3 — chat history + strict message countdown."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import settings


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatState(BaseModel):
    order_id: int
    plate: str
    history: list[ChatMessage] = Field(default_factory=list)
    user_turns_used: int = 0
    limit: int = settings.ai_message_limit
    closed: bool = False

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.user_turns_used)

    @property
    def is_last_turn(self) -> bool:
        return self.remaining <= 1
