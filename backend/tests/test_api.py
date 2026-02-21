import importlib.util
import unittest
from unittest.mock import MagicMock, patch


FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None


@unittest.skipUnless(FASTAPI_INSTALLED, "fastapi not installed in current environment")
class ApiTests(unittest.TestCase):
    def test_health_endpoint(self):
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


@unittest.skipUnless(FASTAPI_INSTALLED, "fastapi not installed in current environment")
class KeywordSearchTests(unittest.TestCase):
    def _make_client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def _mock_supabase(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    def _patch_settings(self):
        mock_settings = MagicMock()
        mock_settings.supabase_url = "https://fake.supabase.co"
        mock_settings.supabase_service_key = "fake-key"
        return patch("app.main.settings", mock_settings)

    def test_list_writeups_q_builds_or_filter(self):
        client = self._make_client()
        with self._patch_settings(), patch("app.main.requests.get") as mock_get:
            mock_get.return_value = self._mock_supabase()
            client.get("/api/writeups?q=SSRF")
            called_url = mock_get.call_args[0][0]
        self.assertIn("or=(title.ilike.*SSRF*,summary.ilike.*SSRF*)", called_url)

    def test_list_writeups_q_sanitizes_special_chars(self):
        client = self._make_client()
        with self._patch_settings(), patch("app.main.requests.get") as mock_get:
            mock_get.return_value = self._mock_supabase()
            client.get("/api/writeups?q=SS*RF(bad)")
            called_url = mock_get.call_args[0][0]
        self.assertIn("*SSRFbad*", called_url)

    def test_list_writeups_q_absent_skips_or_filter(self):
        client = self._make_client()
        with self._patch_settings(), patch("app.main.requests.get") as mock_get:
            mock_get.return_value = self._mock_supabase()
            client.get("/api/writeups")
            called_url = mock_get.call_args[0][0]
        self.assertNotIn("or=", called_url)


if __name__ == "__main__":
    unittest.main()
