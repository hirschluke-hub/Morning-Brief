"""Google Calendar — fetches today's events using OAuth2 refresh token."""

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

PT = ZoneInfo("America/Los_Angeles")

COLOR_CATEGORIES = {
    "1":  ("Work",     "#b39ddb"),
    "10": ("School",   "#81c784"),
}


def get_calendar_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return build("calendar", "v3", credentials=creds)


def get_todays_events(service):
    now   = datetime.now(PT)
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
        color_id        = e.get("colorId", "")
        category, color = COLOR_CATEGORIES.get(color_id, ("Personal", "#80cbc4"))
        start_str       = e["start"].get("dateTime", e["start"].get("date", ""))
        end_str         = e["end"].get("dateTime",   e["end"].get("date", ""))
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
