import os
import re
import html
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

INPUT_URL = "https://www.expressentertainment.tv/etv-schedule/"
CHANNEL_ID = "Express.Entertainment.pk"
CHANNEL_NAME = "Express Entertainment"
CHANNEL_LOGO = "https://thefilmtuition.com/tvlogo/Express-Entertainment.png"
OUTPUT_CHANNELS = os.path.join("channels", "Express-Entertainment.xml")
OUTPUT_PKCHANNELS = os.path.join("pkchannels", "Express-Entertainment.xml")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def fetch_html(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text

def get_server_today(url):
    try:
        resp = requests.head(url, timeout=15)
        date_hdr = resp.headers.get("Date")
        if date_hdr:
            dt = datetime.strptime(date_hdr, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc)
            return dt
    except Exception:
        pass
    return datetime.now(timezone.utc)

def map_days_to_dates(server_dt_utc):
    pst = timezone(timedelta(hours=5))
    base = server_dt_utc.astimezone(pst)
    today_name = base.strftime("%A")
    start_idx = DAYS.index(today_name)
    order = DAYS[start_idx:] + DAYS[:start_idx]
    day_to_date = {}
    for i, dn in enumerate(order):
        day_to_date[dn] = base.date() + timedelta(days=i)
    return day_to_date, order

def extract_sections(soup):
    sections = {}
    base = soup.find("div", class_="container") or soup
    day_classes = {
        "Monday": "monday",
        "Tuesday": "tuesday",
        "Wednesday": "wednesday",
        "Thursday": "thursday",
        "Friday": "friday",
        "Saturday": "saturday",
        "Sunday": "sunday",
    }
    for day_name, day_cls in day_classes.items():
        day_div = base.find("div", class_=lambda c: c and "schedule_check" in c and day_cls in c)
        items = []
        if day_div:
            for card in day_div.select("div.trending_single figcaption"):
                t_el = card.find("h5", class_="tw-drama-time")
                n_el = card.find("h4", class_="tw-drama-name")
                if not t_el or not n_el:
                    continue
                hhmm = t_el.get_text(strip=True)
                title = re.sub(r"\s+", " ", html.unescape(n_el.get_text(strip=True)))
                if re.fullmatch(r"([0-2]?\d:\d{2})", hhmm) and title:
                    items.append((hhmm, title))
        if items:
            # dedupe by (time,title)
            seen = set()
            unique = []
            for hhmm, title in items:
                key = (hhmm, title.lower())
                if key in seen:
                    continue
                seen.add(key)
                unique.append((hhmm, title))
            sections[day_name] = unique
    return sections

def normalize_time(hhmm, date_obj):
    try:
        h, m = hhmm.split(":")
        h = int(h); m = int(m)
        return datetime(date_obj.year, date_obj.month, date_obj.day, h, m)
    except Exception:
        return None

def title_case(text):
    t = text.strip().title()
    t = re.sub(r"\(r\)", "(R)", t, flags=re.I)
    t = re.sub(r"\(f\)", "(F)", t, flags=re.I)
    t = re.sub(r"\(ep", "(Ep", t, flags=re.I)
    return t

def description_from_title(raw):
    base = title_case(raw)
    extras = []
    markers = [
        (r"\(FRESH REPEAT\)", "Fresh Repeat"),
        (r"\(FRESH\)|\(F\)", "Fresh"),
        (r"\(1ST RPT\)|\(1st Rpt\)", "1st Repeat"),
        (r"\(SPECIAL\)|\(Special\)|\(S\)", "Special"),
        (r"\(LIVE\)|\(Live\)", "Live"),
        (r"\(EP\s*[:\-]?\s*(\d+[^)]*)\)", None),
        (r"\(RPT\)|\(REPEAT\)|\(Rpt\)|\(R\)", "Repeat"),
    ]
    for patt, repl in markers:
        m = re.search(patt, raw, re.I)
        if m:
            if repl:
                extras.append(repl)
            else:
                extras.append(f"Episode {m.group(1).strip()}")
    extras = list(dict.fromkeys(extras))
    return base if not extras else base + "\n" + "\n".join(extras)

def xml_time(dt):
    return dt.strftime("%Y%m%d%H%M%S +0500")

def build_programmes(sections, day_to_date, day_order):
    all_items = []
    day_first_start = {}
    per_day_items = {}
    for dn in day_order:
        pairs = sections.get(dn, [])
        date_obj = day_to_date.get(dn)
        day_items = []
        for hhmm, title in pairs:
            start = normalize_time(hhmm, date_obj) if date_obj else None
            if start:
                day_items.append({"start": start, "title": title})
        day_items.sort(key=lambda x: x["start"])
        if day_items:
            per_day_items[dn] = day_items
            day_first_start[dn] = day_items[0]["start"]
    for idx, dn in enumerate(day_order):
        day_items = per_day_items.get(dn, [])
        for i in range(len(day_items)):
            if i + 1 < len(day_items):
                day_items[i]["end"] = day_items[i + 1]["start"]
            else:
                # link to next day's first start when available, else +1h
                next_dn = day_order[(idx + 1) % len(day_order)]
                next_start = day_first_start.get(next_dn)
                day_items[i]["end"] = next_start if next_start and next_start > day_items[i]["start"] else day_items[i]["start"] + timedelta(hours=1)
        all_items.extend(day_items)
    return all_items

def write_xml(items):
    lines = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<tv>",
        f"  <channel id=\"{CHANNEL_ID}\">",
        f"    <display-name>{CHANNEL_NAME}</display-name>",
        f"    <icon src=\"{CHANNEL_LOGO}\" />",
        "  </channel>",
    ]
    for it in sorted(items, key=lambda x: x["start"]):
        start = xml_time(it["start"]) ; end = xml_time(it["end"]) ; title = title_case(it["title"]) ; desc = description_from_title(it["title"]) 
        lines.append(f"  <programme start=\"{start}\" stop=\"{end}\" channel=\"{CHANNEL_ID}\">")
        lines.append(f"    <title>{escape(title)}</title>")
        lines.append(f"    <desc>{escape(desc)}</desc>")
        lines.append("  </programme>")
    lines.append("</tv>")
    xml_str = "\n".join(lines)
    base = os.path.dirname(os.path.abspath(__file__))
    out_channels = os.path.join(base, OUTPUT_CHANNELS)
    out_pkchannels = os.path.join(base, OUTPUT_PKCHANNELS)
    os.makedirs(os.path.dirname(out_channels), exist_ok=True)
    os.makedirs(os.path.dirname(out_pkchannels), exist_ok=True)
    with open(out_channels, "w", encoding="utf-8") as f:
        f.write(xml_str)
    with open(out_pkchannels, "w", encoding="utf-8") as f:
        f.write(xml_str)

def main():
    server_dt = get_server_today(INPUT_URL)
    html_text = fetch_html(INPUT_URL)
    soup = BeautifulSoup(html_text, "html.parser")
    sections = extract_sections(soup)
    day_to_date, order = map_days_to_dates(server_dt)
    items = build_programmes(sections, day_to_date, order)
    write_xml(items)

if __name__ == "__main__":
    main()
