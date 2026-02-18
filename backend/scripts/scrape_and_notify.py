from __future__ import annotations

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.scraper import (
    collect_all_sources,
    fetch_existing_urls,
    format_daily_digest,
    send_discord_message,
    send_telegram_message,
    upsert_items_to_supabase,
)


def main() -> int:
    if not settings.supabase_url or not settings.supabase_service_key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")

    items = collect_all_sources()
    urls = [item["url"] for item in items]
    existing = fetch_existing_urls(settings.supabase_url, settings.supabase_service_key, urls)
    new_items = [item for item in items if item["url"] not in existing]

    upserted = upsert_items_to_supabase(settings.supabase_url, settings.supabase_service_key, items)

    message = format_daily_digest(new_items)
    send_telegram_message(settings.telegram_bot_token, settings.telegram_chat_id, message)
    send_discord_message(settings.discord_webhook_url, message)

    print(f"Collected: {len(items)} | New: {len(new_items)} | Upserted: {upserted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
