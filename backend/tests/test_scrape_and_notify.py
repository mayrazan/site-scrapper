import importlib.util
from pathlib import Path
import types
import unittest
from unittest.mock import patch


def _load_scrape_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "scrape_and_notify.py"
    spec = importlib.util.spec_from_file_location("scrape_and_notify", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ScrapeAndNotifyTests(unittest.TestCase):
    def test_no_notifications_when_no_new_items(self):
        module = _load_scrape_module()
        module.settings = types.SimpleNamespace(
            supabase_url="https://db.example.com",
            supabase_service_key="secret",
            telegram_bot_token="tg",
            telegram_chat_id="chat",
            discord_webhook_url="https://discord.example.com/webhook",
        )
        existing_item = {"url": "https://example.com/a", "title": "A"}

        with (
            patch.object(module, "collect_all_sources", return_value=[existing_item]),
            patch.object(module, "fetch_existing_urls", return_value={"https://example.com/a"}),
            patch.object(module, "upsert_items_to_supabase", return_value=1),
            patch.object(module, "format_daily_digest") as digest,
            patch.object(module, "send_telegram_message") as telegram,
            patch.object(module, "send_discord_message") as discord,
        ):
            code = module.main()

        self.assertEqual(code, 0)
        digest.assert_not_called()
        telegram.assert_not_called()
        discord.assert_not_called()

    def test_notifications_when_there_are_new_items(self):
        module = _load_scrape_module()
        module.settings = types.SimpleNamespace(
            supabase_url="https://db.example.com",
            supabase_service_key="secret",
            telegram_bot_token="tg",
            telegram_chat_id="chat",
            discord_webhook_url="https://discord.example.com/webhook",
        )
        new_item = {"url": "https://example.com/new", "title": "N"}

        with (
            patch.object(module, "collect_all_sources", return_value=[new_item]),
            patch.object(module, "fetch_existing_urls", return_value=set()),
            patch.object(module, "upsert_items_to_supabase", return_value=1),
            patch.object(module, "format_daily_digest", return_value="msg") as digest,
            patch.object(module, "send_telegram_message") as telegram,
            patch.object(module, "send_discord_message") as discord,
        ):
            code = module.main()

        self.assertEqual(code, 0)
        digest.assert_called_once()
        telegram.assert_called_once_with("tg", "chat", "msg")
        discord.assert_called_once_with("https://discord.example.com/webhook", "msg")


if __name__ == "__main__":
    unittest.main()
