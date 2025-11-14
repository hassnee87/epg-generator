import os
import sys
import gzip
import shutil
import xml.etree.ElementTree as ET
from io import BytesIO
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from datetime import datetime, timedelta, timezone
import re

# ========================
# Configurable parameters
# ========================

# 1) Input file URL (source EPG feed)
INPUT_URL = "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz"

# 2) Extracted/Downloaded file path under countries subfolder
#    This must be an XML file name (the code handles .xml.gz vs .xml automatically)
COUNTRIES_XML_PATH = os.path.join("countries", "UK.epg.xml")

# 3) Channel ID to read from the input EPG
CHANNEL_ID_TO_READ = "Al.Jazeera.HD.uk"

# 4) Output file path for the per-channel EPG under channels subfolder
OUTPUT_CHANNEL_XML_PATH = os.path.join("channels", "Al-Jazeera.xml")

# 5) Optional override Channel Name (if None, read from source EPG)
OUTPUT_CHANNEL_NAME = "Al Jazeera"

# 6) Optional override Channel ID (if None, keep as source channel id)
OUTPUT_CHANNEL_ID = "Al.Jazeera.English.qt"

# 7) Optional override Channel Logo URL (if None, read from source EPG)
OUTPUT_CHANNEL_LOGO = "https://thefilmtuition.com/tvlogo/Al-Jazeera.png"

# 8) Target timezone offset for output (Pakistan Standard Time +05:00)
TARGET_TZ_OFFSET = "+05:00"

# ========================
# Debug helpers
# ========================

def debug(msg):
    print(f"[DEBUG] {msg}")


# ========================
# Date/time helpers
# ========================

def parse_xmltv_datetime(dt_str):
    """
    Parse XMLTV datetime strings like 'YYYYMMDDHHMMSS +ZZZZ' or 'YYYYMMDDHHMMSS' (no offset).
    Returns an aware datetime in its stated timezone if offset present; otherwise treat as UTC.
    """
    # Extract base timestamp and optional offset
    m = re.match(r"^(\d{14})(?:\s*([+-]\d{4}))?$", dt_str)
    if not m:
        raise ValueError(f"Unrecognized datetime format: {dt_str}")
    base = m.group(1)
    offset = m.group(2)

    year = int(base[0:4])
    month = int(base[4:6])
    day = int(base[6:8])
    hour = int(base[8:10])
    minute = int(base[10:12])
    second = int(base[12:14])

    if offset:
        sign = 1 if offset.startswith("+") else -1
        off_hours = int(offset[1:3])
        off_mins = int(offset[3:5])
        tz = timezone(sign * timedelta(hours=off_hours, minutes=off_mins))
    else:
        tz = timezone.utc

    return datetime(year, month, day, hour, minute, second, tzinfo=tz)


def format_xmltv_datetime(dt, offset_str):
    """
    Format datetime into XMLTV-like 'YYYYMMDDHHMMSS +ZZZZ' using the provided offset string '+HH:MM' or '+HHMM'.
    The dt provided is assumed to be naive or aware; it will be converted to the target offset.
    """
    # Normalize offset string to '+HHMM'
    if re.match(r"^[+-]\d{2}:\d{2}$", offset_str):
        offset_compact = offset_str.replace(":", "")
    elif re.match(r"^[+-]\d{4}$", offset_str):
        offset_compact = offset_str
    else:
        raise ValueError(f"Invalid offset string: {offset_str}")

    sign = 1 if offset_compact.startswith("+") else -1
    off_hours = int(offset_compact[1:3])
    off_mins = int(offset_compact[3:5])
    target_tz = timezone(sign * timedelta(hours=off_hours, minutes=off_mins))

    # Convert dt to target timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_target = dt.astimezone(target_tz)

    return f"{dt_target.strftime('%Y%m%d%H%M%S')} {offset_compact}"


def get_server_datetime(url):
    """
    Try to get current datetime from the server hosting 'url' using HTTP 'Date' header.
    Fallback to UTC now if header missing.
    """
    debug(f"Fetching server date from HEAD: {url}")
    try:
        req = Request(url, method="HEAD")
        with urlopen(req, timeout=30) as resp:
            date_hdr = resp.headers.get("Date")
            if date_hdr:
                # Example: 'Fri, 14 Nov 2025 09:30:00 GMT'
                dt = datetime.strptime(date_hdr, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc)
                debug(f"Server date header found: {dt.isoformat()}")
                return dt
    except Exception as e:
        debug(f"HEAD request failed, will fallback to GET for date: {e}")
    # Fallback: UTC now
    now_utc = datetime.now(timezone.utc)
    debug(f"Using UTC now as server time: {now_utc.isoformat()}")
    return now_utc


def file_created_today(path, reference_dt_utc):
    """
    Check if file 'path' has creation date equal to 'today' based on 'reference_dt_utc'.
    We compare local file creation date (local timezone) to reference date converted to local timezone.
    """
    if not os.path.exists(path):
        return False
    st = os.stat(path)
    created_local = datetime.fromtimestamp(st.st_ctime).astimezone()
    ref_local = reference_dt_utc.astimezone(created_local.tzinfo)
    debug(f"Existing file creation date: {created_local.date()} | reference date: {ref_local.date()}")
    return created_local.date() == ref_local.date()


# ========================
# Network/IO helpers
# ========================

def ensure_dirs():
    for d in [os.path.dirname(COUNTRIES_XML_PATH), os.path.dirname(OUTPUT_CHANNEL_XML_PATH)]:
        if d and not os.path.exists(d):
            debug(f"Creating directory: {d}")
            os.makedirs(d, exist_ok=True)


def download_or_extract_input(url, out_xml_path, server_dt_utc):
    """
    Download or extract the input feed into out_xml_path.
    If a fresh file for today already exists, skip downloading.
    Supports .xml and .xml.gz based on URL path.
    """
    ensure_dirs()
    if file_created_today(out_xml_path, server_dt_utc):
        debug("Fresh EPG file for today already exists. Skipping download/extraction.")
        return

    parsed = urlparse(url)
    is_gz = parsed.path.endswith(".xml.gz")
    debug(f"Downloading input feed: {url} | gzip={is_gz}")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (EPG Generator)"})
    with urlopen(req, timeout=120) as resp:
        content = resp.read()

    if is_gz:
        debug(f"Decompressing GZIP content to: {out_xml_path}")
        with gzip.GzipFile(fileobj=BytesIO(content)) as gz:
            with open(out_xml_path, "wb") as f:
                shutil.copyfileobj(gz, f)
    else:
        debug(f"Saving XML content to: {out_xml_path}")
        with open(out_xml_path, "wb") as f:
            f.write(content)


# ========================
# EPG processing
# ========================

def read_source_channel_info(root, source_channel_id):
    """
    Read channel metadata (name, logo) from source EPG <channel id=...> element.
    """
    ch_el = root.find(f"./channel[@id='{source_channel_id}']")
    name = None
    logo = None
    if ch_el is not None:
        dn = ch_el.find("display-name")
        if dn is not None and dn.text:
            name = dn.text.strip()
        icon = ch_el.find("icon")
        if icon is not None:
            # XMLTV uses 'src' attribute for icon URL
            logo = icon.attrib.get("src")
    debug(f"Source channel info -> name: {name} | logo: {logo}")
    return name, logo


def detect_source_timezone(root, source_channel_id):
    """
    Detect timezone offset used in the source EPG for programmes of the channel.
    We'll inspect the first programme and parse its offset.
    """
    for prog in root.findall("programme"):
        if prog.attrib.get("channel") == source_channel_id:
            start_attr = prog.attrib.get("start")
            if start_attr:
                m = re.match(r"^\d{14}\s*([+-]\d{4})$", start_attr)
                if m:
                    src_offset = m.group(1)
                    debug(f"Detected source timezone offset from programme: {src_offset}")
                    return src_offset
                else:
                    debug("Programme start has no explicit offset; treating as +0000")
                    return "+0000"
    debug("No programmes found for channel to detect timezone; default to +0000")
    return "+0000"


def collect_programmes_for_days(root, source_channel_id, today_server_utc, target_offset_str):
    """
    Collect programmes for 'today' and next 2 days, converting times to target timezone.
    Selection is based on programme start date in target timezone.
    Returns a list of dicts with keys: start, stop, title, sub_title, desc.
    """
    # Build target tz
    # Accept '+HH:MM' or '+HHMM'
    if ":" in target_offset_str:
        off_h = int(target_offset_str[1:3])
        off_m = int(target_offset_str[4:6])
        sign = 1 if target_offset_str.startswith("+") else -1
    else:
        off_h = int(target_offset_str[1:3])
        off_m = int(target_offset_str[3:5])
        sign = 1 if target_offset_str.startswith("+") else -1
    target_tz = timezone(sign * timedelta(hours=off_h, minutes=off_m))

    # Determine 'today' in target timezone based on server time
    today_target = today_server_utc.astimezone(target_tz).date()
    valid_dates = {today_target,
                   (today_server_utc.astimezone(target_tz) + timedelta(days=1)).date(),
                   (today_server_utc.astimezone(target_tz) + timedelta(days=2)).date()}
    debug(f"Target timezone today: {today_target} | valid dates: {sorted(valid_dates)}")

    items = []
    for prog in root.findall("programme"):
        if prog.attrib.get("channel") != source_channel_id:
            continue
        start_attr = prog.attrib.get("start")
        stop_attr = prog.attrib.get("stop")
        if not start_attr or not stop_attr:
            continue

        try:
            start_dt = parse_xmltv_datetime(start_attr)
            stop_dt = parse_xmltv_datetime(stop_attr)
        except Exception as e:
            debug(f"Skipping programme due to datetime parse error: {e}")
            continue

        # Convert to target timezone for selection
        start_target = start_dt.astimezone(target_tz)
        prog_date = start_target.date()
        if prog_date not in valid_dates:
            continue

        # Prepare text fields
        title_el = prog.find("title")
        sub_el = prog.find("sub-title")
        desc_el = prog.find("desc")
        title = title_el.text.strip() if (title_el is not None and title_el.text) else ""
        sub_title = sub_el.text.strip() if (sub_el is not None and sub_el.text) else None
        desc = desc_el.text.strip() if (desc_el is not None and desc_el.text) else None

        items.append({
            "start_dt": start_dt,
            "stop_dt": stop_dt,
            "title": title,
            "sub_title": sub_title,
            "desc": desc
        })

    # Sort by start time
    items.sort(key=lambda x: x["start_dt"])
    debug(f"Collected {len(items)} programmes for 3-day window")
    return items


def write_channel_epg(out_path, channel_id, channel_name, channel_logo, programmes, target_offset_str):
    """
    Write the per-channel EPG XML to out_path with times converted to target offset.
    """
    debug(f"Writing channel EPG to: {out_path}")
    root = ET.Element("tv")
    # Channel definition
    ch = ET.SubElement(root, "channel", {"id": channel_id})
    dn = ET.SubElement(ch, "display-name")
    dn.text = channel_name
    if channel_logo:
        ET.SubElement(ch, "icon", {"src": channel_logo})

    # Programmes
    for item in programmes:
        p = ET.SubElement(root, "programme", {"channel": channel_id})
        p.set("start", format_xmltv_datetime(item["start_dt"], target_offset_str))
        p.set("stop", format_xmltv_datetime(item["stop_dt"], target_offset_str))

        t = ET.SubElement(p, "title")
        t.text = item["title"]
        if item["sub_title"]:
            st = ET.SubElement(p, "sub-title")
            st.text = item["sub_title"]
        if item["desc"]:
            d = ET.SubElement(p, "desc")
            d.text = item["desc"]

    # Write pretty-ish XML (ElementTree doesn't indent by default prior to 3.9; implement simple indentation)
    indent_xml(root)
    ensure_dirs()
    tree = ET.ElementTree(root)
    tree.write(out_path, encoding="utf-8", xml_declaration=True)


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
    debug("Starting Al-Jazeera EPG generation script")

    # Get current server datetime for 'today' baseline
    server_dt_utc = get_server_datetime(INPUT_URL)

    # Download/extract input to countries/uk.epg.xml (unless fresh for today)
    download_or_extract_input(INPUT_URL, COUNTRIES_XML_PATH, server_dt_utc)

    # Read the source XML
    debug(f"Reading source XML: {COUNTRIES_XML_PATH}")
    if not os.path.exists(COUNTRIES_XML_PATH):
        print(f"ERROR: Source XML not found at {COUNTRIES_XML_PATH}")
        sys.exit(1)
    tree = ET.parse(COUNTRIES_XML_PATH)
    root = tree.getroot()

    # Read channel metadata from source; allow overrides
    src_name, src_logo = read_source_channel_info(root, CHANNEL_ID_TO_READ)
    channel_name = OUTPUT_CHANNEL_NAME or (src_name or "Unknown Channel")
    channel_id = OUTPUT_CHANNEL_ID or CHANNEL_ID_TO_READ
    channel_logo = OUTPUT_CHANNEL_LOGO or src_logo
    debug(f"Final channel params -> id: {channel_id} | name: {channel_name} | logo: {channel_logo}")

    # Detect source timezone and log it
    src_tz = detect_source_timezone(root, CHANNEL_ID_TO_READ)
    debug(f"Source EPG timezone offset: {src_tz}")

    # Collect programmes for 3-day window and convert to target timezone
    programmes = collect_programmes_for_days(root, CHANNEL_ID_TO_READ, server_dt_utc, TARGET_TZ_OFFSET)

    # Write per-channel output XML in target timezone
    write_channel_epg(OUTPUT_CHANNEL_XML_PATH, channel_id, channel_name, channel_logo, programmes, TARGET_TZ_OFFSET)

    debug("EPG generation completed successfully")


if __name__ == "__main__":
    main()
