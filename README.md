# meteo-client

A small, typed Python client for the free [Open-Meteo](https://open-meteo.com) weather API. No API key, no dependencies (just the standard library), returns dataclasses instead of raw JSON.

```bash
pip install git+https://github.com/xacking/meteo-client
```

```python
from meteo_client import OpenMeteo

om = OpenMeteo()                     # or OpenMeteo(units="imperial")

now = om.current("Lagos")
print(f"{now.temperature}{now.units['temperature']}, {now.description}, feels like {now.feels_like}")
# 29.1°C, Partly cloudy, feels like 33.0

for day in om.daily("Abuja", days=5):
    print(day.date, day.temp_min, "–", day.temp_max, day.description, f"{day.rain_chance}% rain")

om.search("Kano")                    # [Place(name='Kano', latitude=12.0, longitude=8.5, country='Nigeria', ...)]
om.current((51.5, -0.12))            # by coordinates
```

## What you get

- `current(where)` → `CurrentWeather` (temperature, feels_like, humidity, wind_speed, weather_code, is_day, description)
- `daily(where, days=7)` → `list[DailyForecast]` (up to 16 days)
- `search(name)` → `list[Place]` via Open-Meteo geocoding
- `describe_code(code)` → text for any WMO weather code

`where` can be a place name, a `Place`, or a `(lat, lon)` tuple. Errors raise `MeteoError`.

Open-Meteo is free for non-commercial use. See their [terms](https://open-meteo.com/en/terms) for commercial use.

## License

MIT
