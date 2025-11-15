# PTV-Global.py
# Reads UK times (marked “UK”) and builds EPG using +0100 offset.

import re
import os
import html
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

# ================ CONFIG =================
INPUT_FILE = r"https://thefilmtuition.com/epg/pk/PTV/PTVGlobal.Schedule.All.txt"
OUTPUT_CHANNELS = os.path.join("channels", "PTV-Global.xml")
OUTPUT_PKCHANNELS = os.path.join("pkchannels", "PTV-Global.xml")
UK_OFFSET_HOURS = 1   # UK as UTC+1
CHANNEL_ID = "PTV.Global.pk"
CHANNEL_NAME = "PTV Global"
CHANNEL_LOGO = "https://thefilmtuition.com/tvlogo/PTV-Global.png"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# =========================================

def read_input(path):
    if path.startswith("http://") or path.startswith("https://"):
        from urllib.request import Request, urlopen
        req = Request(path, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def find_day_sections(html_text):
    sections = []
    for day in DAYS:
        marker = f"<!-- {day} -->"
        idx = html_text.find(marker)
        if idx != -1:
            sections.append((day, idx))
    sections_sorted = sorted(sections, key=lambda x: x[1])
    result = {}
    for i, (day, start) in enumerate(sections_sorted):
        end = sections_sorted[i + 1][1] if i + 1 < len(sections_sorted) else len(html_text)
        result[day] = html_text[start:end]
    return result

def extract_pairs(day_html):
    # Extract UK time entries and titles
    time_spans = re.findall(r'<span[^>]*>.*?<i[^>]*></i>(.*?)</span>', day_html, flags=re.S | re.I)
    titles = re.findall(r'<h4[^>]*class="post-title"[^>]*>\s*(.*?)\s*</h4>', day_html, flags=re.S | re.I)
    clean_titles = [re.sub(r'<[^>]+>', '', t).strip() for t in titles]
    uk_times = []
    for ts in time_spans:
        txt = " ".join(ts.split())
        m = re.search(r'(\d{1,4}[:\.]?\d{0,2})\s*UK', txt, flags=re.I)
        if m:
            uk_times.append(m.group(1))
        else:
            uk_times.append(None)
    pairs = []
    for i in range(min(len(uk_times), len(clean_titles))):
        if uk_times[i]:
            pairs.append((uk_times[i], clean_titles[i]))
    return pairs

def parse_uk_time_str(time_str):
    """Parses 12/24 hour UK times like 400, 0400, 4:30, 21:00 safely."""
    s = time_str.strip().replace('.', ':')
    s = re.sub(r'[^\d:]', '', s)
    if not s:
        return None, None
    if ':' in s:
        h, m = s.split(':')
    elif len(s) <= 2:
        h, m = s, "0"
    elif len(s) == 3:
        h, m = s[0], s[1:]
    else:
        h, m = s[:2], s[2:]
    try:
        h = int(h)
        m = int(m)
        if not (0 <= h < 24 and 0 <= m < 60):
            return None, None
        return h, m
    except ValueError:
        return None, None

def build_epg(sections):
    now_utc = datetime.now(timezone.utc)
    now_uk = now_utc + timedelta(hours=UK_OFFSET_HOURS)
    today_weekday = now_uk.strftime("%A")
    idx_today = DAYS.index(today_weekday)
    day_order = DAYS[idx_today:] + DAYS[:idx_today]

    base_date = now_uk.date()
    day_name_to_date = {dn: base_date + timedelta(days=i) for i, dn in enumerate(day_order)}

    programmes = []
    for dn in day_order:
        block = sections.get(dn)
        if not block:
            continue
        pairs = extract_pairs(block)
        if not pairs:
            continue

        day_date = day_name_to_date[dn]
        day_programmes = []
        for tstr, title in pairs:
            h, m = parse_uk_time_str(tstr)
            if h is None:
                continue
            start_dt = datetime(day_date.year, day_date.month, day_date.day, h, m)
            day_programmes.append({"start": start_dt, "title": title})

        day_programmes.sort(key=lambda x: x["start"])
        for i, cur in enumerate(day_programmes):
            if i + 1 < len(day_programmes):
                cur["end"] = day_programmes[i + 1]["start"]
            else:
                next_day_index = day_order.index(dn) + 1
                next_end = None
                while next_day_index < len(day_order):
                    nd = day_order[next_day_index]
                    nd_block = sections.get(nd)
                    if nd_block:
                        nd_pairs = extract_pairs(nd_block)
                        if nd_pairs:
                            nh, nm = parse_uk_time_str(nd_pairs[0][0])
                            if nh is not None:
                                nd_date = day_name_to_date[nd]
                                next_end = datetime(nd_date.year, nd_date.month, nd_date.day, nh, nm)
                                break
                    next_day_index += 1
                cur["end"] = next_end if next_end else cur["start"] + timedelta(hours=24)
        programmes.extend(day_programmes)
    return programmes

def fmt_epg_dt(dt):
    return dt.strftime("%Y%m%d%H%M") + " +0100"

def title_to_description(title):
    disp = " ".join([w.capitalize() for w in title.split()])
    desc_lines = [disp]
    specials = [
        (r'\bS-?\s*(\d+)\b', r'Season - \1'),
        (r'\b\(FRESH\)|\(FRESH\)|\b\(F\)|\(Fresh\)|\(f\)', "(Fresh)"),
        (r'\b\(EP\b|\b\(Ep\b|\b\(EP-?', "(Episode"),
        (r'\b\(RPT\)|\(REPEAT\)|\(Repeat\)|\(Rpt\)|\(R\)', "(Repeat)"),
        (r'\b\(1ST RPT\)|\(1st Rpt\)', "(1st Repeat)"),
        (r'\b\(SPECIAL\)|\(Special\)|\(S\)', "(Special)"),
        (r'\b\(LIVE\)|\(Live\)', "(Live)"),
        (r'\b\(FRESH REPEAT\)|\(Fresh Repeat\)', "(Fresh Repeat)"),
    ]
    for pat, repl in specials:
        if re.search(pat, title, flags=re.I):
            desc_lines.append(re.sub(pat, repl, title, flags=re.I))
    return disp, "\n".join(desc_lines)

def generate_xml(programmes):
    xml_lines = []
    xml_lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    xml_lines.append('<tv>')
    xml_lines.append(f'  <channel id="{CHANNEL_ID}">')
    xml_lines.append(f'    <display-name>{CHANNEL_NAME}</display-name>')
    xml_lines.append(f'    <icon src="{CHANNEL_LOGO}" />')
    xml_lines.append('  </channel>')
    for p in sorted(programmes, key=lambda x: x["start"]):
        start = fmt_epg_dt(p["start"])
        end = fmt_epg_dt(p["end"])
        title, desc = title_to_description(p["title"]) 
        xml_lines.append(f'  <programme start="{start}" stop="{end}" channel="{CHANNEL_ID}">')
        xml_lines.append(f'    <title>{escape(title)}</title>')
        xml_lines.append(f'    <desc>{escape(desc)}</desc>')
        xml_lines.append('  </programme>')
    xml_lines.append('</tv>')
    xml_str = "\n".join(xml_lines)
    out_channels = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_CHANNELS)
    out_pkchannels = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_PKCHANNELS)
    os.makedirs(os.path.dirname(out_channels), exist_ok=True)
    os.makedirs(os.path.dirname(out_pkchannels), exist_ok=True)
    with open(out_channels, "w", encoding="utf-8") as f:
        f.write(xml_str)
    with open(out_pkchannels, "w", encoding="utf-8") as f:
        f.write(xml_str)

def main():
    html_text = read_input(INPUT_FILE)
    sections = find_day_sections(html_text)
    programmes = build_epg(sections)
    if not programmes:
        print("[ERROR] No programmes parsed!")
        return
    generate_xml(programmes)
    print(f"[INFO] EPG generated successfully with {len(programmes)} programmes → {OUTPUT_CHANNELS} and {OUTPUT_PKCHANNELS}")

if __name__ == "__main__":
    main()
