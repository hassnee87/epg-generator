import os
import gzip
import xml.etree.ElementTree as ET

PK_DIR = "pkchannels"
OUT_XML = os.path.join("package", "PK.epg.xml")
OUT_GZ = os.path.join("package", "PK.epg.xml.gz")

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
    for name in os.listdir(PK_DIR):
        if name.lower().endswith(".xml"):
            files.append(os.path.join(PK_DIR, name))
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
        items.append({
            "channel": p.attrib.get("channel"),
            "start": p.attrib.get("start"),
            "stop": p.attrib.get("stop"),
            "title": (p.findtext("title") or "").strip(),
            "sub": (p.findtext("sub-title") or None),
            "desc": (p.findtext("desc") or None),
        })
    return items

def write_out(channels, programmes):
    tv = ET.Element("tv")
    for ch in channels:
        c = ET.SubElement(tv, "channel", {"id": ch["id"]})
        dn = ET.SubElement(c, "display-name")
        dn.text = ch["name"]
        if ch["logo"]:
            ET.SubElement(c, "icon", {"src": ch["logo"]})
    for it in programmes:
        p = ET.SubElement(tv, "programme", {"channel": it["channel"]})
        if it["start"]:
            p.set("start", it["start"])
        if it["stop"]:
            p.set("stop", it["stop"])
        t = ET.SubElement(p, "title")
        t.text = it["title"]
        if it["sub"]:
            st = ET.SubElement(p, "sub-title")
            st.text = it["sub"]
        if it["desc"]:
            d = ET.SubElement(p, "desc")
            d.text = it["desc"]
    indent_xml(tv)
    ensure_dir(OUT_XML)
    ET.ElementTree(tv).write(OUT_XML, encoding="utf-8", xml_declaration=True)
    ensure_dir(OUT_GZ)
    with open(OUT_XML, "rb") as f_in, gzip.open(OUT_GZ, "wb") as f_out:
        f_out.write(f_in.read())

def main():
    debug("Aggregating PK channels")
    inputs = discover_inputs()
    channels_map = {}
    programmes = []
    for path in inputs:
        try:
            root = ET.parse(path).getroot()
        except Exception as e:
            debug(f"Skipping {path}: {e}")
            continue
        for info in parse_channel_info(root):
            if info["id"] not in channels_map:
                channels_map[info["id"]] = info
        programmes.extend(parse_programmes(root))
    channels_sorted = sorted(channels_map.values(), key=lambda x: (x["name"].lower(), x["id"].lower()))
    debug(f"Channels: {len(channels_sorted)} | Programmes: {len(programmes)}")
    write_out(channels_sorted, programmes)
    debug(f"Wrote: {OUT_XML} and {OUT_GZ}")

if __name__ == "__main__":
    main()

