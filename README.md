# CARMA — WhatsApp Vehicle-Report Platform

Send a Peruvian license plate on WhatsApp → pay → the system scrapes 7 state
portals in parallel, generates a scored PDF report, and opens a 15-message AI
advisor session. Includes an internal dashboard with finance, control and market
-intelligence tabs.

> **Status:** working end-to-end skeleton. Portal automation runs in **demo mode**
> (synthetic, deterministic data) until authorized live selectors are implemented
> in each `app/rpa/portals/*.py::_scrape_live`. Everything else — pipeline, PDF,
> scoring, AI, payments interface, dashboard, queue — is real.

## Architecture

```
WhatsApp ─▶ /webhook/whatsapp ─▶ create Order ─▶ payment link
                                                     │
Payment gateway ─▶ /webhook/payment ─▶ run_report (Celery)
                                             │
                     ┌───────────────────────┴───────────────────────┐
                     ▼                                                 ▼
            RPA Orchestrator (parallel)                        PDF Compiler
       base portals ▶ COST GATE ▶ paid portal                scoring + template
                     │                                                 │
                     ▼                                                 ▼
            persist NON-personal data                        WhatsApp document
            (Ley 29733: personal data                                 │
             stays in memory only)                             AI advisor chat
                                                              (15-msg / 30-min)
```

| Layer | Tech | Path |
|---|---|---|
| API | FastAPI | `app/main.py`, `app/api/` |
| RPA engine | Playwright + asyncio + cost gate | `app/rpa/` |
| PDF | Jinja2 + headless Chromium | `app/pdf/` |
| AI advisor | Anthropic (Claude), 15-msg guardrail | `app/ai/` |
| Payments | Stripe / Culqi abstraction | `app/services/payment.py` |
| Queue | Celery + Redis (+ beat) | `app/tasks/` |
| Data | PostgreSQL + SQLAlchemy 2.0 | `app/models/` |
| Dashboard | 3 tabs + CRUD | `app/api/dashboard.py` |

The three JSON contracts live in `app/schemas/`: **report** (JSON 1),
**knowledge** (JSON 2), **chat** (JSON 3).

## Client requirements mapped

1. **Dynamic PDF containers** → `app/pdf/compiler.py::build_context` + `templates/report.html` (score gauge, % bars, radar, red-flags, AI text — all data-injected).
2. **30-min chat close** → `Order.chat_expires_at`, enforced in `app/api/whatsapp.py` + `close_expired_chats` beat task.
3. **RPA cost control** → `app/rpa/orchestrator.py`: free base portals run first; if state portals are down, the paid S/6.10 lookup is skipped and a "wait" message is sent.
4. **3-tab dashboard** → `app/api/dashboard.py`: `/finanzas`, `/control` (+ semáforo), `/inteligencia`.
5. **Ley 29733** → technical data persisted forever; personal data (`PersonalData`) held in memory only and never written to the DB (`report.strip_personal()`).

## Run locally

```bash
cp .env.example .env            # fill values as you get them
pip install -r requirements.txt
playwright install chromium     # only needed for live/PDF rendering

# infra
docker compose up -d db redis
python scripts/init_db.py

# app + worker
uvicorn app.main:app --reload
celery -A app.tasks.celery_app.celery worker -l info
celery -A app.tasks.celery_app.celery beat   -l info
```

Or the whole stack: `docker compose up --build`.

## Tests

```bash
pytest          # scoring, RPA cost gate + data isolation, AI limits — no DB/network needed
ruff check .
```

## Deploy (Hostinger VPS)

`docker compose up -d --build` on the VPS. Put a reverse proxy (Caddy/Nginx) in
front for TLS on `api.carma.pe`. See `Dockerfile` for the Chromium system deps.

> ⚠️ **CPU:** the current VPS is 1 vCPU. Running 7 parallel headless browsers +
> workers needs ≥2 vCPU for the 60-second target. Resize before going live.

## Legal / compliance note

Live scraping of state portals and captcha solving must be done under authorized
access and in compliance with **Ley N° 29733** and each portal's terms. The
`_scrape_live` methods are intentionally left as authorized-integration points.
Personal data handling is already constrained to in-memory-only by design.
