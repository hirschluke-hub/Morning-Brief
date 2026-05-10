"""CRE news — pulls yesterday's headlines via Google News RSS search queries."""

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

NEWS_QUERIES = {
    "Multifamily":           "multifamily+apartments+real+estate",
    "CRE":                   "commercial+real+estate+CRE+deal",
    "San Diego Real Estate": "san+diego+real+estate+housing",
}

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

BOOST_KEYWORDS = {
    "san diego":          3,
    "multifamily":        2,
    "multi-family":       2,
    "apartment":          1,
    "apartments":         1,
    "mixed-use":          1,
    "affordable housing": 2,
    "cap rate":           1,
    "deal":               1,
}


def get_news(max_articles=6):
    cutoff   = datetime.now(timezone.utc) - timedelta(hours=24)
    articles = []

    for label, query in NEWS_QUERIES.items():
        url = GOOGLE_NEWS_RSS.format(query=query)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                root = ET.fromstring(r.read())
            for item in root.findall(".//item"):
                pub_date = item.findtext("pubDate") or ""
                try:
                    published = parsedate_to_datetime(pub_date)
                    if published < cutoff:
                        continue
                except Exception:
                    pass  # include if date can't be parsed

                title = item.findtext("title") or ""
                link  = item.findtext("link") or ""
                desc  = item.findtext("description") or ""
                text  = (title + " " + desc).lower()
                score = sum(v for k, v in BOOST_KEYWORDS.items() if k in text)
                articles.append({"title": title.strip(), "link": link.strip(), "source": label, "score": score})
        except Exception as e:
            print(f"News feed error ({label}): {e}")

    articles.sort(key=lambda x: x["score"], reverse=True)
    seen, unique = set(), []
    for a in articles:
        key = a["title"][:50].lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique[:max_articles]
