import os
import re
import html
from urllib.request import Request, urlopen
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

INPUT_REMOTE = "https://thefilmtuition.com/epg/pk/PTV/PTVNews.Schedule.All.txt"
CHANNEL_ID = "PTV.News.pk"
CHANNEL_NAME = "PTV News"
CHANNEL_LOGO = "https://thefilmtuition.com/tvlogo/PTV-News.png"
OUTPUT_CHANNELS = os.path.join("channels", "PTV-News.xml")
OUTPUT_PKCHANNELS = os.path.join("pkchannels", "PTV-News.xml")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def read_text():
    req = Request(INPUT_REMOTE, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def split_day_sections(txt):
    pattern = re.compile(r"<!--\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s*-->", re.I)
    matches = list(pattern.finditer(txt))
    sections = {}
    for i, m in enumerate(matches):
        day = m.group(1).title()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(txt)
        sections[day] = txt[start:end]
    return sections

def find_times(chunk):
    base_pattern = re.compile(r'<i[^>]*class=["\']far fa-clock["\'][^>]*>\s*</i>\s*([^<\r\n]+)', re.I)
    raws = [html.unescape(r).strip() for r in base_pattern.findall(chunk)]
    cleaned = []
    for r in raws:
        s = re.sub(r"\s+", " ", r).upper()
        m = re.search(r'([0-2]?\d(?:[:.]\d{2}|\d{2})?)\s*(AM|PM|NOON|MN)?', s)
        if m:
            token = m.group(1).replace('.', ':')
            marker = m.group(2) or ""
            cleaned.append((token + (" " + marker if marker else "")).strip())
        else:
            cleaned.append(s)
    return cleaned

def find_titles(chunk):
    pattern = re.compile(r'<h4[^>]*class=["\']post-title["\'][^>]*>(.*?)</h4>', re.I | re.S)
    titles = []
    for t in pattern.findall(chunk):
        text = re.sub(r'<[^>]+>', '', t)
        text = html.unescape(text).strip()
        text = re.sub(r'\s+', ' ', text)
        if text:
            titles.append(text)
    return titles

def normalize_time(tok, base_date):
    s = tok.strip().upper().replace('.', ':')
    if s.endswith("NOON"): s = re.sub(r"NOON$", "PM", s)
    if s.endswith("MN"): s = re.sub(r"MN$", "AM", s)
    m = re.match(r'^(\d{3,4})(?:\s*(AM|PM))?$', s)
    if m:
        digits, marker = m.group(1), (m.group(2) or '')
        hh = int(digits[:-2]); mm = digits[-2:]
        s = f"{hh}:{mm}" + (f" {marker}" if marker else "")
    m2 = re.match(r'^(\d{1,2})\s*(AM|PM)?$', s)
    if m2:
        hh = int(m2.group(1)); marker = m2.group(2) or ''
        s = f"{hh}:00" + (f" {marker}" if marker else "")
    for fmt in ("%I:%M %p", "%H:%M", "%I:%M%p"):
        try:
            dt = datetime.strptime(s, fmt)
            return base_date.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)
        except Exception:
            pass
    m3 = re.match(r'(\d{1,2}):(\d{2})', s)
    if m3:
        return base_date.replace(hour=int(m3.group(1)), minute=int(m3.group(2)), second=0, microsecond=0)
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
        (r'\(FRESH REPEAT\)', "Fresh Repeat"),
        (r'\(FRESH\)|\(F\)', "Fresh"),
        (r'\(1ST RPT\)|\(1st Rpt\)', "1st Repeat"),
        (r'\(SPECIAL\)|\(Special\)|\(S\)', "Special"),
        (r'\(LIVE\)|\(Live\)', "Live"),
        (r'\(EP\s*[:\-]?\s*(\d+[^)]*)\)', None),
        (r'\(RPT\)|\(REPEAT\)|\(Rpt\)|\(R\)', "Repeat")
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

def build_epg(sections):
    now = datetime.utcnow() + timedelta(hours=5)
    today = now.strftime("%A")
    order = DAYS[DAYS.index(today):] + DAYS[:DAYS.index(today)]
    programmes = []
    current_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    prev_last = None
    for day in order:
        block = sections.get(day)
        if not block:
            current_date += timedelta(days=1)
            continue
        times = find_times(block)
        titles = find_titles(block)
        pairs = min(len(times), len(titles))
        day_items = []
        for i in range(pairs):
            start_dt = normalize_time(times[i], current_date)
            if not start_dt:
                continue
            day_items.append({"start": start_dt, "title": titles[i]})
        if prev_last and day_items:
            prev_last["end"] = day_items[0]["start"]
        for i in range(len(day_items) - 1):
            day_items[i]["end"] = day_items[i + 1]["start"]
        if day_items:
            prev_last = day_items[-1]
        programmes.extend(day_items)
        current_date += timedelta(days=1)
    if programmes and "end" not in programmes[-1]:
        programmes[-1]["end"] = programmes[0]["start"] + timedelta(days=7)
    return programmes

def write_xml(programmes):
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<tv>',
        f'  <channel id="{CHANNEL_ID}">',
        f'    <display-name>{CHANNEL_NAME}</display-name>',
        f'    <icon src="{CHANNEL_LOGO}" />',
        '  </channel>',
    ]
    for p in programmes:
        start, end = p["start"], p["end"]
        title = title_case(p["title"]) 
        desc = description_from_title(p["title"]) 
        xml_lines.append(f'  <programme start="{xml_time(start)}" stop="{xml_time(end)}" channel="{CHANNEL_ID}">')
        xml_lines.append(f'    <title>{escape(title)}</title>')
        xml_lines.append(f'    <desc>{escape(desc)}</desc>')
        xml_lines.append('  </programme>')
    xml_lines.append('</tv>')
    xml_str = "\n".join(xml_lines)
    out_channels = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_CHANNELS)
    out_pkchannels = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_PKCHANNELS)
    os.makedirs(os.path.dirname(out_channels), exist_ok=True)
    os.makedirs(os.path.dirname(out_pkchannels), exist_ok=True)
    with open(out_channels, 'w', encoding='utf-8') as f:
        f.write(xml_str)
    with open(out_pkchannels, 'w', encoding='utf-8') as f:
        f.write(xml_str)

def main():
    txt = read_text()
    sections = split_day_sections(txt)
    programmes = build_epg(sections)
    write_xml(programmes)
    print(f"[INFO] PTV News EPG written to {OUTPUT_CHANNELS} and {OUTPUT_PKCHANNELS}")

if __name__ == '__main__':
    main()
