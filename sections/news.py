"""CRE news — fetches articles from the last 24 hours from free RSS feeds."""

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

NEWS_FEEDS = {
    "Multifamily Dive":  "https://www.multifamilydive.com/feeds/news/",
    "Connect CRE":       "https://www.connectcre.com/feed/",
    "REBusiness Online": "https://rebusinessonline.com/feed/",
    "Bisnow":            "https://www.bisnow.com/rss",
}

NEWS_KEYWORDS = {
    "san diego":          3,
    "multifamily":        3,
    "multi-family":       3,
    "apartment":          2,
    "apartments":         2,
    "mixed-use":          1,
    "mixed use":          1,
    "affordable housing": 2,
    "cap rate":           1,
}


def get_news(max_articles=5):
    cutoff   = datetime.now(timezone.utc) - timedelta(hours=24)
    articles = []

    for source, feed_url in NEWS_FEEDS.items():
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                root = ET.fromstring(r.read())
            for item in root.findall(".//item"):
                pub_date = item.findtext("pubDate") or ""
                try:
                    published = parsedate_to_datetime(pub_date)
                except Exception:
                    continue
                if published < cutoff:
                    continue

                title = item.findtext("title") or ""
                desc  = item.findtext("description") or ""
                link  = item.findtext("link") or ""
                text  = (title + " " + desc).lower()
                score = sum(v for k, v in NEWS_KEYWORDS.items() if k in text)
                if score >= 3:
                    articles.append({"title": title.strip(), "link": link.strip(), "source": source, "score": score})
        except Exception as e:
            print(f"News feed error ({source}): {e}")

    articles.sort(key=lambda x: x["score"], reverse=True)
    seen, unique = set(), []
    for a in articles:
        key = a["title"][:50].lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique[:max_articles]
