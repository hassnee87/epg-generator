import os
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

# Configurable variables
CHANNEL_NAME = "Generic Channel"
CHANNEL_ID = "Generic.Channel.pk"
CHANNEL_LOGO = "https://thefilmtuition.com/tvlogo/Generic-Channel.png"
PROGRAMMES_DURATION_MIN = 60
PROGRAMME_TITLE = "Generic Show"
PROGRAMME_SUBTITLE = "Generic Show Category"
PROGRAMME_DESCRIPTION = (
    "This is generic description of the Generic Show which is highly appreciated by viewers on our Generic Channel."
)
DAYS_OF_EPG_TO_GENERATE = 3
OUTPUT_FILE_NAME = "Generic-Channel.xml"

OUT_CHANNELS = os.path.join("channels", OUTPUT_FILE_NAME)
OUT_PKCHANNELS = os.path.join("pkchannels", OUTPUT_FILE_NAME)

def debug(msg):
    print(f"[DEBUG] {msg}")

def ensure_dirs():
    for p in [OUT_CHANNELS, OUT_PKCHANNELS]:
        d = os.path.dirname(p)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

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

def xml_time(dt):
    return dt.strftime("%Y%m%d%H%M%S +0500")

def build_generic_programmes():
    pst = timezone(timedelta(hours=5))
    now_pst = datetime.now(timezone.utc).astimezone(pst)
    programmes = []
    minutes = max(1, PROGRAMMES_DURATION_MIN)
    slots_per_day = int((24 * 60) / minutes)
    for day in range(DAYS_OF_EPG_TO_GENERATE):
        base_date = (now_pst + timedelta(days=day)).date()
        day_start = datetime(base_date.year, base_date.month, base_date.day, 0, 0, tzinfo=pst)
        for i in range(slots_per_day):
            s = day_start + timedelta(minutes=i * minutes)
            e = s + timedelta(minutes=minutes)
            programmes.append((s, e))
    return programmes

def write_xml(programmes):
    tv = ET.Element("tv")
    ch = ET.SubElement(tv, "channel", {"id": CHANNEL_ID})
    dn = ET.SubElement(ch, "display-name")
    dn.text = CHANNEL_NAME
    ET.SubElement(ch, "icon", {"src": CHANNEL_LOGO})
    for s, e in programmes:
        p = ET.SubElement(tv, "programme", {"channel": CHANNEL_ID})
        p.set("start", xml_time(s))
        p.set("stop", xml_time(e))
        t = ET.SubElement(p, "title")
        t.text = PROGRAMME_TITLE
        st = ET.SubElement(p, "sub-title")
        st.text = PROGRAMME_SUBTITLE
        d = ET.SubElement(p, "desc")
        d.text = PROGRAMME_DESCRIPTION
    indent_xml(tv)
    ensure_dirs()
    ET.ElementTree(tv).write(OUT_CHANNELS, encoding="utf-8", xml_declaration=True)
    ET.ElementTree(tv).write(OUT_PKCHANNELS, encoding="utf-8", xml_declaration=True)
    debug(f"Wrote {OUT_CHANNELS} and {OUT_PKCHANNELS}")

def main():
    progs = build_generic_programmes()
    write_xml(progs)

if __name__ == "__main__":
    main()

