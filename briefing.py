#!/usr/bin/env python3
"""Daily morning briefing — generates web page + sends push notification."""

import os
import subprocess
import urllib.request
from datetime import datetime

from sections.gcal    import get_calendar_service, get_todays_events
from sections.html_gen import generate_html
from sections.news    import get_news
from sections.quotes  import get_quote
from sections.russian import get_russian_word
from sections.todos   import get_todos
from sections.weather import get_weather

NTFY_TOPIC = "luke-brief-x7k2m9"
PAGE_URL   = "https://hirschluke-hub.github.io/Morning-Brief/"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR   = os.path.join(SCRIPT_DIR, "docs")
HTML_FILE  = os.path.join(DOCS_DIR, "index.html")


def save_html(html):
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)


def send_notification(title, body):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=body.encode(),
        headers={"Title": title, "Click": PAGE_URL, "Priority": "high"},
    )
    urllib.request.urlopen(req, timeout=5)


def publish_page():
    today = datetime.now().strftime("%Y-%m-%d")
    cmds = [
        ["git", "config", "user.name", "Morning Brief"],
        ["git", "config", "user.email", "action@github.com"],
        ["git", "add", "docs/index.html"],
        ["git", "commit", "-m", f"Daily brief {today}"],
        ["git", "push"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True)
        if result.returncode != 0 and cmd[1] != "commit":
            print(f"git error ({' '.join(cmd)}): {result.stderr.strip()}")


if __name__ == "__main__":
    service       = get_calendar_service()
    events        = get_todays_events(service)
    todos         = get_todos()
    temp, weather = get_weather()
    quote, author, image_url = get_quote()
    news          = get_news()
    russian       = get_russian_word()

    html = generate_html(events, todos, temp, weather, quote, author, image_url, news, russian)
    save_html(html)

    day = datetime.now().strftime("%A")
    publish_page()
    send_notification("Morning Brief", f"Good morning Luke. Your {day} brief is ready.")
    print("Done.")
