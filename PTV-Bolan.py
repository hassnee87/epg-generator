# PTV-Bolan.py 

import re
import html
import os
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

# ================ CONFIG =================
INPUT_FILE = r"https://thefilmtuition.com/epg/pk/PTV/PTVBolan.Schedule.All.txt"
OUTPUT_CHANNELS = os.path.join("channels", "PTV-Bolan.xml")
OUTPUT_PKCHANNELS = os.path.join("pkchannels", "PTV-Bolan.xml")
PST_OFFSET_HOURS = 5   # Pakistan Standard Time (UTC +5)
CHANNEL_ID = "PTV.Bolan.pk"
CHANNEL_NAME = "PTV Bolan"
CHANNEL_LOGO = "https://thefilmtuition.com/tvlogo/PTV-Bolan.png"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# =========================================

def read_file(path):
    if path.startswith("http://") or path.startswith("https://"):
        from urllib.request import Request, urlopen
        req = Request(path, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def utcnow_pst():
    return datetime.utcnow() + timedelta(hours=PST_OFFSET_HOURS)

def split_day_sections(txt):
    pattern = re.compile(r"<!--\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s*-->", re.IGNORECASE)
    matches = list(pattern.finditer(txt))
    sections = {}
    for i, m in enumerate(matches):
        day = m.group(1).title()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(txt)
        sections[day] = txt[start:end]
    return sections

def find_times(chunk):
    """
    Robustly extract time text occurring after the clock icon.
    Captures formats like: '08.00 AM', '0800 AM', '11.40 PM', '1100AM', '1200NOON', '1200MN', '12.00 AM', '12:00 PM', '5:00 PM'
    """
    # grab the raw content after the <i ...fa-clock></i>
    base_pattern = re.compile(r'<i[^>]*class=["\']far fa-clock["\'][^>]*>\s*</i>\s*([^<\r\n]+)', re.IGNORECASE)
    raws = [html.unescape(r).strip() for r in base_pattern.findall(chunk)]

    cleaned = []
    for r in raws:
        s = r.strip()
        # collapse spaces and normalize to uppercase words for markers
        s = re.sub(r'\s+', ' ', s).upper()
        # typical cases: '08.00 AM', '0800 AM', '1100AM', '11.40 PM', '1200NOON', '1200MN', '12.00 AM'
        # try to extract a contiguous time token + optional marker (AM/PM/NOON/MN)
        m = re.search(r'([0-2]?\d(?:[:.]\d{2}|\d{2})?)\s*(AM|PM|NOON|MN)?', s)
        if m:
            token = m.group(1)
            marker = m.group(2) or ""
            token = token.replace('.', ':')
            cleaned.append((token + (" " + marker if marker else "")).strip())
        else:
            # fallback: any numbers+AM/PM
            m2 = re.search(r'([0-2]?\d{1,4})\s*(AM|PM|NOON|MN)?', s)
            if m2:
                token = m2.group(1)
                marker = m2.group(2) or ""
                # insert colon if token looks like HHMM
                if len(token) in (3,4):
                    hh = token[:-2]; mm = token[-2:]
                    token = f"{int(hh)}:{mm}"
                cleaned.append((token + (" " + marker if marker else "")).strip())
            else:
                # give raw as last resort
                cleaned.append(s)
    return cleaned

def find_titles(chunk):
    pattern = re.compile(r'<h4[^>]*class=["\']post-title["\'][^>]*>(.*?)</h4>', re.IGNORECASE | re.DOTALL)
    titles = []
    for t in pattern.findall(chunk):
        text = re.sub(r'<[^>]+>', '', t)
        text = html.unescape(text).strip()
        text = re.sub(r'\s+', ' ', text)
        if text:
            titles.append(text)
    return titles

def normalize_time_token_to_datetime(tok, base_date):
    """
    tok examples: '08:00 AM', '08:00', '0800 AM', '1100AM', '1200NOON', '1200MN', '11:40 PM'
    Return datetime on base_date (naive, PST assumed elsewhere).
    """
    s = tok.strip().upper()
    # handle NOON / MN markers
    if s.endswith("NOON"):
        s = re.sub(r'NOON$', 'PM', s)
    if s.endswith("MN"):
        # treat MN as midnight (AM)
        s = re.sub(r'MN$', 'AM', s)

    # replace dots with colon
    s = s.replace('.', ':')

    # if something like '0800 AM' or '1100AM' -> insert colon
    m = re.match(r'^(\d{3,4})(?:\s*(AM|PM))?$', s)
    if m:
        digits = m.group(1)
        marker = m.group(2) or ''
        hh = int(digits[:-2]); mm = digits[-2:]
        s = f"{hh}:{mm}" + (f" {marker}" if marker else "")

    # if single H or HH with no minutes, append :00 (e.g., '8 AM' or '08 AM')
    m2 = re.match(r'^(\d{1,2})\s*(AM|PM)?$', s)
    if m2:
        hh = int(m2.group(1))
        marker = m2.group(2) or ''
        s = f"{hh}:00" + (f" {marker}" if marker else "")

    # now try parsing with known formats
    for fmt in ("%I:%M %p", "%H:%M", "%I:%M%p"):
        try:
            dt = datetime.strptime(s, fmt)
            return base_date.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)
        except Exception:
            continue

    # last attempt: extract numbers
    m3 = re.match(r'(\d{1,2}):(\d{2})', s)
    if m3:
        hh = int(m3.group(1)); mm = int(m3.group(2))
        return base_date.replace(hour=hh, minute=mm, second=0, microsecond=0)

    raise ValueError(f"Unrecognized time token: '{tok}'")

def title_case(text):
    t = text.strip().title()
    # enforce markers case in title
    t = re.sub(r"\(r\)", "(R)", t, flags=re.IGNORECASE)
    t = re.sub(r"\(f\)", "(F)", t, flags=re.IGNORECASE)
    t = re.sub(r"\(ep", "(Ep", t, flags=re.IGNORECASE)
    return t

def build_description(raw_title):
    # description from title with full-word abbreviations, no title repetition
    base = title_case(raw_title)
    extras = []
    # Season S-123 etc
    s_match = re.search(r'\bS- *([0-9A-Za-z-]+)', raw_title, re.IGNORECASE)
    if s_match:
        extras.append("Season - " + s_match.group(1))
    # other markers
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
        match = re.search(patt, raw_title, re.IGNORECASE)
        if match:
            if repl:
                extras.append(repl)
            else:
                extras.append(f"Episode {match.group(1).strip()}")

    extras = list(dict.fromkeys(extras))
    if extras:
        return base + "\n" + "\n".join(extras)
    return base

def xml_time(dt):
    return dt.strftime("%Y%m%d%H%M%S +0500")

def build_epg(sections):
    now = utcnow_pst()
    today = now.strftime("%A")
    ordered_days = DAYS[DAYS.index(today):] + DAYS[:DAYS.index(today)]

    programmes = []
    current_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    prev_last = None
    for day in ordered_days:
        chunk = sections.get(day)
        if not chunk:
            current_date += timedelta(days=1)
            continue

        times = find_times(chunk)
        titles = find_titles(chunk)
        pairs = min(len(times), len(titles))
        day_programmes = []

        for i in range(pairs):
            try:
                start_dt = normalize_time_token_to_datetime(times[i], current_date)
            except Exception:
                # if normalization fails, skip this pair
                continue
            day_programmes.append({"start": start_dt, "title": titles[i]})

        # link previous day's last to today's first
        if prev_last and day_programmes:
            prev_last["end"] = day_programmes[0]["start"]

        # set ends for all except last of day
        for i in range(len(day_programmes)-1):
            day_programmes[i]["end"] = day_programmes[i+1]["start"]

        if day_programmes:
            prev_last = day_programmes[-1]

        programmes.extend(day_programmes)
        current_date += timedelta(days=1)

    # loop: last programme end → first programme start + 7 days (keeps continuity)
    if programmes and "end" not in programmes[-1]:
        programmes[-1]["end"] = programmes[0]["start"] + timedelta(days=7)

    return programmes

def write_epg(programmes):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<tv>",
        f'  <channel id="{CHANNEL_ID}">',
        f'    <display-name>{CHANNEL_NAME}</display-name>',
        f'    <icon src="{CHANNEL_LOGO}" />',
        "  </channel>",
    ]

    for p in programmes:
        start, end = p["start"], p["end"]
        title, desc = title_case(p["title"]), build_description(p["title"])
        lines.append(f'  <programme start="{xml_time(start)}" stop="{xml_time(end)}" channel="{CHANNEL_ID}">')
        lines.append(f'    <title>{escape(title)}</title>')
        lines.append(f'    <desc>{escape(desc)}</desc>')
        lines.append("  </programme>")

    lines.append("</tv>")

    out_channels = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_CHANNELS)
    out_pkchannels = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_PKCHANNELS)
    os.makedirs(os.path.dirname(out_channels), exist_ok=True)
    os.makedirs(os.path.dirname(out_pkchannels), exist_ok=True)
    xml_str = "\n".join(lines)
    with open(out_channels, "w", encoding="utf-8") as f:
        f.write(xml_str)
    with open(out_pkchannels, "w", encoding="utf-8") as f:
        f.write(xml_str)

def main():
    txt = read_file(INPUT_FILE)
    sections = split_day_sections(txt)
    programmes = build_epg(sections)
    write_epg(programmes)
    print(f"[INFO] EPG created: {OUTPUT_CHANNELS} and {OUTPUT_PKCHANNELS}")

if __name__ == "__main__":
    main()
