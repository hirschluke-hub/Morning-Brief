"""Newsletter news — fetches Morning Digest emails from Gmail, curates with Claude."""

import base64
import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import anthropic
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

MORNING_DIGEST_LABEL_NAME = "Morning Digest"
MAX_CHARS_PER_EMAIL       = 3000
MAX_ARTICLES_PER_EMAIL    = 5
MAX_CHARS_PER_ARTICLE     = 4000

_SKIP_PATTERNS = {
    "unsubscribe", "optout", "opt-out", "manage-subscription", "preferences",
    "mailto:", "javascript:",
    "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "youtube.com", "tiktok.com",
    "apple.com/app", "play.google.com",
}

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

Below are today's morning newsletters. Each newsletter preview is followed by full article content \
where available — use the article text for deeper context and more accurate summaries.

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


def _get_label_id(service):
    """Find the Morning Digest label ID by name. Handles nested labels (e.g. Personal/Morning Digest)."""
    result = service.users().labels().list(userId="me").execute()
    labels = result.get("labels", [])
    target = MORNING_DIGEST_LABEL_NAME.lower()
    for label in labels:
        name = label.get("name", "")
        if name.lower() == target or name.lower().endswith("/" + target):
            print(f"News: found label '{name}' → {label['id']}")
            return label["id"]
    names = [l.get("name", "") for l in labels]
    print(f"News: label '{MORNING_DIGEST_LABEL_NAME}' not found. Available labels: {names}")
    return None


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


def _extract_html_body(payload):
    """Return raw HTML from the email payload so we can pull links before stripping."""
    mime = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime == "text/html" and body_data:
        return _decode(body_data)

    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/html":
            data = part.get("body", {}).get("data", "")
            if data:
                return _decode(data)
    for part in parts:
        result = _extract_html_body(part)
        if result:
            return result
    return ""


def _extract_links(html):
    """Pull unique article URLs from raw email HTML, filtering junk links."""
    hrefs = re.findall(r'href=["\']([^"\'>\s]+)["\']', html, re.IGNORECASE)
    seen, links = set(), []
    for url in hrefs:
        if not url.startswith("http"):
            continue
        url_lower = url.lower()
        if any(pat in url_lower for pat in _SKIP_PATTERNS):
            continue
        if "#" in url:
            continue
        if url not in seen:
            seen.add(url)
            links.append(url)
    return links


def _fetch_article(url):
    """Fetch a URL and return stripped plain text, or None on failure."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            html = r.read().decode("utf-8", errors="replace")
        text = _strip_html(html)
        return text[:MAX_CHARS_PER_ARTICLE] if text else None
    except Exception:
        return None


def _fetch_articles_parallel(links):
    """Fetch up to MAX_ARTICLES_PER_EMAIL article pages concurrently."""
    results = {}
    with ThreadPoolExecutor(max_workers=MAX_ARTICLES_PER_EMAIL) as pool:
        futures = {pool.submit(_fetch_article, url): url for url in links[:MAX_ARTICLES_PER_EMAIL]}
        for future in as_completed(futures):
            url = futures[future]
            text = future.result()
            if text:
                results[url] = text
    return results


def _fetch_newsletters():
    service = _get_gmail_service()

    label_id = _get_label_id(service)
    if not label_id:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    after = cutoff.strftime("%Y/%m/%d")

    result = service.users().messages().list(
        userId="me",
        labelIds=[label_id],
        q=f"after:{after}",
        maxResults=15,
    ).execute()

    refs = result.get("messages", [])
    print(f"News: {len(refs)} message(s) found in '{MORNING_DIGEST_LABEL_NAME}' since {after}")

    newsletters = []
    for ref in refs:
        try:
            msg = service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
            payload  = msg.get("payload", {})
            headers  = {h["name"]: h["value"] for h in payload.get("headers", [])}
            sender   = headers.get("From", "")
            subject  = headers.get("Subject", "")
            text     = _extract_text(payload)
            raw_html = _extract_html_body(payload)
            links    = _extract_links(raw_html) if raw_html else []
            print(f"News: '{subject}' — {len(text)} chars, {len(links)} links found")
            articles = _fetch_articles_parallel(links)
            print(f"News: fetched {len(articles)} article(s) successfully")
            if text or articles:
                newsletters.append({
                    "sender":   sender,
                    "subject":  subject,
                    "content":  text[:MAX_CHARS_PER_EMAIL],
                    "articles": articles,
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

    sections = []
    for n in newsletters:
        parts = [f"FROM: {n['sender']}\nSUBJECT: {n['subject']}\n\nNEWSLETTER PREVIEW:\n{n['content']}"]
        for url, text in n["articles"].items():
            parts.append(f"ARTICLE ({url}):\n{text}")
        sections.append("\n\n".join(parts))
    newsletter_text = "\n\n---\n\n".join(sections)

    print(f"News: sending {len(newsletter_text)} chars to Claude for curation")
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
        print(f"News: Claude returned {len(articles)} article(s)")
        if articles:
            return articles
        return []
    except Exception as e:
        print(f"News: Claude curation error — {e}")
        return []
