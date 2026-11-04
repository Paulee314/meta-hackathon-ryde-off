"""The sky behind the app: Open-Meteo readings mapped to sun, clouds, rain, wind and night. Offline."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import sky  # noqa: E402


def reading(code=0, wind=5, gusts=8, day=1, temp=74.4):
    return {"weather_code": code, "wind_speed_10m": wind, "wind_gusts_10m": gusts, "is_day": day, "temperature_2m": temp}


class Sky(unittest.TestCase):
    def test_weather_codes(self):
        cases = {0: "clear", 1: "clear", 2: "partly", 3: "cloudy", 45: "fog", 61: "rain", 81: "rain",
                 95: "storm", 73: "snow"}
        for code, state in cases.items():
            self.assertEqual(sky.from_reading(reading(code))["state"], state, code)

    def test_wind_beats_clouds_but_not_rain(self):
        self.assertEqual(sky.from_reading(reading(3, wind=18))["state"], "windy")
        self.assertEqual(sky.from_reading(reading(0, gusts=30))["state"], "windy")
        self.assertEqual(sky.from_reading(reading(61, wind=25))["state"], "rain")

    def test_night_and_label(self):
        s = sky.from_reading(reading(0, day=0))
        self.assertTrue(s["night"])
        self.assertEqual(s["label"], "Clear in Houston, 74°F")

    def test_no_weather_no_crash(self):
        sky._cache.update(at=0.0, sky=None)

        def broken():
            raise OSError("offline")
        self.assertIsNone(sky.now(fetch=broken))
        self.assertEqual(sky.now(fetch=lambda: reading(61))["state"], "rain")
        self.assertEqual(sky.now(fetch=broken)["state"], "rain")   # cached
        sky._cache.update(at=0.0, sky=None)


if __name__ == "__main__":
    unittest.main()
