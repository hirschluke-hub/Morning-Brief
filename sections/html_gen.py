"""HTML generation — builds the full morning brief page."""

from datetime import datetime

from sections.gcal import fmt_time


def generate_html(events, todos, temp, weather_desc, quote, author, image_url, news=None):
    today        = datetime.now()
    day_name     = today.strftime("%A").upper()
    date_display = today.strftime("%B %-d, %Y")
    weather_str      = f"{temp}°" if temp else ""
    weather_desc_str = weather_desc if weather_desc else ""

    if events:
        rows = ""
        for e in events:
            start_t    = fmt_time(e["start"])
            end_t      = fmt_time(e["end"])
            time_range = start_t if start_t == "All day" else f"{start_t} — {end_t}"
            rows += f"""
          <div class="event" style="border-left-color:{e['color']}">
            <div class="event-time">{time_range}</div>
            <div class="event-name">{e['summary']}</div>
            <div class="event-category" style="color:{e['color']}">{e['category']}</div>
          </div>"""
        events_html = rows
    else:
        events_html = '<div class="empty">Free day — make it yours.</div>'

    if todos:
        todos_html = "".join(
            f'<div class="todo-item"><div class="circle"></div>{item}</div>'
            for item in todos
        )
    else:
        todos_html = '<div class="empty">add &lt;item&gt; &nbsp;·&nbsp; done &lt;n&gt; &nbsp;·&nbsp; list &nbsp;·&nbsp; clear</div>'

    if news:
        items = []
        for a in news:
            summary = a.get("summary", "")
            why     = a.get("why_it_matters", "")
            source  = a.get("source", "")
            link    = a.get("link", "")
            link_html = (
                f'<a class="news-article-link" href="{link}" target="_blank" rel="noopener">Try article →</a>'
                if link else ""
            )
            items.append(f"""
    <details class="news-item">
      <summary class="news-toggle">{a["title"]}</summary>
      <div class="news-body">
        {f'<p class="news-summary-text">{summary}</p>' if summary else ""}
        {f'<p class="news-why-text">Why it matters: {why}</p>' if why else ""}
        <div class="news-source-note">Find it in your <strong>{source}</strong> email.{(" " + link_html) if link_html else ""}</div>
      </div>
    </details>""")
        news_html = "".join(items)
    else:
        news_html = '<div class="empty">No stories cleared the bar today.</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Morning Brief</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: #0d0d0d;
      color: #e0e0e0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, sans-serif;
      min-height: 100vh;
    }}

    /* ── Hero ── */
    .hero {{
      position: relative;
      width: 100%;
      height: 60vh;
      min-height: 360px;
      background: #1a1a1a url('{image_url}') center/cover no-repeat;
    }}

    .hero-overlay {{
      position: absolute;
      inset: 0;
      background: linear-gradient(
        to bottom,
        rgba(0,0,0,0.3) 0%,
        rgba(0,0,0,0.1) 35%,
        rgba(0,0,0,0.85) 100%
      );
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 28px 32px 36px;
    }}

    .hero-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}

    .greeting {{
      font-size: 13px;
      font-weight: 500;
      letter-spacing: 2.5px;
      text-transform: uppercase;
      color: rgba(255,255,255,0.55);
      text-shadow: 0 1px 4px rgba(0,0,0,0.5);
    }}

    .hero-bottom {{ }}

    .hero-day {{
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 3px;
      color: rgba(255,255,255,0.38);
      text-transform: uppercase;
      margin-bottom: 6px;
    }}

    .hero-date {{
      font-size: 38px;
      font-weight: 700;
      color: #fff;
      letter-spacing: -0.5px;
      text-shadow: 0 2px 12px rgba(0,0,0,0.6);
      margin-bottom: 18px;
      line-height: 1;
    }}

    .hero-quote {{
      font-size: 16px;
      font-style: italic;
      color: rgba(255,255,255,0.85);
      line-height: 1.6;
      text-shadow: 0 1px 4px rgba(0,0,0,0.6);
      max-width: 500px;
    }}

    .hero-author {{
      margin-top: 8px;
      font-size: 12px;
      color: rgba(255,255,255,0.38);
      text-shadow: 0 1px 3px rgba(0,0,0,0.5);
      letter-spacing: 0.5px;
    }}

    /* ── Weather ── */
    .weather-strip {{
      background: #111;
      border-bottom: 1px solid #1c1c1c;
      padding: 24px 32px;
      display: flex;
      align-items: center;
      gap: 20px;
    }}

    .weather-temp-big {{
      font-size: 52px;
      font-weight: 200;
      color: #f0f0f0;
      line-height: 1;
    }}

    .weather-right {{}}

    .weather-condition {{
      font-size: 16px;
      color: #aaa;
      font-weight: 400;
    }}

    .weather-location {{
      font-size: 12px;
      color: #3a3a3a;
      margin-top: 4px;
      text-transform: uppercase;
      letter-spacing: 1.5px;
    }}

    /* ── Content ── */
    .content {{
      max-width: 860px;
      margin: 0 auto;
      padding: 36px 32px 64px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 40px;
    }}

    @media (max-width: 600px) {{
      .content {{ grid-template-columns: 1fr; gap: 32px; padding: 28px 20px 56px; }}
      .hero-date {{ font-size: 28px; }}
    }}

    .label {{
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 2.5px;
      color: #888;
      font-weight: 600;
      margin-bottom: 16px;
    }}

    /* ── Event cards ── */
    .event {{
      background: #111;
      border-radius: 12px;
      border-left: 4px solid #444;
      padding: 14px 16px;
      margin-bottom: 10px;
    }}

    .event-time {{
      font-size: 19px;
      font-weight: 700;
      color: #fff;
      line-height: 1;
      margin-bottom: 5px;
    }}

    .event-name {{
      font-size: 14px;
      color: #888;
      line-height: 1.35;
      margin-bottom: 5px;
    }}

    .event-category {{
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      opacity: 0.7;
    }}

    /* ── To-Do ── */
    .todo-item {{
      display: flex;
      align-items: center;
      gap: 14px;
      background: #111;
      border-radius: 12px;
      border-left: 4px solid #e8e8e8;
      padding: 14px 16px;
      margin-bottom: 10px;
      font-size: 15px;
      font-weight: 500;
      color: #e8e8e8;
    }}

    .circle {{
      width: 18px;
      height: 18px;
      border: 2px solid #e8e8e8;
      border-radius: 50%;
      flex-shrink: 0;
    }}

    .empty {{ color: #383838; font-size: 14px; padding: 8px 0; }}

    /* ── News ── */
    .news-section {{
      border-top: 1px solid #1c1c1c;
      padding: 28px 32px 48px;
    }}

    .news-inner {{
      max-width: 860px;
      margin: 0 auto;
    }}

    .news-item {{
      border-bottom: 1px solid #1a1a1a;
    }}

    .news-toggle {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 0;
      font-size: 15px;
      font-weight: 500;
      color: #c8c8c8;
      cursor: pointer;
      list-style: none;
      line-height: 1.45;
    }}

    .news-toggle::-webkit-details-marker {{ display: none; }}

    .news-toggle::after {{
      content: '+';
      font-size: 16px;
      color: #444;
      flex-shrink: 0;
    }}

    .news-item[open] .news-toggle::after {{ content: '−'; color: #666; }}

    .news-toggle:hover {{ color: #fff; }}

    .news-body {{
      padding: 2px 0 18px;
    }}

    .news-summary-text {{
      font-size: 13px;
      color: #888;
      line-height: 1.6;
      margin-bottom: 10px;
    }}

    .news-why-text {{
      font-size: 12px;
      color: #555;
      line-height: 1.5;
      font-style: italic;
      margin-bottom: 12px;
    }}

    .news-source-note {{
      font-size: 12px;
      color: #444;
    }}

    .news-source-note strong {{ color: #666; }}

    .news-article-link {{
      color: #5a7a8a;
      text-decoration: none;
      font-size: 12px;
    }}

    .news-article-link:hover {{ color: #80cbc4; }}

    .bottom {{
      text-align: center;
      padding: 0 32px 56px;
      font-size: 13px;
      color: #2e2e2e;
      font-style: italic;
      letter-spacing: 0.3px;
    }}
  </style>
</head>
<body>

  <div class="hero">
    <div class="hero-overlay">
      <div class="hero-top">
        <div class="greeting">Good morning, Luke.</div>
      </div>
      <div class="hero-bottom">
        <div class="hero-day">{day_name}</div>
        <div class="hero-date">{date_display}</div>
        <div class="hero-quote">"{quote}"</div>
        <div class="hero-author">— {author}</div>
      </div>
    </div>
  </div>

  <div class="weather-strip">
    <div class="weather-temp-big">{weather_str}</div>
    <div class="weather-right">
      <div class="weather-condition">{weather_desc_str}</div>
      <div class="weather-location">San Diego, CA — Today's High</div>
    </div>
  </div>

  <div class="content">
    <div>
      <div class="label">Today's Schedule</div>
      {events_html}
    </div>
    <div>
      <div class="label">To-Do</div>
      {todos_html}
    </div>
  </div>

  <div class="news-section">
    <div class="news-inner">
      <div class="label">Top Stories</div>
      {news_html}
    </div>
  </div>

  <div class="bottom">You're building the life you dreamed of. Keep going.</div>

</body>
</html>"""
