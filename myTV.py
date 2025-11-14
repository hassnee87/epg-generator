import os
import gzip
import xml.etree.ElementTree as ET

CHANNELS_DIR = "channels"
OUTPUT_XML_PATH = os.path.join("package", "myTV.xml")
OUTPUT_GZ_PATH = os.path.join("package", "myTV.xml.gz")
INPUT_FILES = None

def debug(msg):
    print(f"[DEBUG] {msg}")

def ensure_dir(path):
    d = os.path.dirname(path)
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

def discover_inputs():
    files = []
    for name in os.listdir(CHANNELS_DIR):
        if name.lower().endswith(".xml"):
            files.append(name)
    files.sort()
    return files

def parse_channel_info(root):
    infos = []
    for ch in root.findall("channel"):
        cid = ch.attrib.get("id", "")
        dn = ch.find("display-name")
        name = dn.text.strip() if (dn is not None and dn.text) else ""
        icon = ch.find("icon")
        logo = icon.attrib.get("src") if (icon is not None) else None
        infos.append({"id": cid, "name": name, "logo": logo})
    return infos

def parse_programmes(root):
    items = []
    for p in root.findall("programme"):
        ch = p.attrib.get("channel")
        start = p.attrib.get("start")
        stop = p.attrib.get("stop")
        t = p.find("title")
        st = p.find("sub-title")
        d = p.find("desc")
        items.append({
            "channel": ch,
            "start": start,
            "stop": stop,
            "title": t.text.strip() if (t is not None and t.text) else "",
            "sub": st.text.strip() if (st is not None and st.text) else None,
            "desc": d.text.strip() if (d is not None and d.text) else None,
        })
    return items

def main():
    debug("Starting myTV aggregator")
    inputs = INPUT_FILES if INPUT_FILES else discover_inputs()
    inputs_full = [os.path.join(CHANNELS_DIR, f) for f in inputs]
    debug(f"Input files: {inputs}")

    channels_map = {}
    programmes = []

    for path in inputs_full:
        if not os.path.exists(path):
            debug(f"Skipping missing file: {path}")
            continue
        debug(f"Reading: {path}")
        tree = ET.parse(path)
        root = tree.getroot()
        for info in parse_channel_info(root):
            if info["id"] not in channels_map:
                channels_map[info["id"]] = info
        programmes.extend(parse_programmes(root))

    sorted_channels = sorted(channels_map.values(), key=lambda x: (x["name"].lower(), x["id"].lower()))
    debug(f"Total channels: {len(sorted_channels)} | Total programmes: {len(programmes)}")

    tv = ET.Element("tv")
    for ch in sorted_channels:
        c = ET.SubElement(tv, "channel", {"id": ch["id"]})
        dn = ET.SubElement(c, "display-name")
        dn.text = ch["name"]
        if ch["logo"]:
            ET.SubElement(c, "icon", {"src": ch["logo"]})

    for item in programmes:
        p = ET.SubElement(tv, "programme", {"channel": item["channel"]})
        if item["start"]:
            p.set("start", item["start"])
        if item["stop"]:
            p.set("stop", item["stop"])
        t = ET.SubElement(p, "title")
        t.text = item["title"]
        if item["sub"]:
            st = ET.SubElement(p, "sub-title")
            st.text = item["sub"]
        if item["desc"]:
            d = ET.SubElement(p, "desc")
            d.text = item["desc"]

    indent_xml(tv)
    ensure_dir(OUTPUT_XML_PATH)
    ET.ElementTree(tv).write(OUTPUT_XML_PATH, encoding="utf-8", xml_declaration=True)
    debug(f"Wrote XML: {OUTPUT_XML_PATH}")

    ensure_dir(OUTPUT_GZ_PATH)
    with open(OUTPUT_XML_PATH, "rb") as f_in:
        with gzip.open(OUTPUT_GZ_PATH, "wb") as f_out:
            f_out.write(f_in.read())
    debug(f"Wrote GZIP: {OUTPUT_GZ_PATH}")

if __name__ == "__main__":
    main()

