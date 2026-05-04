#!/usr/bin/env python3
"""Daily morning briefing — Google Calendar + Claude + SMS via Verizon gateway."""

import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

import anthropic
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ── Config ──────────────────────────────────────────────────────────────────
GMAIL_ADDRESS     = "hirschluke@gmail.com"
GMAIL_APP_PW      = os.environ.get("GMAIL_APP_PW", "nnkq bija eeyp utun")
SMS_GATEWAY       = "4254925800@vtext.com"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE   = os.path.join(SCRIPT_DIR, "briefing_log.txt")

# Google OAuth — loaded from env vars (GitHub Actions) or hardcoded fallback
GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID",     "763633570239-qnubdp4htilvdal2lf4de7r3b5tk8ikt.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "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")
GOOGLE_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN", "1//06W5GtjfxzER8CgYIARAAGAYSNwF-L9IrUwTpmHepvTVZT84TpHgBjrOqISPWxqCRBd6yvn0TncmXSiLK4U-9biA7jGaL_a8Dr64")

# Google Calendar colorId → category label
COLOR_CATEGORIES = {
    "1":  "Work",     # Lavender
    "10": "School",   # Basil
}

# ── Google Calendar ──────────────────────────────────────────────────────────
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
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
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
        color_id = e.get("colorId", "")
        category = COLOR_CATEGORIES.get(color_id, "Personal")
        start_str = e["start"].get("dateTime", e["start"].get("date", ""))
        end_str   = e["end"].get("dateTime",   e["end"].get("date", ""))
        events.append({
            "summary":  e.get("summary", "Untitled"),
            "start":    start_str,
            "end":      end_str,
            "category": category,
            "location": e.get("location", ""),
        })
    return events


# ── Briefing generation ──────────────────────────────────────────────────────
def fmt_time(dt_str):
    """Convert ISO datetime string to readable time like '10am' or '4:30pm'."""
    try:
        dt = datetime.fromisoformat(dt_str)
        hour = dt.strftime("%I").lstrip("0") or "12"
        minute = dt.strftime("%M")
        ampm = dt.strftime("%p").lower()
        return f"{hour}:{minute}{ampm}" if minute != "00" else f"{hour}{ampm}"
    except Exception:
        return dt_str


def build_events_text(events):
    if not events:
        return "No events today — free day!"

    grouped = {}
    for e in events:
        grouped.setdefault(e["category"], []).append(e)

    lines = []
    for category, items in grouped.items():
        lines.append(f"{category}:")
        for item in items:
            time_range = f"{fmt_time(item['start'])}–{fmt_time(item['end'])}"
            loc = f" @ {item['location'].split(',')[0]}" if item["location"] else ""
            lines.append(f"  • {item['summary']} {time_range}{loc}")
    return "\n".join(lines)


def generate_briefing(events):
    api_key = ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")
    today = datetime.now().strftime("%A, %B %d").replace(" 0", " ")
    events_text = build_events_text(events)

    if not api_key:
        # Fallback: simple template if no API key
        return f"Good morning Luke! {today}\n\n{events_text}\n\nMake it count today."

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=350,
        messages=[{
            "role": "user",
            "content": (
                f"Write a short morning briefing SMS for Luke. Today is {today}.\n\n"
                f"Events:\n{events_text}\n\n"
                "Format:\n"
                "1. Warm one-line greeting with date\n"
                "2. Events listed clearly (exact times and names)\n"
                "3. One sentence 'today's vibe' based on the schedule\n"
                "4. A short motivational quote relevant to what's ahead\n\n"
                "Keep it under 320 characters total. Energizing, not cheesy. No emojis."
            )
        }]
    )
    return message.content[0].text.strip()


# ── Send SMS ─────────────────────────────────────────────────────────────────
def send_sms(text):
    msg = MIMEText(text)
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = SMS_GATEWAY
    msg["Subject"] = ""

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PW)
        server.send_message(msg)


# ── Log ──────────────────────────────────────────────────────────────────────
def log_briefing(briefing):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*50}\n{timestamp}\n{briefing}\n")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    service  = get_calendar_service()
    events   = get_todays_events(service)
    briefing = generate_briefing(events)
    send_sms(briefing)
    log_briefing(briefing)
    print("Sent:\n", briefing)
