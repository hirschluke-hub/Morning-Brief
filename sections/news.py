"""Newsletter news — fetches Morning Digest emails from Gmail, curates with Claude."""

import base64
import json
import os
import re
from datetime import datetime, timedelta, timezone

import anthropic
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

MORNING_DIGEST_LABEL = "Label_4467215843786575600"
MAX_CHARS_PER_EMAIL = 3000

CURATION_PROMPT = """\
You are a sharp CRE analyst briefing a real estate graduate student each morning.

User profile:
- Real estate graduate student in San Diego
- Focused on: commercial real estate, development, acquisitions, capital markets, AI in CRE, long-term investing

Priority areas (ranked):
1. CRE capital markets — deals, CMBS, lending, cap rates, interest rates, distressed assets, construction costs, \
institutional acquisitions/dispositions, major leases, office/multifamily/industrial/retail development, \
proptech/AI in real estate, data centers, energy infrastructure
2. San Diego business/real estate — major developments, zoning, housing policy, life sciences, \
downtown/UTC/La Jolla/Del Mar/North County, major employer moves, infrastructure/transit
3. Big national business/political news — only if large enough to affect markets, real estate, lending, \
taxes, energy, labor, or investor sentiment

Selection rules:
- Return 3 to 5 articles. Always return at least 3 if content is available.
- Minimum relevance score: 7/10
- Exclude: celebrity news, sports, crime, generic politics, repetitive coverage, ads, event promotions
- Rank by: relevance to user → importance → CRE/investing impact → timeliness → uniqueness

Below are the contents of today's morning newsletters. Extract and summarize the most relevant stories.

{newsletters}

Return ONLY a valid JSON object — no markdown, no explanation:
{{
  "articles": [
    {{
      "title": "clear headline summarizing the story",
      "source": "newsletter name",
      "link": "url if present, else empty string",
      "score": 9,
      "category": "CRE Capital Markets",
      "summary": "2-3 sentence analyst summary written for a sharp young CRE investor",
      "why_it_matters": "1 sentence on why this matters to Luke specifically",
      "tags": ["tag1", "tag2", "tag3"]
    }}
  ]
}}"""


def _get_gmail_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def _decode(data):
    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")


def _strip_html(html):
    html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', html)
    for entity, char in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                         ('&nbsp;', ' '), ('&#39;', "'"), ('&quot;', '"')]:
        text = text.replace(entity, char)
    return re.sub(r'\s+', ' ', text).strip()


def _extract_text(payload):
    mime = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime == "text/plain" and body_data:
        return _decode(body_data)
    if mime == "text/html" and body_data:
        return _strip_html(_decode(body_data))

    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain":
            text = _extract_text(part)
            if text:
                return text
    for part in parts:
        text = _extract_text(part)
        if text:
            return text
    return ""


def _fetch_newsletters():
    service = _get_gmail_service()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    after = cutoff.strftime("%Y/%m/%d")

    result = service.users().messages().list(
        userId="me",
        labelIds=[MORNING_DIGEST_LABEL],
        q=f"after:{after}",
        maxResults=15,
    ).execute()

    newsletters = []
    for ref in result.get("messages", []):
        try:
            msg = service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
            payload = msg.get("payload", {})
            headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
            sender  = headers.get("From", "")
            subject = headers.get("Subject", "")
            text    = _extract_text(payload)
            if text:
                newsletters.append({
                    "sender":  sender,
                    "subject": subject,
                    "content": text[:MAX_CHARS_PER_EMAIL],
                })
        except Exception as e:
            print(f"Gmail: error reading message {ref['id']}: {e}")

    return newsletters


def get_news():
    try:
        newsletters = _fetch_newsletters()
    except Exception as e:
        print(f"News: Gmail fetch failed — {e}")
        return []

    if not newsletters:
        print("News: no newsletters found in Morning Digest")
        return []

    newsletter_text = "\n\n---\n\n".join(
        f"FROM: {n['sender']}\nSUBJECT: {n['subject']}\n\n{n['content']}"
        for n in newsletters
    )

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": CURATION_PROMPT.format(newsletters=newsletter_text)}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
            if raw.endswith("```"):
                raw = raw[:-3]
        articles = json.loads(raw).get("articles", [])
        if articles:
            return articles
        print("News: Claude returned 0 articles")
        return []
    except Exception as e:
        print(f"News: Claude curation error — {e}")
        return []
