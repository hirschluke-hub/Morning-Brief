#!/usr/bin/env python3
"""Daily morning briefing — generates web page + sends push notification."""

import json
import os
import random
import urllib.request
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────────────────
NTFY_TOPIC    = "luke-brief-x7k2m9"
PAGE_URL      = "https://hirschluke-hub.github.io/Morning-Brief/"

SCRIPT_DIR           = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR             = os.path.join(SCRIPT_DIR, "docs")
HTML_FILE            = os.path.join(DOCS_DIR, "index.html")

GOOGLE_CLIENT_ID     = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_REFRESH_TOKEN = os.environ["GOOGLE_REFRESH_TOKEN"]

LAT, LON = 32.7157, -117.1611  # San Diego

COLOR_CATEGORIES = {
    "1":  ("Work",     "#b39ddb"),
    "10": ("School",   "#81c784"),
}

QUOTES = [
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("Do what you can, with what you have, where you are.", "Theodore Roosevelt"),
    ("It always seems impossible until it's done.", "Nelson Mandela"),
    ("Don't watch the clock; do what it does. Keep going.", "Sam Levenson"),
    ("Either you run the day, or the day runs you.", "Jim Rohn"),
    ("You don't have to be great to start, but you have to start to be great.", "Zig Ziglar"),
    ("The way to get started is to quit talking and begin doing.", "Walt Disney"),
    ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
    ("Your time is limited, so don't waste it living someone else's life.", "Steve Jobs"),
    ("Hard work beats talent when talent doesn't work hard.", "Tim Notke"),
    ("Discipline is choosing between what you want now and what you want most.", "Abraham Lincoln"),
    ("Show up. Do the work. Trust the process.", "Anonymous"),
]

# Curated dramatic/motivational Unsplash photos — rotates daily
HERO_IMAGES = [
    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1400&q=85",  # mountain sunset
    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85",  # mountain sunrise
    "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=1400&q=85",  # aerial lake
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85",  # ocean sunrise
    "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1400&q=85",  # mountain stars
    "https://images.unsplash.com/photo-1434725039720-aaad6dd32dfe?w=1400&q=85",  # desert road
    "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1400&q=85",  # forest mist
    "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1400&q=85",  # lake reflection
    "https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=1400&q=85",  # alpine peaks
    "https://images.unsplash.com/photo-1484910292437-025e5d13ce87?w=1400&q=85",  # city lights
    "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?w=1400&q=85",  # person cliff
    "https://images.unsplash.com/photo-1476611338391-6f395a0dd82e?w=1400&q=85",  # golden hour road
    "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85",  # winter sunrise
    "https://images.unsplash.com/photo-1540390769625-2fc3f8b1d50c?w=1400&q=85",  # dramatic clouds
]

WEATHER_CODES = {
    0: "Clear skies", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 53: "Drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    80: "Rain showers", 81: "Showers", 95: "Thunderstorm",
}

# ── Weather ───────────────────────────────────────────────────────────────────
def get_weather():
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={LAT}&longitude={LON}"
            f"&current=temperature_2m,weather_code"
            f"&temperature_unit=fahrenheit"
            f"&timezone=America/Los_Angeles"
        )
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
        temp = round(data["current"]["temperature_2m"])
        code = data["current"]["weather_code"]
        desc = WEATHER_CODES.get(code, "San Diego")
        return temp, desc
    except Exception:
        return None, None


# ── Google Calendar ───────────────────────────────────────────────────────────
def get_calendar_service():
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return build("calendar", "v3", credentials=creds)


def get_todays_events(service):
    now   = datetime.now(timezone.utc)
    start = now.replace(hour=0,  minute=0,  second=0,  microsecond=0)
    end   = now.replace(hour=23, minute=59, second=59, microsecond=0)

    result = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for e in result.get("items", []):
        color_id          = e.get("colorId", "")
        category, color   = COLOR_CATEGORIES.get(color_id, ("Personal", "#80cbc4"))
        start_str         = e["start"].get("dateTime", e["start"].get("date", ""))
        end_str           = e["end"].get("dateTime",   e["end"].get("date", ""))
        events.append({
            "summary":  e.get("summary", "Untitled"),
            "start":    start_str,
            "end":      end_str,
            "category": category,
            "color":    color,
        })
    return events


def fmt_time(dt_str):
    try:
        dt     = datetime.fromisoformat(dt_str)
        hour   = dt.strftime("%I").lstrip("0") or "12"
        minute = dt.strftime("%M")
        ampm   = dt.strftime("%p").lower()
        return f"{hour}:{minute}{ampm}" if minute != "00" else f"{hour}{ampm}"
    except Exception:
        return dt_str


# ── HTML ──────────────────────────────────────────────────────────────────────
def generate_html(events, temp, weather_desc, quote, author):
    today      = datetime.now()
    date_str   = today.strftime("%A, %B %-d, %Y")
    day_of_yr  = today.timetuple().tm_yday
    image_url  = HERO_IMAGES[day_of_yr % len(HERO_IMAGES)]
    weather_str = f"{temp}°" if temp else ""
    weather_desc_str = weather_desc if weather_desc else ""

    if events:
        rows = ""
        for e in events:
            t = f"{fmt_time(e['start'])}–{fmt_time(e['end'])}"
            rows += f"""
          <div class="event">
            <div class="dot" style="background:{e['color']}"></div>
            <div class="event-info">
              <div class="event-name">{e['summary']}</div>
              <div class="event-time">{t}</div>
            </div>
          </div>"""
        events_html = rows
    else:
        events_html = '<div class="empty">Free day — make it yours.</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Morning Brief</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: #0d0d0d;
      color: #e0e0e0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, sans-serif;
      min-height: 100vh;
    }}

    /* ── Hero ── */
    .hero {{
      position: relative;
      width: 100%;
      height: 55vh;
      min-height: 320px;
      background: url('{image_url}') center/cover no-repeat;
    }}

    .hero-overlay {{
      position: absolute;
      inset: 0;
      background: linear-gradient(
        to bottom,
        rgba(0,0,0,0.35) 0%,
        rgba(0,0,0,0.15) 40%,
        rgba(0,0,0,0.75) 100%
      );
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 28px 32px 32px;
    }}

    .hero-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}

    .greeting {{
      font-size: 22px;
      font-weight: 600;
      color: #fff;
      text-shadow: 0 1px 4px rgba(0,0,0,0.5);
    }}

    .weather-badge {{
      font-size: 13px;
      color: rgba(255,255,255,0.75);
      text-shadow: 0 1px 3px rgba(0,0,0,0.5);
      text-align: right;
    }}

    .hero-bottom {{ }}

    .date-label {{
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 2px;
      color: rgba(255,255,255,0.45);
      margin-bottom: 8px;
    }}

    .hero-quote {{
      font-size: 17px;
      font-style: italic;
      color: rgba(255,255,255,0.9);
      line-height: 1.55;
      text-shadow: 0 1px 4px rgba(0,0,0,0.6);
      max-width: 520px;
    }}

    .hero-author {{
      margin-top: 8px;
      font-size: 12px;
      color: rgba(255,255,255,0.45);
      text-shadow: 0 1px 3px rgba(0,0,0,0.5);
    }}

    /* ── Content ── */
    .content {{
      max-width: 860px;
      margin: 0 auto;
      padding: 36px 32px 64px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 40px;
    }}

    @media (max-width: 600px) {{
      .content {{ grid-template-columns: 1fr; gap: 32px; padding: 28px 20px 56px; }}
    }}

    .label {{
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 2.5px;
      color: #3a3a3a;
      margin-bottom: 16px;
    }}

    .event {{
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 14px 0;
      border-bottom: 1px solid #1a1a1a;
    }}

    .event:last-child {{ border-bottom: none; }}

    .dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
      margin-top: 5px;
    }}

    .event-name {{
      font-size: 15px;
      font-weight: 500;
      color: #ddd;
      line-height: 1.3;
    }}

    .event-time {{
      font-size: 12px;
      color: #484848;
      margin-top: 3px;
    }}

    .todo-item {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 0;
      border-bottom: 1px solid #1a1a1a;
      color: #333;
      font-size: 15px;
    }}

    .todo-item:last-child {{ border-bottom: none; }}

    .circle {{
      width: 17px;
      height: 17px;
      border: 1.5px solid #2a2a2a;
      border-radius: 50%;
      flex-shrink: 0;
    }}

    .empty {{ color: #383838; font-size: 14px; padding: 8px 0; }}

    .weather-strip {{
      background: #111;
      border-bottom: 1px solid #1c1c1c;
      padding: 24px 32px;
      display: flex;
      align-items: center;
      gap: 20px;
    }}

    .weather-temp-big {{
      font-size: 52px;
      font-weight: 200;
      color: #f0f0f0;
      line-height: 1;
    }}

    .weather-right {{}}

    .weather-condition {{
      font-size: 16px;
      color: #aaa;
      font-weight: 400;
    }}

    .weather-location {{
      font-size: 12px;
      color: #3a3a3a;
      margin-top: 4px;
      text-transform: uppercase;
      letter-spacing: 1.5px;
    }}

    .bottom {{
      text-align: center;
      padding: 0 32px 56px;
      font-size: 13px;
      color: #2e2e2e;
      font-style: italic;
      letter-spacing: 0.3px;
    }}
  </style>
</head>
<body>

  <div class="hero">
    <div class="hero-overlay">
      <div class="hero-top">
        <div class="greeting">Good morning, Luke.</div>
      </div>
      <div class="hero-bottom">
        <div class="date-label">{date_str}</div>
        <div class="hero-quote">"{quote}"</div>
        <div class="hero-author">— {author}</div>
      </div>
    </div>
  </div>

  <div class="weather-strip">
    <div class="weather-temp-big">{weather_str}</div>
    <div class="weather-right">
      <div class="weather-condition">{weather_desc_str}</div>
      <div class="weather-location">San Diego, CA</div>
    </div>
  </div>

  <div class="content">
    <div>
      <div class="label">Today's Schedule</div>
      {events_html}
    </div>
    <div>
      <div class="label">To-Do</div>
      <div class="todo-item"><div class="circle"></div> —</div>
      <div class="todo-item"><div class="circle"></div> —</div>
      <div class="todo-item"><div class="circle"></div> —</div>
    </div>
  </div>

  <div class="bottom">You're building the life you dreamed of. Keep going.</div>

</body>
</html>"""


# ── Save & send ───────────────────────────────────────────────────────────────
def save_html(html):
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)


def send_notification(title, body):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=body.encode(),
        headers={"Title": title, "Click": PAGE_URL},
    )
    urllib.request.urlopen(req, timeout=5)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    service        = get_calendar_service()
    events         = get_todays_events(service)
    temp, weather  = get_weather()
    quote, author  = random.choice(QUOTES)

    html = generate_html(events, temp, weather, quote, author)
    save_html(html)

    day = datetime.now().strftime("%A")
    send_notification("Morning Brief", f"Good morning Luke. Your {day} brief is ready.")
    print("Done.")
