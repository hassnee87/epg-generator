import os
import re
import sys
import gzip
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen
from datetime import datetime, timedelta, timezone

INPUT_URL = "https://streamingtvguides.com/Channel/ARYZauq"
CHANNEL_NAME = "ARY Zauq"
CHANNEL_ID = "ARY.News.pk"
CHANNEL_LOGO = "https://thefilmtuition.com/tvlogo/ARY-Zauq.png"
OUTPUT_PATH_CHANNELS = os.path.join("channels", "Ary-Zauq.xml")
OUTPUT_PATH_PKCHANNELS = os.path.join("pkchannels", "Ary-Zauq.xml")
TARGET_TZ_OFFSET = "+05:00"

def debug(msg):
    print(f"[DEBUG] {msg}")

def get_server_datetime(url):
    debug(f"Fetching server date from HEAD: {url}")
    try:
        req = Request(url, method="HEAD")
        with urlopen(req, timeout=30) as resp:
            date_hdr = resp.headers.get("Date")
            if date_hdr:
                dt = datetime.strptime(date_hdr, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc)
                debug(f"Server date header found: {dt.isoformat()}")
                return dt
    except Exception as e:
        debug(f"HEAD request failed: {e}")
    now_utc = datetime.now(timezone.utc)
    debug(f"Using UTC now as server time: {now_utc.isoformat()}")
    return now_utc

def fetch_html(url):
    debug(f"Downloading HTML: {url}")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (ARY Zauq EPG)"})
    with urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def strip_tags(text):
    return re.sub(r"<[^>]+>", "", text)

def parse_range(line):
    m = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+[A-Z]{3}\s+-\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+[A-Z]{3}$", line)
    if not m:
        return None, None
    s_date, s_time, e_date, e_time = m.groups()
    tz = timezone(timedelta(hours=5))
    s_dt = datetime.strptime(f"{s_date} {s_time}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
    e_dt = datetime.strptime(f"{e_date} {e_time}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
    return s_dt, e_dt

def format_xmltv_datetime(dt, offset_str):
    compact = offset_str.replace(":", "") if ":" in offset_str else offset_str
    sign = 1 if compact.startswith("+") else -1
    off_h = int(compact[1:3])
    off_m = int(compact[3:5])
    target_tz = timezone(sign * timedelta(hours=off_h, minutes=off_m))
    dt_target = dt.astimezone(target_tz)
    return f"{dt_target.strftime('%Y%m%d%H%M%S')} {compact}"

def parse_entries(html):
    entries = []
    cards = re.split(r"<div\s+class=\"card\"\s*>", html)
    for card in cards:
        m_title = re.search(r"<h5\s+class=\"card-title\">([\s\S]*?)</h5>", card)
        if not m_title:
            continue
        raw_title = m_title.group(1)
        title = strip_tags(raw_title).replace("Playing Now!", "").strip()
        m_time = re.search(r"\n\s*([0-9\-:\sA-Z]+)\s*<br\s*/?>", card)
        start_dt, end_dt = None, None
        if m_time:
            line = m_time.group(1).strip()
            start_dt, end_dt = parse_range(line)
        m_desc = re.search(r"<p\s+class=\"card-text\">([\s\S]*?)</p>", card)
        desc = strip_tags(m_desc.group(1)).strip() if m_desc else None
        if not desc:
            desc = title
        entries.append({
            "title": title,
            "start_dt": start_dt,
            "end_dt": end_dt,
            "desc": desc,
        })
    return entries

def indent_xml(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent_xml(e, level + 1)
        if not e.tail or not e.tail.strip():
            e.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def ensure_dirs():
    for p in [OUTPUT_PATH_CHANNELS, OUTPUT_PATH_PKCHANNELS]:
        d = os.path.dirname(p)
        if d and not os.path.exists(d):
            debug(f"Creating directory: {d}")
            os.makedirs(d, exist_ok=True)

def fill_gaps_and_missing(entries):
    entries = [e for e in entries if e["start_dt"] is not None]
    entries.sort(key=lambda x: x["start_dt"])
    fixed = []
    for i, e in enumerate(entries):
        start = e["start_dt"]
        end = e["end_dt"]
        if end is None:
            if i + 1 < len(entries):
                end = entries[i + 1]["start_dt"]
            else:
                end = start + timedelta(minutes=30)
        fixed.append({**e, "end_dt": end})
    with_gaps = []
    for i, e in enumerate(fixed):
        with_gaps.append(e)
        if i + 1 < len(fixed):
            if e["end_dt"] < fixed[i + 1]["start_dt"]:
                with_gaps.append({
                    "title": "ARY News Special Programme",
                    "start_dt": e["end_dt"],
                    "end_dt": fixed[i + 1]["start_dt"],
                    "desc": "ARY News Special Programme",
                })
    return with_gaps

def filter_three_days(entries, server_dt_utc):
    off_h = int(TARGET_TZ_OFFSET[1:3])
    off_m = int(TARGET_TZ_OFFSET[4:6]) if ":" in TARGET_TZ_OFFSET else int(TARGET_TZ_OFFSET[3:5])
    sign = 1 if TARGET_TZ_OFFSET.startswith("+") else -1
    target_tz = timezone(sign * timedelta(hours=off_h, minutes=off_m))
    today_target = server_dt_utc.astimezone(target_tz).date()
    valid_dates = {today_target,
                   (server_dt_utc.astimezone(target_tz) + timedelta(days=1)).date(),
                   (server_dt_utc.astimezone(target_tz) + timedelta(days=2)).date()}
    selected = []
    seen = set()
    for e in entries:
        d = e["start_dt"].astimezone(target_tz).date()
        if d in valid_dates:
            key = (e["start_dt"], e["end_dt"], e["title"]) 
            if key not in seen:
                seen.add(key)
                selected.append(e)
    return selected

def write_xml(out_path, entries):
    debug(f"Writing XML to: {out_path}")
    tv = ET.Element("tv")
    ch = ET.SubElement(tv, "channel", {"id": CHANNEL_ID})
    dn = ET.SubElement(ch, "display-name")
    dn.text = CHANNEL_NAME
    ET.SubElement(ch, "icon", {"src": CHANNEL_LOGO})
    for e in entries:
        p = ET.SubElement(tv, "programme", {"channel": CHANNEL_ID})
        p.set("start", format_xmltv_datetime(e["start_dt"], TARGET_TZ_OFFSET))
        p.set("stop", format_xmltv_datetime(e["end_dt"], TARGET_TZ_OFFSET))
        t = ET.SubElement(p, "title")
        t.text = e["title"]
        d = ET.SubElement(p, "desc")
        d.text = e["desc"]
    indent_xml(tv)
    ET.ElementTree(tv).write(out_path, encoding="utf-8", xml_declaration=True)

def write_gzip(xml_path, gz_path):
    debug(f"Writing GZIP to: {gz_path}")
    with open(xml_path, "rb") as f_in:
        with gzip.open(gz_path, "wb") as f_out:
            f_out.write(f_in.read())

def main():
    debug("Starting ARY Zauq EPG scraper")
    server_dt_utc = get_server_datetime(INPUT_URL)
    html = fetch_html(INPUT_URL)
    entries = parse_entries(html)
    debug(f"Parsed {len(entries)} raw entries")
    entries = fill_gaps_and_missing(entries)
    entries = filter_three_days(entries, server_dt_utc)
    ensure_dirs()
    write_xml(OUTPUT_PATH_CHANNELS, entries)
    write_xml(OUTPUT_PATH_PKCHANNELS, entries)
   # write_gzip(OUTPUT_PATH_CHANNELS, OUTPUT_PATH_CHANNELS + ".gz")
   # write_gzip(OUTPUT_PATH_PKCHANNELS, OUTPUT_PATH_PKCHANNELS + ".gz")
    debug("ARY Zauq EPG generation completed")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

