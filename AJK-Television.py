# AJK-Television.py

import re
import os
import html
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

# ================= CONFIG =================
INPUT_FILE = r"https://thefilmtuition.com/epg/pk/PTV/AJKTelevision.Schedule.All.txt"
OUTPUT_CHANNELS = os.path.join("channels", "AJK-Television.xml")
OUTPUT_PKCHANNELS = os.path.join("pkchannels", "AJK-Television.xml")
PST_OFFSET_HOURS = 5   # Pakistan Standard Time (UTC +5)
CHANNEL_ID = "AJK.Television.pk"
CHANNEL_NAME = "AJK Television"
CHANNEL_LOGO = "https://thefilmtuition.com/tvlogo/AJK-Television.png"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# ==========================================


def read_file(path):
    if path.startswith("http://") or path.startswith("https://"):
        from urllib.request import Request, urlopen
        req = Request(path, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def utcnow_pst():
    """Return current datetime in PST (UTC+5)."""
    return datetime.utcnow() + timedelta(hours=PST_OFFSET_HOURS)


def split_day_sections(txt):
    """Find <!-- Monday --> style day markers and return dict of day → HTML chunk."""
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
    """Extract all time strings from <i class="far fa-clock"></i> elements."""
    pattern = re.compile(r'<i[^>]*class=["\']far fa-clock["\'][^>]*>\s*</i>\s*([^<]*)', re.IGNORECASE)
    results = []
    for raw in pattern.findall(chunk):
        text = html.unescape(raw).strip()
        m_ampm = re.search(r'(\d{1,2}:\d{2}\s*[APMapm]{2})', text)
        if m_ampm:
            results.append(m_ampm.group(1).strip())
        else:
            m_24 = re.search(r'(\d{1,2}:\d{2})', text)
            if m_24:
                results.append(m_24.group(1).strip())
    return results


def find_titles(chunk):
    """Extract programme titles from <h4 class="post-title"> elements."""
    pattern = re.compile(r'<h4[^>]*class=["\']post-title["\'][^>]*>(.*?)</h4>', re.IGNORECASE | re.DOTALL)
    titles = []
    for t in pattern.findall(chunk):
        text = re.sub(r'<[^>]+>', '', t)
        text = html.unescape(text).strip()
        text = re.sub(r'\s+', ' ', text)
        if text:
            titles.append(text)
    return titles


def parse_time_to_datetime(time_str, base_date):
    """Convert '4:59 PM' or '17:00' → datetime on the given date."""
    s = time_str.strip().upper()
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            t = datetime.strptime(s, fmt)
            return base_date.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        except Exception:
            continue
    m = re.match(r'(\d{1,2}):(\d{2})', s)
    if m:
        h, m_ = int(m.group(1)), int(m.group(2))
        return base_date.replace(hour=h, minute=m_, second=0, microsecond=0)
    raise ValueError(f"Unrecognized time: {time_str}")


def title_case(text):
    return text.strip().title()


def build_description(raw_title):
    """Generate formatted description with normalized markers."""
    desc = title_case(raw_title)
    extras = []

    s_match = re.search(r'\bS- *([0-9A-Za-z-]+)', raw_title, re.IGNORECASE)
    if s_match:
        extras.append("Season - " + s_match.group(1))

    markers = [
        (r'\(FRESH REPEAT\)', "(Fresh Repeat)"),
        (r'\(FRESH\)|\(F\)', "(Fresh)"),
        (r'\(1ST RPT\)|\(1st Rpt\)', "(1st Repeat)"),
        (r'\(SPECIAL\)|\(Special\)|\(S\)', "(Special)"),
        (r'\(LIVE\)|\(Live\)', "(Live)"),
        (r'\(EP\s*[:\-]?\s*(\d+[^)]*)\)', None),
        (r'\(RPT\)|\(Repeat\)|\(REPEAT\)|\(Rpt\)|\(R\)', "(Repeat)")
    ]
    for patt, repl in markers:
        match = re.search(patt, raw_title, re.IGNORECASE)
        if match:
            if repl:
                extras.append(repl)
            else:
                extras.append(f"(Episode {match.group(1).strip()})")

    final = [desc] + list(dict.fromkeys(extras))  # remove duplicates
    return "\n".join(final)


def xml_time(dt):
    """Format datetime as XMLTV time with +0500 offset."""
    return dt.strftime("%Y%m%d%H%M%S +0500")


def build_epg(sections):
    now = utcnow_pst()
    today = now.strftime("%A")
    ordered_days = DAYS[DAYS.index(today):] + DAYS[:DAYS.index(today)]

    programmes = []
    current_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    prev_end = None
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
            start_dt = parse_time_to_datetime(times[i], current_date)
            day_programmes.append({"start": start_dt, "title": titles[i]})

        # connect last programme of previous day to first of current day
        if prev_end and day_programmes:
            prev_end["end"] = day_programmes[0]["start"]

        # assign end times for current day except last (last will connect to next day)
        for i in range(len(day_programmes) - 1):
            day_programmes[i]["end"] = day_programmes[i + 1]["start"]

        # store last for linking later
        if day_programmes:
            prev_end = day_programmes[-1]

        programmes.extend(day_programmes)
        current_date += timedelta(days=1)

    # finally, link the very last programme of the week to the first programme of the week (loop)
    if programmes:
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
        lines.append(
            f'  <programme start="{xml_time(start)}" stop="{xml_time(end)}" channel="{CHANNEL_ID}">'
        )
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
    print(f"[INFO] EPG created successfully: {OUTPUT_CHANNELS} and {OUTPUT_PKCHANNELS}")


if __name__ == "__main__":
    main()
