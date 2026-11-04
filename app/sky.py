"""The sky behind the app follows the real weather where the demo business is (Houston): sun when it's
clear, dark clouds and rain when it rains, gusts of leaves when it's windy, stars after dark.

The server asks Open-Meteo (free, no key) at most every 10 minutes, so a visitor's browser makes no
third-party call and nobody is asked for their location. If the weather can't be fetched the app
keeps its usual sky.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from typing import Dict, Optional

PLACE = ("Houston", 29.7604, -95.3698)
URL = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
       "&current=temperature_2m,weather_code,wind_speed_10m,wind_gusts_10m,is_day"
       "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=America%2FChicago")
KEEP = 600          # seconds a reading is reused
WINDY_MPH = 15      # sustained wind that counts as windy
GUSTY_MPH = 25      # or gusts this strong

_cache: Dict = {"at": 0.0, "sky": None}
_lock = threading.Lock()


def from_reading(cur: Dict, place: str = PLACE[0]) -> Dict:
    """Open-Meteo's current reading as the app's sky: state, night, and a short label."""
    code = int(cur.get("weather_code") or 0)
    wind = float(cur.get("wind_speed_10m") or 0)
    gusts = float(cur.get("wind_gusts_10m") or 0)
    if code >= 95:
        state = "storm"
    elif 71 <= code <= 77 or code in (85, 86):
        state = "snow"
    elif 51 <= code <= 67 or 80 <= code <= 82:
        state = "rain"
    elif code in (45, 48):
        state = "fog"
    elif wind >= WINDY_MPH or gusts >= GUSTY_MPH:
        state = "windy"
    elif code == 3:
        state = "cloudy"
    elif code == 2:
        state = "partly"
    else:
        state = "clear"
    words = {"storm": "Storms", "snow": "Snow", "rain": "Rain", "fog": "Fog", "windy": "Windy",
             "cloudy": "Cloudy", "partly": "Partly cloudy", "clear": "Clear"}[state]
    temp = cur.get("temperature_2m")
    return {"state": state, "night": not bool(cur.get("is_day", 1)), "place": place,
            "temp": None if temp is None else round(float(temp)), "wind_mph": round(wind),
            "label": f"{words} in {place}" + ("" if temp is None else f", {round(float(temp))}°F")}


def now(fetch=None) -> Optional[Dict]:
    """The current sky, cached; None if the weather couldn't be read."""
    with _lock:
        if _cache["sky"] and time.time() - _cache["at"] < KEEP:
            return _cache["sky"]
    try:
        cur = (fetch or _fetch)()
        sky = from_reading(cur)
    except Exception:   # the weather is decoration: never break the app over it
        return _cache["sky"]
    with _lock:
        _cache.update(at=time.time(), sky=sky)
    return sky


def _fetch() -> Dict:
    name, lat, lon = PLACE
    req = urllib.request.Request(URL.format(lat=lat, lon=lon), headers={"User-Agent": "ryde-off/1.0"})
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read())["current"]
