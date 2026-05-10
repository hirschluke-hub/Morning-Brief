"""CRE news — fetches candidates from RSS then uses Claude to curate and summarize."""

import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import anthropic

CANDIDATE_FEEDS = {
    "CRE / Capital Markets":    "https://news.google.com/rss/search?q=commercial+real+estate+capital+markets+CMBS+lending+acquisitions&hl=en-US&gl=US&ceid=US:en",
    "Development / Multifamily": "https://news.google.com/rss/search?q=multifamily+development+industrial+office+retail+real+estate+deal&hl=en-US&gl=US&ceid=US:en",
    "San Diego":                "https://news.google.com/rss/search?q=san+diego+real+estate+development+zoning+business&hl=en-US&gl=US&ceid=US:en",
    "Proptech / AI":            "https://news.google.com/rss/search?q=proptech+AI+real+estate+data+center+technology&hl=en-US&gl=US&ceid=US:en",
    "Markets / Economy":        "https://news.google.com/rss/search?q=interest+rates+federal+reserve+economy+real+estate+investors+tariffs&hl=en-US&gl=US&ceid=US:en",
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
- Return 3 to 5 articles. Always return at least 3 if candidates are available.
- Minimum relevance score: 7/10
- Prefer articles from the last 24–72 hours
- Exclude: celebrity news, sports, crime, generic politics, repetitive coverage of the same story
- Rank by: relevance to user → importance → CRE/investing impact → timeliness → uniqueness

Here are today's candidate articles (index | title | source | description snippet):

{candidates}

Return ONLY a valid JSON object — no markdown, no explanation:
{{
  "articles": [
    {{
      "title": "exact headline",
      "source": "publication name",
      "link": "url",
      "score": 9,
      "category": "CRE Capital Markets",
      "summary": "2-3 sentence analyst summary written for a sharp young CRE investor",
      "why_it_matters": "1 sentence on why this matters to Luke specifically",
      "tags": ["tag1", "tag2", "tag3"]
    }}
  ]
}}"""


def _fetch_candidates(hours=72):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    candidates = []
    seen = set()

    for label, feed_url in CANDIDATE_FEEDS.items():
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                root = ET.fromstring(r.read())
            for item in root.findall(".//item"):
                title    = (item.findtext("title") or "").strip()
                link     = (item.findtext("link") or "").strip()
                desc     = (item.findtext("description") or "").strip()
                pub_date = item.findtext("pubDate") or ""

                if not title:
                    continue
                key = title[:50].lower()
                if key in seen:
                    continue

                try:
                    published = parsedate_to_datetime(pub_date)
                    if published < cutoff:
                        continue
                except Exception:
                    pass  # include if date unparseable

                seen.add(key)
                candidates.append({"title": title, "link": link, "desc": desc[:180], "source": label})
        except Exception as e:
            print(f"Feed error ({label}): {e}")

    return candidates[:50]


def _fallback_articles(candidates, n=5):
    """Return raw candidates as minimal article dicts when Claude is unavailable."""
    return [
        {
            "title":         a["title"],
            "source":        a["source"],
            "link":          a["link"],
            "score":         "",
            "category":      a["source"],
            "summary":       a["desc"],
            "why_it_matters": "",
            "tags":          [],
        }
        for a in candidates[:n]
    ]


def get_news():
    candidates = _fetch_candidates()
    if not candidates:
        print("News: no candidates fetched from RSS feeds")
        return []

    candidate_text = "\n".join(
        f"{i+1}. {a['title']} | {a['source']} | {a['desc'][:140]}"
        for i, a in enumerate(candidates)
    )

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": CURATION_PROMPT.format(candidates=candidate_text)}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
            if raw.endswith("```"):
                raw = raw[:-3]
        articles = json.loads(raw).get("articles", [])
        if articles:
            return articles
        print("News: Claude returned 0 articles — using fallback")
        return _fallback_articles(candidates)
    except Exception as e:
        print(f"News: Claude curation error — {e} — using fallback")
        return _fallback_articles(candidates)
