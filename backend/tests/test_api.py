"""Tests for PlotTwistt API endpoints and fallback/caching mechanics."""

import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.schemas import IntentType, Location, AnalyzeRequest
from backend.cache import make_cache_slug, get_cached_response


class TestPlotTwisttAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        """Verify health check returns 200 and expected status."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("PlotTwistt", data["service"])
        self.assertIn("timestamp", data)

    def test_presets_endpoint(self):
        """Verify /api/presets returns the curated demo locations."""
        response = self.client.get("/api/presets")
        self.assertEqual(response.status_code, 200)
        presets = response.json()
        self.assertIsInstance(presets, list)
        self.assertGreaterEqual(len(presets), 3)

        preset_ids = [p["id"] for p in presets]
        self.assertIn("bellandur-lake-corridor", preset_ids)
        self.assertIn("peenya-industrial-area", preset_ids)
        self.assertIn("indiranagar-100ft-road", preset_ids)

        # Validate schema of first item
        first = presets[0]
        self.assertIn("location", first)
        self.assertIn("lat", first["location"])
        self.assertIn("lng", first["location"])
        self.assertIn("intent", first)
        self.assertIn(first["intent"], ["warehouse", "retail", "plot"])

    def test_analyze_fallback_safe_execution(self):
        """Verify /api/analyze executes safely and falls back gracefully when live collectors are unconfigured."""
        payload = {
            "location": {
                "lat": 12.9298,
                "lng": 77.6749,
                "address": "Bellandur Outer Ring Road, Bengaluru",
                "locality": "Bellandur",
                "city": "Bengaluru",
            },
            "intent": "warehouse",
        }

        # Request analysis
        response = self.client.post("/api/analyze?refresh=true", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Validate SPEC.md conformity
        self.assertIn("friction_score", data)
        self.assertTrue(0 <= data["friction_score"] <= 100)
        self.assertIn("verdict", data)
        self.assertIn("summary", data)
        self.assertIn("friction_points", data)
        self.assertGreater(len(data["friction_points"]), 0)

        first_point = data["friction_points"][0]
        self.assertIn("category", first_point)
        self.assertIn("severity", first_point)
        self.assertIn("receipts", first_point)
        self.assertGreater(len(first_point["receipts"]), 0)

        receipt = first_point["receipts"][0]
        self.assertIn("title", receipt)
        self.assertIn("url", receipt)
        self.assertIn("exact_quote", receipt)
        self.assertTrue(receipt["url"].startswith("http"))

    def test_analyze_cache_behavior(self):
        """Verify repeated request hits cache."""
        payload = {
            "location": {
                "lat": 12.9719,
                "lng": 77.6412,
                "address": "100 Feet Road, Indiranagar",
                "locality": "Indiranagar",
                "city": "Bengaluru",
            },
            "intent": "retail",
        }

        # First request
        res1 = self.client.post("/api/analyze", json=payload)
        self.assertEqual(res1.status_code, 200)

        # Second request (should be cached)
        res2 = self.client.post("/api/analyze", json=payload)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertTrue(data2["cached"])


if __name__ == "__main__":
    unittest.main()
