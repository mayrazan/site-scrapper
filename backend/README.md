# Backend

## Run API locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Run scraper job

```bash
python3 scripts/scrape_and_notify.py
```

Required env vars:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `TELEGRAM_BOT_TOKEN` (optional)
- `TELEGRAM_CHAT_ID` (optional)
- `DISCORD_WEBHOOK_URL` (optional)
- `HACKERONE_USERNAME` (optional, enables HackerOne source via API)
- `HACKERONE_API_TOKEN` (optional, enables HackerOne source via API)
