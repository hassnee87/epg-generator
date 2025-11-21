import os
import gzip
import re
import xml.etree.ElementTree as ET
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone

CHANNEL_NAME = "J2"  # Channel display name
CHANNEL_ID = "J2-NZ"  # Channel id to write into output EPG
CHANNEL_LOGO = "https://thefilmtuition.com/tvlogo/J2-NZ.png"  # Channel logo URL
PROGRAMMES_DURATION_MIN = 60  # Duration in minutes for generic slots
PROGRAMME_TITLE = "Classic Hits"  # Title used for generic programmes
PROGRAMME_SUBTITLE = "Music"  # Subtitle used for generic programmes
PROGRAMME_DESCRIPTION = "J2 provides a non-stop music television experience, with a programming mix that includes both current hits and older classics."  # Description text
DAYS_OF_EPG_TO_GENERATE = 3  # Number of days to generate
OUTPUT_FILE_NAME = "J2-NZ.xml"  # Output filename base (no folder)
TARGET_TZ_OFFSET = "+05:00"  # Pakistan Standard Time

INPUT_URL = "https://i.mjh.nz/nzau/epg.xml.gz"  # External feed (.xml or .xml.gz)
COUNTRIES_XML_PATH = os.path.join("countries", "NZAU.epg.xml")  # Local countries XML path
CHANNEL_ID_TO_READ = "mjh-mood-1289"  # Source channel id to read from countries XML

# Toggle writing into pkchannels (set True to write; keep as False to only write into channels)
WRITE_PKCHANNELS = False  # Set to True to also write into pkchannels

def debug(msg):
    print(f"[DEBUG] {msg}")

def ensure_dirs():
    # Ensure required directories exist
    for d in [
        os.path.dirname(COUNTRIES_XML_PATH),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "channels"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "nzchannels"),
    ]:
        if d and not os.path.exists(d):
            debug(f"Creating directory: {d}")
            os.makedirs(d, exist_ok=True)

def get_server_datetime(url):
    try:
        req = Request(url, method="HEAD")
        with urlopen(req, timeout=30) as resp:
            date_hdr = resp.headers.get("Date")
            if date_hdr:
                return datetime.strptime(date_hdr, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc)
    except Exception:
        pass
    return datetime.now(timezone.utc)

def file_created_today(path, reference_dt_utc):
    if not os.path.exists(path):
        return False
    st = os.stat(path)
    modified_local = datetime.fromtimestamp(st.st_mtime).astimezone()
    ref_local = reference_dt_utc.astimezone(modified_local.tzinfo)
    debug(f"Existing file modified date: {modified_local.date()} | reference date: {ref_local.date()} | path: {path}")
    return modified_local.date() == ref_local.date()

def download_or_extract_input(url, out_xml_path, server_dt_utc):
    # Only download/extract when file missing or older than "today" (based on server date)
    if os.path.exists(out_xml_path):
        if file_created_today(out_xml_path, server_dt_utc):
            debug("Countries XML is fresh (created today); skip download/extraction.")
            return
        else:
            debug("Countries XML exists but is older; will refresh from external source.")
    else:
        debug("Countries XML does not exist; will download.")

    parsed = urlparse(url)
    is_gz = parsed.path.endswith(".xml.gz")
    debug(f"Downloading: {url} | gzip={is_gz}")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Generic Channel Fetch)"})
    with urlopen(req, timeout=120) as resp:
        content = resp.read()
    if is_gz:
        debug(f"Decompressing into: {out_xml_path}")
        with gzip.GzipFile(fileobj=BytesIO(content)) as gz:
            xml_bytes = gz.read()
        with open(out_xml_path, "wb") as f:
            f.write(xml_bytes)
    else:
        debug(f"Saving XML into: {out_xml_path}")
        with open(out_xml_path, "wb") as f:
            f.write(content)

def parse_xmltv_datetime(dt_str):
    m = re.match(r"^(\d{14})(?:\s*([+-]\d{4}))?$", dt_str)
    if not m:
        raise ValueError(f"Unrecognized datetime format: {dt_str}")
    base = m.group(1)
    offset = m.group(2)
    year = int(base[0:4]); month = int(base[4:6]); day = int(base[6:8]); hour = int(base[8:10]); minute = int(base[10:12]); second = int(base[12:14])
    if offset:
        sign = 1 if offset.startswith("+") else -1
        off_hours = int(offset[1:3]); off_mins = int(offset[3:5])
        tz = timezone(sign * timedelta(hours=off_hours, minutes=off_mins))
    else:
        tz = timezone.utc
    return datetime(year, month, day, hour, minute, second, tzinfo=tz)

def format_xmltv_datetime(dt, offset_str):
    compact = offset_str.replace(":", "") if ":" in offset_str else offset_str
    sign = 1 if compact.startswith("+") else -1
    off_h = int(compact[1:3]); off_m = int(compact[3:5])
    target_tz = timezone(sign * timedelta(hours=off_h, minutes=off_m))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_target = dt.astimezone(target_tz)
    return f"{dt_target.strftime('%Y%m%d%H%M%S')} {compact}"

def collect_programmes_for_days(root, source_channel_id, server_dt_utc, target_offset_str, days):
    if ":" in target_offset_str:
        off_h = int(target_offset_str[1:3]); off_m = int(target_offset_str[4:6]); sign = 1 if target_offset_str.startswith("+") else -1
    else:
        off_h = int(target_offset_str[1:3]); off_m = int(target_offset_str[3:5]); sign = 1 if target_offset_str.startswith("+") else -1
    target_tz = timezone(sign * timedelta(hours=off_h, minutes=off_m))
    base = server_dt_utc.astimezone(target_tz)
    valid_dates = { (base + timedelta(days=i)).date() for i in range(days) }
    items = []
    for prog in root.findall("programme"):
        if prog.attrib.get("channel") != source_channel_id:
            continue
        start_attr = prog.attrib.get("start"); stop_attr = prog.attrib.get("stop")
        if not start_attr:
            continue
        try:
            start_dt = parse_xmltv_datetime(start_attr)
            stop_dt = parse_xmltv_datetime(stop_attr) if stop_attr else None
        except Exception:
            continue
        start_target = start_dt.astimezone(target_tz)
        if start_target.date() not in valid_dates:
            continue
        title_el = prog.find("title"); sub_el = prog.find("sub-title"); desc_el = prog.find("desc")
        title = title_el.text.strip() if (title_el is not None and title_el.text) else PROGRAMME_TITLE
        sub = sub_el.text.strip() if (sub_el is not None and sub_el.text) else PROGRAMME_SUBTITLE
        desc = desc_el.text.strip() if (desc_el is not None and desc_el.text) else PROGRAMME_DESCRIPTION
        items.append({"start_dt": start_dt, "stop_dt": stop_dt, "title": title, "sub": sub, "desc": desc})
    items.sort(key=lambda x: x["start_dt"])
    for i in range(len(items)):
        if not items[i]["stop_dt"]:
            if i + 1 < len(items):
                items[i]["stop_dt"] = items[i + 1]["start_dt"]
            else:
                items[i]["stop_dt"] = items[i]["start_dt"] + timedelta(minutes=PROGRAMMES_DURATION_MIN)
    return items

def build_generic_programmes(server_dt_utc):
    pst = timezone(timedelta(hours=5))
    base_date = server_dt_utc.astimezone(pst).date()
    slots_per_day = int((24 * 60) / max(1, PROGRAMMES_DURATION_MIN))
    entries = []
    for day in range(DAYS_OF_EPG_TO_GENERATE):
        day_start = datetime(base_date.year, base_date.month, base_date.day, 0, 0, tzinfo=pst) + timedelta(days=day)
        for i in range(slots_per_day):
            s = day_start + timedelta(minutes=i * PROGRAMMES_DURATION_MIN)
            e = s + timedelta(minutes=PROGRAMMES_DURATION_MIN)
            entries.append({"start_dt": s, "stop_dt": e, "title": PROGRAMME_TITLE, "sub": PROGRAMME_SUBTITLE, "desc": PROGRAMME_DESCRIPTION})
    return entries

def indent_xml(elem, level=0):
    # Pretty-print XML for readability
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

def write_outputs(entries):
    # Build XMLTV document in memory
    tv = ET.Element("tv")
    ch = ET.SubElement(tv, "channel", {"id": CHANNEL_ID})
    dn = ET.SubElement(ch, "display-name"); dn.text = CHANNEL_NAME
    ET.SubElement(ch, "icon", {"src": CHANNEL_LOGO})
    for it in entries:
        p = ET.SubElement(tv, "programme", {"channel": CHANNEL_ID})
        p.set("start", format_xmltv_datetime(it["start_dt"], TARGET_TZ_OFFSET))
        p.set("stop", format_xmltv_datetime(it["stop_dt"], TARGET_TZ_OFFSET))
        t = ET.SubElement(p, "title"); t.text = it["title"]
        st = ET.SubElement(p, "sub-title"); st.text = it["sub"]
        d = ET.SubElement(p, "desc"); d.text = it["desc"]

    # Indent for clean formatting
    indent_xml(tv)

    # Write to channels folder
    out_channels = os.path.join("channels", OUTPUT_FILE_NAME)
    ensure_dirs()
    ET.ElementTree(tv).write(out_channels, encoding="utf-8", xml_declaration=True)
    with open(out_channels, "rb") as f_in, gzip.open(out_channels + ".gz", "wb") as f_out:
        f_out.write(f_in.read())
    debug(f"Wrote {out_channels} (+ .gz)")

    # Optional: write to nzchannels (uncomment to enable)
    out_nzchannels = os.path.join("nzchannels", OUTPUT_FILE_NAME)
    ET.ElementTree(tv).write(out_nzchannels, encoding="utf-8", xml_declaration=True)
    with open(out_nzchannels, "rb") as f_in, gzip.open(out_nzchannels + ".gz", "wb") as f_out:
        f_out.write(f_in.read())
    debug(f"Wrote {out_nzchannels} (+ .gz)")

def main():
    debug("Starting J2-NZ EPG with check")
    server_dt_utc = get_server_datetime(INPUT_URL)
    ensure_dirs()
    if not os.path.exists(COUNTRIES_XML_PATH) or not file_created_today(COUNTRIES_XML_PATH, server_dt_utc):
        download_or_extract_input(INPUT_URL, COUNTRIES_XML_PATH, server_dt_utc)
    entries = []
    if os.path.exists(COUNTRIES_XML_PATH):
        try:
            root = ET.parse(COUNTRIES_XML_PATH).getroot()
            entries = collect_programmes_for_days(root, CHANNEL_ID_TO_READ, server_dt_utc, TARGET_TZ_OFFSET, DAYS_OF_EPG_TO_GENERATE)
        except Exception as e:
            debug(f"Failed reading countries XML, will fallback to generic: {e}")
            entries = []
    if not entries:
        debug("Using generic fallback programmes")
        entries = build_generic_programmes(server_dt_utc)
    write_outputs(entries)
    debug("Completed")

if __name__ == "__main__":
    main()
