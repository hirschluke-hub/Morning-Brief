"""Weather data — fetches today's high temp and condition from Open-Meteo."""

import json
import urllib.request

LAT, LON = 32.7157, -117.1611  # San Diego

WEATHER_CODES = {
    0: "Clear skies", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 53: "Drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    80: "Rain showers", 81: "Showers", 95: "Thunderstorm",
}


def get_weather():
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={LAT}&longitude={LON}"
            f"&daily=temperature_2m_max,weathercode"
            f"&temperature_unit=fahrenheit"
            f"&timezone=America/Los_Angeles"
        )
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
        temp = round(data["daily"]["temperature_2m_max"][0])
        code = data["daily"]["weathercode"][0]
        desc = WEATHER_CODES.get(code, "San Diego")
        return temp, desc
    except Exception:
        return None, None
