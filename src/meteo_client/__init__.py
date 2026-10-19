"""A small, typed client for the free Open-Meteo weather API (no API key)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

__all__ = ["OpenMeteo", "Place", "CurrentWeather", "DailyForecast", "MeteoError", "describe_code"]
__version__ = "0.1.0"

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

_WMO = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Rain showers", 81: "Heavy rain showers", 82: "Violent rain showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm with hail",
}


def describe_code(code: int) -> str:
    """Human-readable text for a WMO weather code."""
    return _WMO.get(code, "Unknown")


class MeteoError(Exception):
    pass


@dataclass(frozen=True)
class Place:
    name: str
    latitude: float
    longitude: float
    country: str = ""
    admin1: str = ""
    timezone: str = "auto"


@dataclass(frozen=True)
class CurrentWeather:
    time: str
    temperature: float
    feels_like: float
    humidity: float
    wind_speed: float
    weather_code: int
    is_day: bool
    units: dict[str, str] = field(default_factory=dict)

    @property
    def description(self) -> str:
        return describe_code(self.weather_code)


@dataclass(frozen=True)
class DailyForecast:
    date: str
    temp_max: float
    temp_min: float
    precipitation_mm: float
    rain_chance: float | None
    weather_code: int

    @property
    def description(self) -> str:
        return describe_code(self.weather_code)


Fetcher = Callable[[str], dict[str, Any]]


def _default_fetch(url: str, timeout: float = 10.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "meteo-client/" + __version__})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            reason = json.loads(exc.read().decode()).get("reason", str(exc))
        except Exception:  # noqa: BLE001
            reason = str(exc)
        raise MeteoError(reason) from exc
    except urllib.error.URLError as exc:
        raise MeteoError(f"Network error: {exc.reason}") from exc


class OpenMeteo:
    """Client for Open-Meteo.

    >>> om = OpenMeteo(units="metric")
    >>> om.current("Lagos").description
    'Partly cloudy'
    """

    def __init__(self, units: str = "metric", fetch: Fetcher | None = None):
        if units not in ("metric", "imperial"):
            raise ValueError("units must be 'metric' or 'imperial'")
        self.units = units
        self._fetch = fetch or _default_fetch

    def _unit_params(self) -> dict[str, str]:
        if self.units == "imperial":
            return {"temperature_unit": "fahrenheit", "wind_speed_unit": "mph", "precipitation_unit": "inch"}
        return {}

    def _get(self, base: str, params: dict[str, Any]) -> dict[str, Any]:
        data = self._fetch(f"{base}?{urllib.parse.urlencode(params)}")
        if data.get("error"):
            raise MeteoError(data.get("reason", "Unknown error"))
        return data

    def search(self, name: str, count: int = 5, language: str = "en") -> list[Place]:
        """Find places by name."""
        data = self._get(GEOCODE_URL, {"name": name, "count": count, "language": language, "format": "json"})
        return [
            Place(r["name"], r["latitude"], r["longitude"], r.get("country", ""), r.get("admin1", ""), r.get("timezone", "auto"))
            for r in data.get("results", [])
        ]

    def _resolve(self, where: str | Place | tuple[float, float]) -> Place:
        if isinstance(where, Place):
            return where
        if isinstance(where, tuple):
            return Place("", where[0], where[1])
        places = self.search(where, count=1)
        if not places:
            raise MeteoError(f"No place found for {where!r}")
        return places[0]

    def current(self, where: str | Place | tuple[float, float]) -> CurrentWeather:
        """Current conditions for a place name, Place, or (lat, lon)."""
        p = self._resolve(where)
        data = self._get(FORECAST_URL, {
            "latitude": p.latitude, "longitude": p.longitude, "timezone": p.timezone,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,is_day",
            **self._unit_params(),
        })
        c, u = data["current"], data.get("current_units", {})
        return CurrentWeather(
            time=c["time"], temperature=c["temperature_2m"], feels_like=c["apparent_temperature"],
            humidity=c["relative_humidity_2m"], wind_speed=c["wind_speed_10m"],
            weather_code=c["weather_code"], is_day=bool(c["is_day"]),
            units={"temperature": u.get("temperature_2m", ""), "wind_speed": u.get("wind_speed_10m", "")},
        )

    def daily(self, where: str | Place | tuple[float, float], days: int = 7) -> list[DailyForecast]:
        """Daily forecast for up to 16 days."""
        if not 1 <= days <= 16:
            raise ValueError("days must be between 1 and 16")
        p = self._resolve(where)
        data = self._get(FORECAST_URL, {
            "latitude": p.latitude, "longitude": p.longitude, "timezone": p.timezone, "forecast_days": days,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code",
            **self._unit_params(),
        })
        d = data["daily"]
        chance = d.get("precipitation_probability_max") or [None] * len(d["time"])
        return [
            DailyForecast(t, hi, lo, pr, ch, code)
            for t, hi, lo, pr, ch, code in zip(
                d["time"], d["temperature_2m_max"], d["temperature_2m_min"], d["precipitation_sum"], chance, d["weather_code"]
            )
        ]
