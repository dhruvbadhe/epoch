"""GET /weather: current temperature and humidity for a village, display only (Open-Meteo forecast API).

Context only: it never changes an estimate or a number, and it is never part of /advise or a WhatsApp reply.
3-second timeout, in-memory cache; any failure returns {"available": false}.
"""
from __future__ import annotations

import logging
import threading
import time

import httpx

log = logging.getLogger("sellsmart.weather")

URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 3
CACHE_SECONDS = 30 * 60
LABEL = "context only; it does not change the estimate"
ATTRIBUTION = "Weather data by Open-Meteo.com"
_cache: dict[str, tuple[float, dict]] = {}
_lock = threading.Lock()


def current(village: dict, client: httpx.Client | None = None) -> dict:
    key = village["village"]
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < CACHE_SECONDS:
            return hit[1]
    base = {"village": key, "label": LABEL, "attribution": ATTRIBUTION}
    try:
        params = {"latitude": village["lat"], "longitude": village["lon"],
                  "current": "temperature_2m,relative_humidity_2m", "timezone": "Asia/Kolkata"}
        if client is None:
            with httpx.Client(timeout=TIMEOUT_SECONDS) as own:
                r = own.get(URL, params=params)
        else:
            r = client.get(URL, params=params, timeout=TIMEOUT_SECONDS)
        r.raise_for_status()
        now = r.json()["current"]
        result = {**base, "available": True, "time": now["time"],
                  "temperature_c": now["temperature_2m"], "relative_humidity_pct": now["relative_humidity_2m"]}
    except Exception as exc:                      # weather is optional: never raise
        log.warning("weather unavailable for %s: %s", key, exc)
        return {**base, "available": False}
    with _lock:
        _cache[key] = (time.time(), result)
    return result
