#!/usr/bin/env python3
"""Daily morning briefing — generates web page + sends push notification."""

import base64
import json
import os
import random
import urllib.request
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────────────────
NTFY_TOPIC    = "luke-brief-x7k2m9"
PAGE_URL      = "https://hirschluke-hub.github.io/Morning-Brief/"

TWILIO_SID    = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_TOKEN  = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_NUMBER = "+18588081672"

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

# Each quote is paired with a thematically matched hero image
QUOTE_IMAGE_PAIRS = [
    (
        "I've missed more than 9,000 shots in my career. I've lost almost 300 games. I've failed over and over again. That is why I succeed.",
        "Michael Jordan",
        "https://images.unsplash.com/photo-1546519638405-a2526ab7ccee?w=1400&q=85",  # basketball court
    ),
    (
        "The moment you give up is the moment you let someone else win.",
        "Kobe Bryant",
        "https://images.unsplash.com/photo-1608245449230-4ac19066d2d0?w=1400&q=85",  # basketball intensity
    ),
    (
        "I hated every minute of training, but I said: don't quit. Suffer now and live the rest of your life as a champion.",
        "Muhammad Ali",
        "https://images.unsplash.com/photo-1549719386-74dfcbf7dbed?w=1400&q=85",  # boxing
    ),
    (
        "You are in danger of living a life so comfortable and soft that you will die without ever realizing your true potential.",
        "David Goggins",
        "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85",  # runner pushing limits
    ),
    (
        "Either you run the day, or the day runs you.",
        "Jim Rohn",
        "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1400&q=85",  # mountain sunrise commanding view
    ),
    (
        "It always seems impossible until it's done.",
        "Nelson Mandela",
        "https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=1400&q=85",  # alpine summit
    ),
    (
        "Success is not final, failure is not fatal: it is the courage to continue that counts.",
        "Winston Churchill",
        "https://images.unsplash.com/photo-1540390769625-2fc3f8b1d50c?w=1400&q=85",  # dramatic storm clouds
    ),
    (
        "Hard work beats talent when talent doesn't work hard.",
        "Tim Notke",
        "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1400&q=85",  # gym / weight room
    ),
    (
        "Your time is limited, so don't waste it living someone else's life.",
        "Steve Jobs",
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85",  # open ocean horizon
    ),
    (
        "Do what you can, with what you have, where you are.",
        "Theodore Roosevelt",
        "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?w=1400&q=85",  # person on cliff edge
    ),
    (
        "Discipline is choosing between what you want now and what you want most.",
        "Abraham Lincoln",
        "https://images.unsplash.com/photo-1476611338391-6f395a0dd82e?w=1400&q=85",  # lone road golden hour
    ),
    (
        "Show up. Do the work. Trust the process.",
        "Anonymous",
        "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1400&q=85",  # mountain under stars
    ),
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


# ── To-Do (inbound SMS) ───────────────────────────────────────────────────────
def get_todos():
    try:
        from email.utils import parsedate_to_datetime
        import urllib.parse
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
            f"?To={urllib.parse.quote(TWILIO_NUMBER)}&PageSize=50"
        )
        creds = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()
        req   = urllib.request.Request(url, headers={"Authorization": f"Basic {creds}"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        msgs = []
        for m in data.get("messages", []):
            if m.get("direction") != "inbound":
                continue
            sent = parsedate_to_datetime(m["date_sent"])
            if sent >= cutoff:
                msgs.append({"text": m["body"].strip(), "time": sent})
        msgs.sort(key=lambda x: x["time"])

        # Find the most recent "clear" — only keep messages after it
        last_clear = None
        for msg in msgs:
            if msg["text"].strip().lower().rstrip("!.:") == "clear":
                last_clear = msg["time"]
        if last_clear:
            msgs = [m for m in msgs if m["time"] > last_clear]

        # "done: <item>" removes matching todos
        done  = {m["text"][5:].strip().lower() for m in msgs if m["text"].lower().startswith("done:")}
        todos = [m["text"] for m in msgs if not m["text"].lower().startswith("done:") and m["text"].lower().strip() not in done]

        print(f"Todos found: {todos}")
        return todos
    except Exception as e:
        print(f"Todo fetch error: {e}")
        return []


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
        if "T" not in dt_str:
            return "All day"
        dt     = datetime.fromisoformat(dt_str)
        hour   = dt.strftime("%I").lstrip("0") or "12"
        minute = dt.strftime("%M")
        ampm   = dt.strftime("%p").lower()
        return f"{hour}:{minute}{ampm}" if minute != "00" else f"{hour}{ampm}"
    except Exception:
        return dt_str


# ── HTML ──────────────────────────────────────────────────────────────────────
def generate_html(events, todos, temp, weather_desc, quote, author, image_url):
    today        = datetime.now()
    day_name     = today.strftime("%A").upper()
    date_display = today.strftime("%B %-d, %Y")
    weather_str      = f"{temp}°" if temp else ""
    weather_desc_str = weather_desc if weather_desc else ""

    if events:
        rows = ""
        for e in events:
            start_t    = fmt_time(e["start"])
            end_t      = fmt_time(e["end"])
            time_range = start_t if start_t == "All day" else f"{start_t} — {end_t}"
            rows += f"""
          <div class="event" style="border-left-color:{e['color']}">
            <div class="event-time">{time_range}</div>
            <div class="event-name">{e['summary']}</div>
            <div class="event-category" style="color:{e['color']}">{e['category']}</div>
          </div>"""
        events_html = rows
    else:
        events_html = '<div class="empty">Free day — make it yours.</div>'

    if todos:
        todos_html = "".join(
            f'<div class="todo-item"><div class="circle"></div>{item}</div>'
            for item in todos
        )
    else:
        todos_html = '<div class="empty">Text (858) 808-1672 to add tasks.</div>'

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
      height: 60vh;
      min-height: 360px;
      background: url('{image_url}') center/cover no-repeat;
    }}

    .hero-overlay {{
      position: absolute;
      inset: 0;
      background: linear-gradient(
        to bottom,
        rgba(0,0,0,0.3) 0%,
        rgba(0,0,0,0.1) 35%,
        rgba(0,0,0,0.85) 100%
      );
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 28px 32px 36px;
    }}

    .hero-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}

    .greeting {{
      font-size: 13px;
      font-weight: 500;
      letter-spacing: 2.5px;
      text-transform: uppercase;
      color: rgba(255,255,255,0.55);
      text-shadow: 0 1px 4px rgba(0,0,0,0.5);
    }}

    .hero-bottom {{ }}

    .hero-day {{
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 3px;
      color: rgba(255,255,255,0.38);
      text-transform: uppercase;
      margin-bottom: 6px;
    }}

    .hero-date {{
      font-size: 38px;
      font-weight: 700;
      color: #fff;
      letter-spacing: -0.5px;
      text-shadow: 0 2px 12px rgba(0,0,0,0.6);
      margin-bottom: 18px;
      line-height: 1;
    }}

    .hero-quote {{
      font-size: 16px;
      font-style: italic;
      color: rgba(255,255,255,0.85);
      line-height: 1.6;
      text-shadow: 0 1px 4px rgba(0,0,0,0.6);
      max-width: 500px;
    }}

    .hero-author {{
      margin-top: 8px;
      font-size: 12px;
      color: rgba(255,255,255,0.38);
      text-shadow: 0 1px 3px rgba(0,0,0,0.5);
      letter-spacing: 0.5px;
    }}

    /* ── Weather ── */
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
      .hero-date {{ font-size: 28px; }}
    }}

    .label {{
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 2.5px;
      color: #888;
      font-weight: 600;
      margin-bottom: 16px;
    }}

    /* ── Event cards ── */
    .event {{
      background: #111;
      border-radius: 12px;
      border-left: 4px solid #444;
      padding: 14px 16px;
      margin-bottom: 10px;
    }}

    .event-time {{
      font-size: 19px;
      font-weight: 700;
      color: #fff;
      line-height: 1;
      margin-bottom: 5px;
    }}

    .event-name {{
      font-size: 14px;
      color: #888;
      line-height: 1.35;
      margin-bottom: 5px;
    }}

    .event-category {{
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      opacity: 0.7;
    }}

    /* ── To-Do ── */
    .todo-item {{
      display: flex;
      align-items: center;
      gap: 14px;
      background: #111;
      border-radius: 12px;
      border-left: 4px solid #555;
      padding: 14px 16px;
      margin-bottom: 10px;
      font-size: 15px;
      font-weight: 500;
      color: #e8e8e8;
    }}

    .circle {{
      width: 18px;
      height: 18px;
      border: 2px solid #555;
      border-radius: 50%;
      flex-shrink: 0;
    }}

    .empty {{ color: #383838; font-size: 14px; padding: 8px 0; }}

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
        <div class="hero-day">{day_name}</div>
        <div class="hero-date">{date_display}</div>
        <div class="hero-quote">"{quote}"</div>
        <div class="hero-author">— {author}</div>
      </div>
    </div>
  </div>

  <div class="weather-strip">
    <div class="weather-temp-big">{weather_str}</div>
    <div class="weather-right">
      <div class="weather-condition">{weather_desc_str}</div>
      <div class="weather-location">San Diego, CA — Today's High</div>
    </div>
  </div>

  <div class="content">
    <div>
      <div class="label">Today's Schedule</div>
      {events_html}
    </div>
    <div>
      <div class="label">To-Do</div>
      {todos_html}
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
    todos          = get_todos()
    temp, weather  = get_weather()
    quote, author, image_url = random.choice(QUOTE_IMAGE_PAIRS)

    html = generate_html(events, todos, temp, weather, quote, author, image_url)
    save_html(html)

    day = datetime.now().strftime("%A")
    send_notification("Morning Brief", f"Good morning Luke. Your {day} brief is ready.")
    print("Done.")
