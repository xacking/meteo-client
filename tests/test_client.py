import urllib.parse

import pytest

from meteo_client import MeteoError, OpenMeteo, Place, describe_code

GEO = {"results": [{"name": "Lagos", "latitude": 6.45, "longitude": 3.39, "country": "Nigeria", "admin1": "Lagos", "timezone": "Africa/Lagos"}]}
CUR = {
    "current": {"time": "2026-10-19T10:00", "temperature_2m": 29.1, "apparent_temperature": 33.0, "relative_humidity_2m": 80,
                "wind_speed_10m": 11.2, "weather_code": 2, "is_day": 1},
    "current_units": {"temperature_2m": "°C", "wind_speed_10m": "km/h"},
}
DAILY = {"daily": {"time": ["2026-10-19", "2026-10-20"], "temperature_2m_max": [31, 30], "temperature_2m_min": [24, 23],
                   "precipitation_sum": [0.0, 12.5], "precipitation_probability_max": [10, 85], "weather_code": [2, 63]}}


class FakeFetch:
    def __init__(self):
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        if "geocoding" in url:
            return GEO
        if "current=" in url:
            return CUR
        return DAILY


def test_current_by_name():
    f = FakeFetch()
    w = OpenMeteo(fetch=f).current("Lagos")
    assert w.temperature == 29.1 and w.description == "Partly cloudy" and w.is_day
    assert w.units["temperature"] == "°C"
    q = urllib.parse.parse_qs(urllib.parse.urlparse(f.urls[1]).query)
    assert q["latitude"] == ["6.45"] and q["timezone"] == ["Africa/Lagos"]


def test_daily_imperial_with_coords():
    f = FakeFetch()
    days = OpenMeteo(units="imperial", fetch=f).daily((6.45, 3.39), days=2)
    assert len(days) == 2 and days[1].description == "Rain" and days[1].rain_chance == 85
    assert "temperature_unit=fahrenheit" in f.urls[0]


def test_errors():
    with pytest.raises(MeteoError):
        OpenMeteo(fetch=lambda url: {"results": []}).current("Nowhere")
    with pytest.raises(MeteoError):
        OpenMeteo(fetch=lambda url: {"error": True, "reason": "bad"}).current(Place("x", 0, 0))
    with pytest.raises(ValueError):
        OpenMeteo().daily((0, 0), days=30)


def test_describe():
    assert describe_code(95) == "Thunderstorm"
    assert describe_code(1234) == "Unknown"
