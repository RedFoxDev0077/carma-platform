"""Celery application + periodic schedule (beat)."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery = Celery(
    "carma",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.jobs"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Lima",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery.conf.beat_schedule = {
    # abandoned-payment recovery: nudge users who dropped before paying
    "recover-abandoned": {
        "task": "app.tasks.jobs.recover_abandoned",
        "schedule": 300.0,  # every 5 min
    },
    # auto-close chat sessions past their 30-min window
    "close-expired-chats": {
        "task": "app.tasks.jobs.close_expired_chats",
        "schedule": 120.0,
    },
    # bi-annual knowledge-base refresh (Jan 1 & Jul 1, 03:00)
    "refresh-knowledge": {
        "task": "app.tasks.jobs.refresh_knowledge_base",
        "schedule": crontab(minute=0, hour=3, day_of_month=1, month_of_year="1,7"),
    },
}
