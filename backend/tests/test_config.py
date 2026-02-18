import importlib
import os
import sys
import unittest
from pathlib import Path


class ConfigTests(unittest.TestCase):
    def test_settings_loads_values_from_dotenv_file(self):
        env_path = Path(__file__).resolve().parents[1] / ".env"
        backup_text = env_path.read_text() if env_path.exists() else None
        old_url = os.environ.pop("SUPABASE_URL", None)
        old_key = os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)

        try:
            env_path.write_text(
                "SUPABASE_URL=https://example-project.supabase.co\n"
                "SUPABASE_SERVICE_ROLE_KEY=test-service-role-key\n",
                encoding="utf-8",
            )
            if "app.config" in sys.modules:
                del sys.modules["app.config"]
            config = importlib.import_module("app.config")
            config = importlib.reload(config)

            self.assertEqual(config.settings.supabase_url, "https://example-project.supabase.co")
            self.assertEqual(config.settings.supabase_service_key, "test-service-role-key")
        finally:
            if backup_text is None:
                env_path.unlink(missing_ok=True)
            else:
                env_path.write_text(backup_text, encoding="utf-8")
            if old_url is not None:
                os.environ["SUPABASE_URL"] = old_url
            if old_key is not None:
                os.environ["SUPABASE_SERVICE_ROLE_KEY"] = old_key


if __name__ == "__main__":
    unittest.main()
