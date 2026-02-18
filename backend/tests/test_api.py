import importlib.util
import unittest


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


if __name__ == "__main__":
    unittest.main()
