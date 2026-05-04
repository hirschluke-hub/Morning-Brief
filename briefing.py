#!/usr/bin/env python3
"""Daily morning briefing — generates web page + sends SMS link."""

import json
import os
import random
import smtplib
import urllib.request
from datetime import datetime, timezone
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────────────────
GMAIL_ADDRESS        = "hirschluke@gmail.com"
GMAIL_APP_PW         = os.environ.get("GMAIL_APP_PW", "nnkqbijaeeyputun")
SMS_GATEWAY          = "4254925800@vtext.com"
PAGE_URL             = "https://hirschluke-hub.github.io/Morning-Brief/"

SCRIPT_DIR           = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR             = os.path.join(SCRIPT_DIR, "docs")
HTML_FILE            = os.path.join(DOCS_DIR, "index.html")

GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID",     "763633570239-qnubdp4htilvdal2lf4de7r3b5tk8ikt.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "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")
GOOGLE_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN", "1//06W5GtjfxzER8CgYIARAAGAYSNwF-L9IrUwTpmHepvTVZT84TpHgBjrOqISPWxqCRBd6yvn0TncmXSiLK4U-9biA7jGaL_a8Dr64")

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
    today    = datetime.now()
    date_str = today.strftime("%A, %B %-d, %Y")

    # weather block
    if temp:
        weather_html = f"""
  <div class="weather">
    <div class="temp">{temp}°</div>
    <div>
      <div class="weather-desc">{weather_desc}</div>
      <div class="weather-loc">San Diego, CA</div>
    </div>
  </div>"""
    else:
        weather_html = ""

    # events block
    if events:
        rows = ""
        for e in events:
            t = f"{fmt_time(e['start'])}–{fmt_time(e['end'])}"
            rows += f"""
    <div class="event">
      <div class="dot" style="background:{e['color']}"></div>
      <div class="event-info">
        <div class="event-name">{e['summary']}</div>
        <div class="event-cat">{e['category']}</div>
      </div>
      <div class="event-time">{t}</div>
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
      padding: 52px 24px 72px;
      max-width: 480px;
      margin: 0 auto;
    }}

    .date {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 2.5px;
      color: #484848;
      margin-bottom: 10px;
    }}

    .greeting {{
      font-size: 32px;
      font-weight: 600;
      color: #f2f2f2;
      margin-bottom: 40px;
      line-height: 1.2;
    }}

    .weather {{
      display: flex;
      align-items: center;
      gap: 18px;
      background: #161616;
      border-radius: 16px;
      padding: 20px 22px;
      margin-bottom: 20px;
    }}

    .temp {{
      font-size: 40px;
      font-weight: 300;
      color: #f0f0f0;
    }}

    .weather-desc {{
      font-size: 15px;
      color: #aaa;
    }}

    .weather-loc {{
      font-size: 12px;
      color: #484848;
      margin-top: 3px;
    }}

    .quote {{
      border-left: 2px solid #222;
      padding: 12px 18px;
      margin-bottom: 40px;
      color: #585858;
      font-size: 14px;
      line-height: 1.75;
      font-style: italic;
    }}

    .quote-author {{
      margin-top: 8px;
      font-style: normal;
      font-size: 12px;
      color: #3a3a3a;
    }}

    .label {{
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 2.5px;
      color: #383838;
      margin-bottom: 14px;
    }}

    .events {{ margin-bottom: 40px; }}

    .event {{
      display: flex;
      align-items: center;
      gap: 14px;
      background: #161616;
      border-radius: 14px;
      padding: 16px 18px;
      margin-bottom: 8px;
    }}

    .dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }}

    .event-info {{ flex: 1; }}

    .event-name {{
      font-size: 15px;
      font-weight: 500;
      color: #e0e0e0;
    }}

    .event-cat {{
      font-size: 11px;
      color: #484848;
      margin-top: 3px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }}

    .event-time {{
      font-size: 13px;
      color: #484848;
      white-space: nowrap;
    }}

    .todo-item {{
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 14px 0;
      border-bottom: 1px solid #161616;
      color: #383838;
      font-size: 15px;
    }}

    .todo-item:last-child {{ border-bottom: none; }}

    .circle {{
      width: 18px;
      height: 18px;
      border: 1.5px solid #242424;
      border-radius: 50%;
      flex-shrink: 0;
    }}

    .empty {{
      color: #383838;
      font-size: 14px;
      padding: 8px 0;
    }}
  </style>
</head>
<body>
  <div class="date">{date_str}</div>
  <div class="greeting">Good morning, Luke.</div>

  {weather_html}

  <div class="quote">
    {quote}
    <div class="quote-author">— {author}</div>
  </div>

  <div class="events">
    <div class="label">Today</div>
    {events_html}
  </div>

  <div>
    <div class="label">To-do</div>
    <div class="todo-item"><div class="circle"></div>—</div>
    <div class="todo-item"><div class="circle"></div>—</div>
    <div class="todo-item"><div class="circle"></div>—</div>
  </div>
</body>
</html>"""


# ── Save & send ───────────────────────────────────────────────────────────────
def save_html(html):
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)


def send_sms(text):
    msg            = MIMEText(text)
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = SMS_GATEWAY
    msg["Subject"] = ""

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PW)
        server.send_message(msg)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    service        = get_calendar_service()
    events         = get_todays_events(service)
    temp, weather  = get_weather()
    quote, author  = random.choice(QUOTES)

    html = generate_html(events, temp, weather, quote, author)
    save_html(html)

    day = datetime.now().strftime("%A")
    send_sms(f"Good morning Luke. Your {day} brief: {PAGE_URL}")
    print("Done.")
