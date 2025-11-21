import os
import gzip
import shutil
from io import BytesIO
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from http.client import IncompleteRead
from datetime import datetime, timezone

# ========================
# Configuration: add more feeds here
# Each entry: {"url": "...", "out_xml": "countries/<name>.xml"}
# Supports .xml and .xml.gz
FEEDS = [
        {"url": "https://epgshare01.online/epgshare01/epg_ripper_AU1.xml.gz", "out_xml": os.path.join("countries", "AU.epg.xml")},
        {"url": "https://epgshare01.online/epgshare01/epg_ripper_CA2.xml.gz", "out_xml": os.path.join("countries", "CA.epg.xml")},
        {"url": "https://epgshare01.online/epgshare01/epg_ripper_IN1.xml.gz", "out_xml": os.path.join("countries", "IN.epg.xml")},
        {"url": "https://iptv-epg.org/files/epg-in.xml", "out_xml": os.path.join("countries", "IN2.epg.xml")},
        {"url": "https://epgshare01.online/epgshare01/epg_ripper_NZ1.xml.gz", "out_xml": os.path.join("countries", "NZ.epg.xml")},
        {"url": "https://epgshare01.online/epgshare01/epg_ripper_PH2.xml.gz", "out_xml": os.path.join("countries", "PH.epg.xml")},
        {"url": "https://programtv.ru/xmltv.xml.gz", "out_xml": os.path.join("countries", "RU.epg.xml")},
        {"url": "https://epgshare01.online/epgshare01/epg_ripper_SG1.xml.gz", "out_xml": os.path.join("countries", "SG.epg.xml")},
        {"url": "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz", "out_xml": os.path.join("countries", "UK.epg.xml")},
        {"url": "https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz", "out_xml": os.path.join("countries", "US.epg.xml")},
        {"url": "https://epgshare01.online/epgshare01/epg_ripper_ZA1.xml.gz", "out_xml": os.path.join("countries", "ZA.epg.xml")},

        {"url": "https://i.mjh.nz/nzau/epg.xml.gz", "out_xml": os.path.join("countries", "NZAU.epg.xml")},
        {"url": "https://epgshare01.online/epgshare01/epg_ripper_ASIANTELEVISION1.xml.gz", "out_xml": os.path.join("countries", "PK-IN.epg.xml")},

        
        {"url": "https://epgshare01.online/epgshare01/epg_ripper_DISTROTV1.xml.gz", "out_xml": os.path.join("countries", "USA-DistroTV.epg.xml")},
        {"url": "https://i.mjh.nz/Plex/us.xml.gz", "out_xml": os.path.join("countries", "US-Plex.epg.xml")},
        {"url": "https://i.mjh.nz/PlutoTV/us.xml.gz", "out_xml": os.path.join("countries", "US-Pluto.epg.xml")},

        {"url": "https://i.mjh.nz/SamsungTVPlus/ca.xml.gz", "out_xml": os.path.join("countries", "CA-Samsung.epg.xml")},
        {"url": "https://i.mjh.nz/SamsungTVPlus/gb.xml.gz", "out_xml": os.path.join("countries", "UK-Samsung.epg.xml")},
        {"url": "https://i.mjh.nz/SamsungTVPlus/us.xml.gz", "out_xml": os.path.join("countries", "US-Samsung.epg.xml")},

        
        {"url": "https://raw.githubusercontent.com/BuddyChewChew/tubi-scraper/refs/heads/main/tubi_epg.xml", "out_xml": os.path.join("countries", "US-Tubi.epg.xml")},
        
        {"url": "https://raw.githubusercontent.com/BuddyChewChew/xumo-playlist-generator/main/playlists/xumo_epg.xml.gz", "out_xml": os.path.join("countries", "US-Xumo.epg.xml")},

        
    
    # Add more feeds as needed
]


def debug(msg):
    print(f"[DEBUG] {msg}")


def ensure_dir_for(path):
    d = os.path.dirname(path)
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
    created_local = datetime.fromtimestamp(st.st_ctime).astimezone()
    ref_local = reference_dt_utc.astimezone(created_local.tzinfo)
    return created_local.date() == ref_local.date()


def download_or_extract(url, out_xml):
    server_dt = get_server_datetime(url)
    ensure_dir_for(out_xml)
    if file_created_today(out_xml, server_dt):
        debug(f"Fresh file exists for today, skipping: {out_xml}")
        return

    is_gz = urlparse(url).path.endswith('.xml.gz')
    debug(f"Downloading: {url}")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Fetch EPGs)"})
    content = None
    attempts = 3
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(req, timeout=120) as resp:
                content = resp.read()
            break
        except IncompleteRead as e:
            debug(f"IncompleteRead on attempt {attempt}/{attempts}: {e}")
            if attempt == attempts:
                raise
        except Exception as e:
            debug(f"Download failure on attempt {attempt}/{attempts}: {e}")
            if attempt == attempts:
                raise
    if is_gz:
        debug(f"Decompressing to: {out_xml}")
        with gzip.GzipFile(fileobj=BytesIO(content)) as gz:
            with open(out_xml, 'wb') as f:
                shutil.copyfileobj(gz, f)
    else:
        debug(f"Saving XML to: {out_xml}")
        with open(out_xml, 'wb') as f:
            f.write(content)


def main():
    debug("Starting bulk EPG fetcher")
    for entry in FEEDS:
        try:
            download_or_extract(entry["url"], entry["out_xml"])
        except Exception as e:
            debug(f"Failed to process {entry['url']}: {e}")
    debug("Bulk fetch completed")


if __name__ == "__main__":
    main()
