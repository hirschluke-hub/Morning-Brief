"""Twilio SMS webhook — instant replies for todo commands."""

import os
from flask import Flask, Response, request
from todos import fetch_todos

app = Flask(__name__)


def twiml(msg):
    safe = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Response(
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Message>{safe}</Message></Response>',
        content_type="text/xml",
    )


def fmt_list(todos):
    if not todos:
        return "No todos. Text 'add <item>' to start."
    return "\n".join(f"{i+1}. {t}" for i, t in enumerate(todos))


@app.route("/sms", methods=["POST"])
def sms():
    body  = request.form.get("Body", "").strip()
    lower = body.lower().strip()

    if lower == "list":
        todos, _ = fetch_todos()
        return twiml(fmt_list(todos))

    elif lower.startswith("add "):
        item = body[4:].strip()
        if not item:
            return twiml("Usage: add <item>")
        # Fetch current list (item is already in history) to show updated state
        todos, _ = fetch_todos()
        return twiml(f"Added ✓\n\n{fmt_list(todos)}")

    elif lower.startswith("done "):
        try:
            n = int(lower[5:].strip())
        except ValueError:
            return twiml("Usage: done <number>  e.g. done 2")

        # Fetch before this message is fully processed to get the pre-removal list
        todos, _ = fetch_todos()
        if 1 <= n <= len(todos):
            removed = todos[n - 1]
            remaining = [t for i, t in enumerate(todos) if i != n - 1]
            reply = f"Removed: {removed}\n\n{fmt_list(remaining)}" if remaining else f"Removed: {removed}\n\nAll done!"
            return twiml(reply)
        else:
            return twiml(f"No item #{n}.\n\n{fmt_list(todos)}")

    elif lower == "clear":
        return twiml("Cleared ✓")

    else:
        return twiml("Commands:\nadd <item>\ndone <n>\nlist\nclear")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
