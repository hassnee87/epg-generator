import os
import re
import sys
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

INPUT_URL = "https://www.geo.tv/schedule"
CHANNEL_NAME = "Geo News"
CHANNEL_ID = "Geo.News.pk"
CHANNEL_LOGO = "https://thefilmtuition.com/tvlogo/Geo-News.png"
OUTPUT_PATH_CHANNELS = os.path.join("channels", "Geo-News.xml")
OUTPUT_PATH_PKCHANNELS = os.path.join("pkchannels", "Geo-News.xml")
TARGET_TZ_OFFSET = "+05:00"
COUNTRIES_XML_CANDIDATES = [os.path.join("countries", "uk.epg.xml"), os.path.join("countries", "UK.epg.xml")]
UK_CHANNEL_ID = "GEO.News.uk"

# Generic fallback configuration
SET_DURATION_FOR_GENERIC_MIN = 30
PROGRAMME_TITLES_GENERIC = "Geo News"
PROGRAM_DESC_GENERIC = (
    "Geo News is a Pakistani news channel that provides around-the-clock news, current affairs, "
    "and sports coverage in Urdu, with a focus on breaking news and live reports."
)

def debug(msg):
    print(f"[DEBUG] {msg}")

def fetch_html(url):
    debug(f"Downloading HTML: {url}")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Geo News EPG)"})
    with urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def parse_schedule_date(html):
    m = re.search(r"<div\s+class=\"month\"[^>]*data-month=\"([^\"]+)\"", html)
    if not m:
        m = re.search(r"<div\s+class=\"month\"[^>]*>\s*<span\s+class=\"heading\">([^<]+)</span>", html)
    if not m:
        raise ValueError("Schedule date not found")
    s = m.group(1).strip()
    return datetime.strptime(s, "%B %d, %Y")

def parse_entries(html, base_date):
    entries = []
    for art in re.findall(r"<article>([\s\S]*?)</article>", html):
        mt = re.search(r"<span\s+class=\"timeslot\">([^<]+)</span>", art)
        ms = re.search(r"<span\s+class=\"program_status\">([^<]+)</span>", art)
        tt = re.search(r"<span\s+class=\"schudule_status\">([^<]+)</span>", art)
        if not mt or not tt:
            continue
        hhmm = mt.group(1).strip()
        title = tt.group(1).strip()
        status = ms.group(1).strip() if ms else ""
        hour, minute = hhmm.split(":")
        start_dt = datetime(base_date.year, base_date.month, base_date.day, int(hour), int(minute), 0,
                            tzinfo=timezone(timedelta(hours=5)))
        desc = f"{title} — {status}".strip(" —")
        entries.append({"title": title, "status": status, "start_dt": start_dt, "desc": desc})
    entries.sort(key=lambda x: x["start_dt"])
    fixed = []
    for i, e in enumerate(entries):
        end_dt = None
        if i + 1 < len(entries):
            end_dt = entries[i + 1]["start_dt"]
        else:
            end_dt = e["start_dt"] + timedelta(minutes=30)
        fixed.append({**e, "end_dt": end_dt})
    return fixed

def load_uk_epg():
    for path in COUNTRIES_XML_CANDIDATES:
        if os.path.exists(path):
            debug(f"Reading UK EPG: {path}")
            tree = ET.parse(path)
            return tree.getroot()
    debug("UK EPG not found; skipping description enrichment")
    return None

def normalize(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def token_set_ratio(a, b):
    ta = set(normalize(a).split())
    tb = set(normalize(b).split())
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union

def best_description(title, uk_root):
    if uk_root is None:
        return None
    best = (0.0, None)
    for p in uk_root.findall("programme"):
        if p.attrib.get("channel") != UK_CHANNEL_ID:
            continue
        t = p.find("title")
        d = p.find("desc")
        st = t.text.strip() if (t is not None and t.text) else ""
        sd = d.text.strip() if (d is not None and d.text) else None
        if not st:
            continue
        r1 = SequenceMatcher(None, normalize(title), normalize(st)).ratio()
        r2 = token_set_ratio(title, st)
        score = max(r1, r2)
        if score > best[0]:
            best = (score, sd)
    return best[1] if best[0] >= 0.45 else None

def ensure_dirs():
    for p in [OUTPUT_PATH_CHANNELS, OUTPUT_PATH_PKCHANNELS]:
        d = os.path.dirname(p)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

def format_xmltv_datetime(dt, offset_str):
    compact = offset_str.replace(":", "") if ":" in offset_str else offset_str
    return f"{dt.strftime('%Y%m%d%H%M%S')} {compact}"

def write_xml(out_path, entries):
    debug(f"Writing XML: {out_path}")
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
        st = ET.SubElement(p, "sub-title")
        st.text = e["status"]
        d = ET.SubElement(p, "desc")
        d.text = e["desc"]
    indent_xml(tv)
    ET.ElementTree(tv).write(out_path, encoding="utf-8", xml_declaration=True)

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

def main():
    try:
        html = fetch_html(INPUT_URL)
        base_date = parse_schedule_date(html)
        entries = parse_entries(html, base_date)
    except Exception as ex:
        debug(f"Schedule fetch/parse failed: {ex}")
        entries = []

    if entries:
        uk_root = load_uk_epg()
        for e in entries:
            bd = best_description(e["title"], uk_root)
            if bd:
                e["desc"] = bd
    else:
        debug("No schedule available; generating generic 1-day EPG")
        # Build one day of generic programmes using configured duration
        pst = timezone(timedelta(hours=5))
        base_date = datetime.now(timezone.utc).astimezone(pst).date()
        slots = int((24 * 60) / max(1, SET_DURATION_FOR_GENERIC_MIN))
        entries = []
        start_dt = datetime(base_date.year, base_date.month, base_date.day, 0, 0, tzinfo=pst)
        for i in range(slots):
            s = start_dt + timedelta(minutes=i * SET_DURATION_FOR_GENERIC_MIN)
            e = s + timedelta(minutes=SET_DURATION_FOR_GENERIC_MIN)
            entries.append({
                "start_dt": s,
                "end_dt": e,
                "title": PROGRAMME_TITLES_GENERIC,
                "status": "Generic",
                "desc": PROGRAM_DESC_GENERIC,
            })
    ensure_dirs()
    write_xml(OUTPUT_PATH_CHANNELS, entries)
    write_xml(OUTPUT_PATH_PKCHANNELS, entries)
    debug("Geo News EPG generation completed")

if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print(f"ERROR: {ex}")
        sys.exit(1)
