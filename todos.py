"""Shared todo parsing logic — reads Twilio message history and returns current list."""

import base64
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

TWILIO_SID    = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_TOKEN  = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_NUMBER = "+18588081672"


def fetch_todos(since_hours=48):
    """Return (todos, list_reply_to) by replaying inbound SMS commands."""
    print(f"DEBUG TWILIO_SID={TWILIO_SID!r} TWILIO_TOKEN={'set' if TWILIO_TOKEN else 'empty'}")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
        f"?To={urllib.parse.quote(TWILIO_NUMBER)}&PageSize=50"
    )
    print(f"DEBUG url={url}")
    creds = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()
    req   = urllib.request.Request(url, headers={"Authorization": f"Basic {creds}"})
    with urllib.request.urlopen(req, timeout=5) as r:
        data = json.loads(r.read())

    print(f"DEBUG SID prefix: {TWILIO_SID[:6]}")
    print(f"DEBUG total messages from API: {len(data.get('messages', []))}")
    for m in data.get("messages", []):
        print(f"DEBUG msg: dir={m.get('direction')} body={m.get('body','')[:30]!r}")

    msgs = []
    for m in data.get("messages", []):
        if m.get("direction") != "inbound":
            continue
        sent = parsedate_to_datetime(m["date_sent"])
        if sent >= cutoff:
            msgs.append({
                "text": m["body"].strip(),
                "time": sent,
                "from": m.get("from", ""),
            })
    msgs.sort(key=lambda x: x["time"])
    print(f"DEBUG inbound msgs in window: {[m['text'] for m in msgs]}")

    todos         = []
    list_reply_to = None

    for msg in msgs:
        text  = msg["text"]
        lower = text.lower().strip()

        if lower == "clear":
            todos         = []
            list_reply_to = None
        elif lower == "list":
            list_reply_to = msg["from"]
        elif lower.startswith("add "):
            item = text[4:].strip()
            if item:
                todos.append(item)
        elif lower.startswith("done "):
            try:
                n = int(lower[5:].strip())
                if 1 <= n <= len(todos):
                    todos.pop(n - 1)
            except ValueError:
                pass

    return todos, list_reply_to


def send_sms(to, body):
    url  = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    data = urllib.parse.urlencode({"From": TWILIO_NUMBER, "To": to, "Body": body}).encode()
    creds = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()
    req  = urllib.request.Request(url, data=data, headers={"Authorization": f"Basic {creds}"})
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"SMS send error: {e}")
