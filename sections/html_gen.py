"""HTML generation — builds the full morning brief page."""

from datetime import datetime

from sections.gcal import fmt_time


def _weather_icon(desc):
    d = (desc or "").lower()
    if "thunder" in d:
        return '<svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 16H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z"/><polyline points="13 11 11 15 14 15 12 19"/></svg>'
    elif "rain" in d or "drizzle" in d or "shower" in d:
        return '<svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="#7aafc9" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 16H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z"/><line x1="8" y1="19" x2="8" y2="21"/><line x1="12" y1="19" x2="12" y2="21"/><line x1="16" y1="19" x2="16" y2="21"/></svg>'
    elif "fog" in d:
        return '<svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="#777" stroke-width="1.4" stroke-linecap="round"><line x1="3" y1="8" x2="21" y2="8"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="5" y1="16" x2="19" y2="16"/></svg>'
    elif "overcast" in d:
        return '<svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="#888" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z"/></svg>'
    elif "partly" in d:
        return '<svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="10" cy="9" r="3" stroke="#d4a843"/><line x1="10" y1="3" x2="10" y2="5" stroke="#d4a843"/><line x1="16" y1="9" x2="14" y2="9" stroke="#d4a843"/><line x1="4" y1="9" x2="6" y2="9" stroke="#d4a843"/><line x1="14.24" y1="4.76" x2="12.83" y2="6.17" stroke="#d4a843"/><line x1="5.76" y1="4.76" x2="7.17" y2="6.17" stroke="#d4a843"/><path d="M16 19H9a5 5 0 1 1 4.78-6.47A3.5 3.5 0 1 1 16 19z" stroke="#888"/></svg>'
    else:
        return '<svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="#d4a843" stroke-width="1.4" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="2" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22" y2="12"/><line x1="4.93" y1="4.93" x2="6.34" y2="6.34"/><line x1="17.66" y1="17.66" x2="19.07" y2="19.07"/><line x1="19.07" y1="4.93" x2="17.66" y2="6.34"/><line x1="6.34" y1="17.66" x2="4.93" y2="19.07"/></svg>'


def generate_html(events, todos, temp, weather_desc, quote, author, image_url, news=None, russian=None):
    today        = datetime.now()
    day_name     = today.strftime("%A").upper()
    date_display = today.strftime("%B %d, %Y").replace(" 0", " ")
    weather_str      = f"{temp}°" if temp else ""
    weather_desc_str = weather_desc if weather_desc else ""

    weather_icon = _weather_icon(weather_desc)

    if temp is None:
        temp_color = "#444"
    elif temp <= 65:
        temp_color = "#FFCC80"
    elif temp <= 70:
        temp_color = "#FFA040"
    elif temp <= 75:
        temp_color = "#FF7A00"
    elif temp <= 80:
        temp_color = "#FF4C4C"
    elif temp <= 85:
        temp_color = "#D92020"
    else:
        temp_color = "#A00000"

    if events:
        rows = ""
        for e in events:
            start_t    = fmt_time(e["start"])
            end_t      = fmt_time(e["end"])
            time_range = start_t if start_t == "All day" else f"{start_t} — {end_t}"
            try:
                if "T" in e["start"] and "T" in e["end"]:
                    dt_start = datetime.fromisoformat(e["start"])
                    dt_end   = datetime.fromisoformat(e["end"])
                    mins     = (dt_end - dt_start).total_seconds() / 60
                    height   = max(52, round(mins / 60 * 30))
                else:
                    height = 62
            except Exception:
                height = 62
            rows += f"""
          <div class="event" style="border-left-color:{e['color']};min-height:{height}px;">
            <div class="event-time">{time_range}</div>
            <div class="event-name">{e['summary']}</div>
            <div class="event-category" style="color:{e['color']}">{e['category']}</div>
          </div>"""
        events_html = rows
    else:
        events_html = '<div class="empty">Free day — make it yours.</div>'

    if russian:
        r_word        = russian.get('russian', '')
        r_translit    = russian.get('transliteration', '')
        r_english     = russian.get('english', '')
        r_explanation = russian.get('explanation', '')
        r_audio       = russian.get('audio_file', '')
        if r_audio:
            audio_html = f'<audio id="russian-audio" src="Russian Words/{r_audio}.mp3" preload="auto"></audio><button class="russian-pronounce" onclick="document.getElementById(\'russian-audio\').play()">&#9654; Pronounce</button>'
        else:
            audio_html = f'<button class="russian-pronounce" onclick="(function(){{var u=new SpeechSynthesisUtterance(\'{r_word}\');u.lang=\'ru-RU\';u.rate=0.8;window.speechSynthesis.speak(u);}})()">&#9654; Pronounce</button>'
        russian_html = f"""
      <div class="russian-word">{r_word}</div>
      <div class="russian-translit">{r_translit}</div>
      <div class="russian-english">{r_english}</div>
      {audio_html}
      <div class="russian-expand" onclick="var b=this.nextElementSibling;var open=b.style.display==='block';b.style.display=open?'none':'block';this.querySelector('.russian-plus').textContent=open?'+':'−';">
        <span class="russian-expand-label">Explanation</span>
        <span class="russian-plus">+</span>
      </div>
      <div class="russian-explanation">{r_explanation}</div>"""
    else:
        russian_html = '<div class="empty">No word today.</div>'

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
    <div class="news-item">
      <div class="news-toggle" onclick="var b=this.nextElementSibling;var open=b.style.display==='block';b.style.display=open?'none':'block';this.querySelector('.news-plus').textContent=open?'+':'−';">
        <span class="news-title">{a["title"]}</span>
        <span class="news-plus">+</span>
      </div>
      <div class="news-body">
        {f'<p class="news-summary-text">{summary}</p>' if summary else ""}
        {f'<p class="news-why-text">Why it matters: {why}</p>' if why else ""}
        <div class="news-source-note">Find it in your <strong>{source}</strong> email.{(" " + link_html) if link_html else ""}</div>
      </div>
    </div>""")
        news_html = "".join(items)
    else:
        news_html = '<div class="empty">No stories cleared the bar today.</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
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

    .temp-bar {{
      width: 4px;
      height: 52px;
      border-radius: 2px;
      flex-shrink: 0;
    }}

    .weather-icon {{
      margin-left: auto;
      opacity: 0.9;
      display: flex;
      align-items: center;
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

    /* ── Russian Word ── */
    .russian-section {{
      border-bottom: 1px solid #1c1c1c;
      padding: 28px 32px;
    }}

    .russian-inner {{
      max-width: 860px;
      margin: 0 auto;
    }}

    .russian-word {{
      font-size: 42px;
      font-weight: 300;
      color: #fff;
      letter-spacing: 1px;
      margin-bottom: 6px;
      line-height: 1.1;
    }}

    .russian-translit {{
      font-size: 16px;
      color: #80cbc4;
      font-style: italic;
      margin-bottom: 4px;
      letter-spacing: 0.5px;
    }}

    .russian-english {{
      font-size: 13px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 2px;
      color: #666;
      margin-bottom: 14px;
    }}

    .russian-expand {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 14px;
      cursor: pointer;
      user-select: none;
      width: fit-content;
    }}

    .russian-expand-label {{
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      color: #444;
    }}

    .russian-plus {{
      font-size: 16px;
      color: #444;
    }}

    .russian-expand:hover .russian-expand-label,
    .russian-expand:hover .russian-plus {{ color: #666; }}

    .russian-explanation {{
      display: none;
      font-size: 14px;
      color: #777;
      line-height: 1.65;
      max-width: 600px;
      margin-top: 12px;
    }}

    .russian-pronounce {{
      background: none;
      border: 1px solid #2a2a2a;
      color: #666;
      font-size: 12px;
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
      letter-spacing: 0.5px;
      transition: border-color 0.15s, color 0.15s;
    }}

    .russian-pronounce:hover {{
      border-color: #80cbc4;
      color: #80cbc4;
    }}

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
      cursor: pointer;
      user-select: none;
    }}

    .news-title {{
      font-size: 15px;
      font-weight: 500;
      color: #c8c8c8;
      line-height: 1.45;
    }}

    .news-plus {{
      font-size: 18px;
      color: #444;
      flex-shrink: 0;
      transition: color 0.15s;
    }}

    .news-toggle:hover .news-title {{ color: #fff; }}
    .news-toggle:hover .news-plus {{ color: #666; }}

    .news-body {{
      display: none;
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
    <div class="temp-bar" style="background:{temp_color};"></div>
    <div class="weather-temp-big">{weather_str}</div>
    <div class="weather-right">
      <div class="weather-condition">{weather_desc_str}</div>
      <div class="weather-location">San Diego, CA — Today's High</div>
    </div>
    <div class="weather-icon">{weather_icon}</div>
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

  <div class="russian-section">
    <div class="russian-inner">
      <div class="label">Russian Word of the Day</div>
      {russian_html}
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
