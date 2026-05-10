"""Twilio SMS webhook — processes todo commands and replies via ntfy push notification."""

import os
import urllib.request
from flask import Flask, Response, request
from sections.todos import fetch_todos

app = Flask(__name__)

NTFY_TOPIC = "luke-brief-x7k2m9"


def notify(title, body=""):
    try:
        req = urllib.request.Request(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=body.encode() if body else title.encode(),
            headers={"Title": title} if body else {},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"ntfy error: {e}")


def empty_twiml():
    return Response(
        '<?xml version="1.0" encoding="UTF-8"?><Response/>',
        content_type="text/xml",
    )


def fmt_list(todos):
    if not todos:
        return "No todos. Text 'add <item>' to start."
    return "\n".join(f"{i+1}. {t}" for i, t in enumerate(todos))


def safe_fetch():
    try:
        return fetch_todos()
    except Exception as e:
        print(f"fetch_todos error: {e}")
        notify("Morning Brief", f"Error fetching todos: {e}")
        return [], None


@app.route("/sms", methods=["POST"])
def sms():
    body  = request.form.get("Body", "").strip()
    lower = body.lower().strip()

    if lower == "list":
        todos, _ = safe_fetch()
        notify("To-Do List", fmt_list(todos))

    elif lower.startswith("add "):
        item = body[4:].strip()
        if not item:
            notify("Morning Brief", "Usage: add <item>")
        else:
            todos, _ = safe_fetch()
            notify("Added ✓", fmt_list(todos))

    elif lower.startswith("done "):
        try:
            n = int(lower[5:].strip())
        except ValueError:
            notify("Morning Brief", "Usage: done <number>  e.g. done 2")
        else:
            todos, _ = safe_fetch()
            if 1 <= n <= len(todos):
                removed = todos[n - 1]
                remaining = [t for i, t in enumerate(todos) if i != n - 1]
                msg = fmt_list(remaining) if remaining else "All done!"
                notify(f"Removed: {removed}", msg)
            else:
                notify("Morning Brief", f"No item #{n}.\n\n{fmt_list(todos)}")

    elif lower == "clear":
        notify("Morning Brief", "List cleared ✓")

    else:
        notify("Morning Brief", "Commands:\nadd <item>\ndone <n>\nlist\nclear")

    return empty_twiml()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
