from django.test import Client, TestCase


class HealthcheckTests(TestCase):
    def test_healthcheck_returns_ok(self) -> None:
        response = Client().get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
