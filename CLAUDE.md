# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal bug bounty writeups aggregator. Scrapes PortSwigger Research, Medium (bug-bounty tag), and HackerOne Hacktivity daily via GitHub Actions, stores results in Supabase Postgres, and serves them through a FastAPI + React frontend.

## Commands

All commands run from repo root unless noted:

```bash
# Full check (lint + build + backend tests)
npm run check

# Frontend
npm run dev          # Vite dev server (http://localhost:5173)
npm run build        # tsc + vite build
npm run lint         # ESLint
npm run lint:fix     # ESLint with autofix
npm run format       # Prettier (write)
npm run format:check # Prettier (check only)

# Backend
npm run backend:run    # uvicorn --reload on port 8000
npm run backend:test   # Python unittest discovery
npm run backend:scrape # Run the scraper + notify script manually
```

**Backend tests require the virtualenv to be active first:**
```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

Run a single backend test:
```bash
cd backend && PYTHONPATH=. python3 -m unittest tests.test_parsers.ParserTests.test_parse_rss_items_extracts_entries -q
```

## Architecture

### Monorepo layout

- `backend/` — Python FastAPI app + scraper (not a Node workspace, managed separately)
- `frontend/` — React/Vite/TypeScript app (npm workspace)
- `infra/supabase/schema.sql` — DB schema, indexes, RLS, retention function
- `.github/workflows/scrape-daily.yml` — Cron at 08:15 UTC, runs `backend/scripts/scrape_and_notify.py`

### Data flow

```
GitHub Actions (daily cron)
  └─> scripts/scrape_and_notify.py
        └─> scraper.collect_all_sources()
              ├─ PortSwigger RSS → parse_rss_items()
              ├─ Medium RSS      → parse_rss_items()
              └─ HackerOne API   → fetch_hackerone_hacktivity_api()
        └─> filter_recent_items()   # drops anything before 2025-01-01
        └─> dedupe_items()          # dedup by URL
        └─> upsert_items_to_supabase()  # on_conflict=url
        └─> send_telegram_message() / send_discord_message()  # only for new items
```

The FastAPI backend (`backend/app/main.py`) calls the Supabase REST API directly (no Supabase client library). It exposes:
- `GET /api/writeups` — filterable by `source`, `year`, `month`, `limit`
- `PATCH /api/writeups/{id}` — toggles `is_favorite`

### Frontend data flow

`App.tsx` → `useWriteups(filters)` hook → TanStack Query → `lib/api.fetchWriteups()` → FastAPI

The **favorites filter is client-side only** — all writeups are fetched and `App.tsx` filters `is_favorite === true` locally. It is not sent to the API.

### Backend config

`backend/app/config.py` reads from `backend/.env` (loaded manually before `os.getenv` calls, not python-dotenv). Copy `backend/.env.example` to `backend/.env`.

Frontend reads `VITE_API_BASE_URL` from `frontend/.env` (defaults to `http://localhost:8000`).

### Key invariants

- URL is the deduplication key — `upsert_items_to_supabase` uses `on_conflict=url`
- Only items with `published_at >= 2025-01-01T00:00:00+00:00` are ingested
- CORS allows only `http://localhost:5173` in dev; update `main.py` for production domains
- HackerOne collection is skipped if `HACKERONE_USERNAME`/`HACKERONE_API_TOKEN` are not set
