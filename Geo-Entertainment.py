# GeoEntertainment.py - Python EPG Scraper and XML Generator
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET
import os
import json
import re # <-- NEW: Import for regular expressions

# --- Main Configuration ---
OUTPUT_FILENAME = os.path.join("channels", "Geo-Entertainment.xml")
OUTPUT_PATH_PKCHANNELS = os.path.join("pkchannels", "Geo-Entertainment.xml")
EPG_DAYS = 7 # Scrape up to 7 days of EPG data

# Custom Timezone Definitions for channels
TIMEZONES = {
    "Asia/Karachi": pytz.timezone("Asia/Karachi"),
    "UTC+05:00": pytz.timezone("Asia/Karachi"),
    "America/New_York": pytz.timezone("America/New_York"),
    "Europe/London": pytz.timezone("Europe/London"),
    "Asia/Dubai": pytz.timezone("Asia/Dubai"),
    "America/Vancouver": pytz.timezone("America/Vancouver"),
}

# Consolidated Channel List and Custom IDs/Names
CHANNELS = [
    # --- Geo Entertainment: HTML Scrape for 1 Day ---
    {"xmltv_id": "Geo.Entertainment.pk", "display_name": "Geo Entertainment", "url": "https://harpalgeo.tv/schedule", "timezone": "Asia/Karachi", "scraper": "scrape_harpalgeo"},
]

# Helper function to convert time string (e.g., "08:00 PM") to datetime
def parse_time(time_str, date_obj, tz_info):
    """Parses time string, combines with date, and localizes timezone."""
    try:
        # Handle formats like "01:30 AM" or "1:30 PM" (12-hour format)
        time_part = datetime.strptime(time_str.upper(), '%I:%M %p').time()
    except ValueError:
        try:
            # Handle formats like "0800" or "1530" (24-hour format)
            time_part = datetime.strptime(time_str, '%H%M').time()
        except Exception:
            # Fallback for unknown time
            return tz_info.localize(datetime.combine(date_obj, datetime.now().time()))
            
    local_dt = datetime.combine(date_obj, time_part)
    return tz_info.localize(local_dt)

# Helper function to get the current day's date list
def get_epg_dates(tz_str, days):
    """Returns a list of datetime.date objects for scraping."""
    local_tz = TIMEZONES[tz_str]
    today = datetime.now(local_tz).date()
    return [today + timedelta(days=i) for i in range(days)]

# --- NEW HELPER FUNCTIONS FOR DESCRIPTION FETCHING ---

def get_program_description_url(title):
    """
    Generates the description page URL from the program title based on Geo's logic.
    - Spaces are replaced by hyphens.
    - If title ends with ' <number>', the space before the number is removed.
    """
    if not title:
        return None
        
    # 1. Apply the 'Case No 9' logic: remove space before a number at the end
    # Matches ' <number>' at the end, e.g., " No 9", " No 90"
    processed_title = re.sub(r'\s(\d+)$', r'\1', title)
    
    # 2. Apply the 'Mann Mast Malang' logic: replace remaining spaces with hyphens
    processed_title = processed_title.replace(' ', '-')
    
    base_url = "https://harpalgeo.tv/program/"
    return f"{base_url}{processed_title}"

def fetch_description_and_cast(program_title):
    """
    Fetches the description and cast information from the program's dedicated page.
    Returns a dictionary {'description': '...', 'cast': '...'}
    """
    description_url = get_program_description_url(program_title)
    if not description_url:
        return {}

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(description_url, headers=headers, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        # print(f"    -> WARNING: Failed to fetch description for '{program_title}': {e}")
        return {}

    soup = BeautifulSoup(response.content, 'html.parser')
    
    full_description = []
    
    # 1. Fetch Synopsis (Description)
    synopsis_div = soup.select_one('.synopsis_content')
    if synopsis_div:
        # Replace <br /> with ", " (The provided example HTML doesn't have <br />, 
        # but this handles the request. Using get_text for <p> tags handles the newlines.)
        for br in synopsis_div.find_all('br'):
            br.replace_with(', ')
            
        # Extract text, joining paragraphs with a space or newline.
        # Since paragraphs already introduce separation, we'll strip all tags and clean the text.
        synopsis_text = synopsis_div.get_text('\n', strip=True)
        if synopsis_text:
            full_description.append(synopsis_text)

    # 2. Fetch Cast
    cast_content = []
    cast_body = soup.select_one('.panel-body')
    if cast_body:
        # Extract all text from <li><p>...</p></li> structures.
        cast_items = cast_body.find_all('li')
        
        # Extract and clean cast names.
        cast_names = []
        for item in cast_items:
            # Using get_text(strip=True) to grab the clean text from inside the <li><p> tags
            name = item.get_text(strip=True)
            if name:
                cast_names.append(name)
        
        # Join cast names as requested: replace "</p></li><li>" with ", ". 
        # Since we extracted names into a list, we join them with ", "
        if cast_names:
            cast_string = ", ".join(cast_names)
            # Add a line break and "Cast: " before the cast list
            full_description.append(f"\n\nCast: {cast_string}")

    return {"description": "\n".join(full_description).strip()}

# --- Scraper Functions ---

#
# >>>>> REVISED SCRAPER FOR GEO ENTERTAINMENT (Description Fetching Added) <<<<<
#
def scrape_harpalgeo(channel_info):
    """
    Scrapes Geo Entertainment, now including an attempt to fetch descriptions.
    """
    programs = []
    tz_info = TIMEZONES[channel_info['timezone']]
    dates_to_scrape = get_epg_dates(channel_info['timezone'], EPG_DAYS)
    
    # CRITICAL: Add a User-Agent header
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(channel_info['url'], headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"    -> Network Error or HTTP Status Issue: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Target containers for all 7 days.
    # Day 1 is in the first section (carousel1)
    # Days 2-7 are in the second section (big_sec2)
    schedule_blocks = []
    
    # 1. Get Day 1 programs (Carousel 1 structure)
    day1_block = soup.select_one('.carousel1 .owl-one')
    if day1_block:
        schedule_blocks.append(day1_block)
        
    # 2. Get Days 2-7 programs (big_sec2 tab structure)
    big_sec2 = soup.select_one('.big_sec2')
    if big_sec2:
        # Find all individual day tabs/schedule wrappers inside big_sec2. 
        day_blocks_2_to_7 = big_sec2.select('.tab-pane')
        schedule_blocks.extend(day_blocks_2_to_7)

    if not schedule_blocks:
        print("    -> ERROR: Could not find the main schedule containers (.carousel1 or .big_sec2).")
        return []

    print(f"    -> Found {len(schedule_blocks)} daily schedule blocks.")

    # Process programs day by day
    for index, block in enumerate(schedule_blocks):
        if index >= EPG_DAYS: 
            break
            
        current_date = dates_to_scrape[index]
        current_dt = datetime.combine(current_date, datetime.min.time()).replace(tzinfo=tz_info)
        
        # Use the precise selector for the program item within the block
        show_items = block.select('.car_bx_main.car_bx1')
        
        if not show_items:
            continue
            
        daily_programs = []
        
        for item in show_items:
            try:
                # 1. Get Time from <h3>
                time_tag = item.select_one('h3')
                time_str = time_tag.text.strip() if time_tag else None
                
                # 2. Get Title and Subtitle from <p> tags
                p_tags = item.select('p')
                title = p_tags[0].text.strip() if len(p_tags) >= 1 else "Unknown Program"
                subtitle = p_tags[1].text.strip() if len(p_tags) >= 2 and p_tags[1].text.strip() not in ('', title) else None
                
                if not time_str:
                    continue

                start_dt = parse_time(time_str, current_dt.date(), tz_info)
                
                # Update the current reference time for the next item in the same day
                current_dt = start_dt

                stop_dt = start_dt + timedelta(hours=1) # Default stop time
                
                # --- NEW: Fetch Description ---
                description_data = fetch_description_and_cast(title)
                
                daily_programs.append({
                    "start": start_dt,
                    "stop": stop_dt,
                    "title": title,
                    "subtitle": subtitle if subtitle and not subtitle.startswith('Ep.') else title + ' - ' + subtitle if subtitle else None,
                    "channel": channel_info['xmltv_id'],
                    "desc": description_data.get('description'), # <-- NEW: Add description
                })

            except Exception as e:
                # print(f"    -> Inner parsing error on day {index} for {title}: {e}")
                continue

        # Time Correction: Set stop time to the start time of the next program within the same day
        for i in range(len(daily_programs)):
            if i + 1 < len(daily_programs):
                daily_programs[i]['stop'] = daily_programs[i+1]['start']
        
        programs.extend(daily_programs)

    # Final Time Correction (linking days - crucial for the last item of each day)
    for i in range(len(programs)):
        if i + 1 < len(programs):
            # Ensure stop time does not fall before start time due to day link
            if programs[i+1]['start'] > programs[i]['start']:
                programs[i]['stop'] = programs[i+1]['start']
            
    return programs



#
# >>>>> XML GENERATION FUNCTION (MODIFIED to include description) <<<<<
#
# --- XML Generation Logic (Central Function) ---
def generate_xmltv(all_programs, channel_infos):
    """Creates the epg.xml file in XMLTV format."""
    
    print(f"\n--- Generating XML File ---")
    tv_root = ET.Element("tv")

    # 1. Add <channel> definitions for all channels
    for info in channel_infos:
        channel_elem = ET.SubElement(tv_root, "channel", {"id": info['xmltv_id']})
        display_name = ET.SubElement(channel_elem, "display-name")
        display_name.text = info['display_name']
        icon_elem = ET.SubElement(channel_elem, "icon", {"src": "https://thefilmtuition.com/tvlogo/Geo-Entertainment.png"})

    # 2. Add <programme> data
    if not all_programs:
        print("WARNING: No program data was found.")
    
    all_programs.sort(key=lambda x: x['start'])

    for prog in all_programs:
        # XMLTV timestamp format: YYYYMMDDHHMMSS +HHMM
        start_time_str = prog['start'].strftime('%Y%m%d%H%M%S ') + prog['start'].strftime('%z')
        stop_time_str = prog['stop'].strftime('%Y%m%d%H%M%S ') + prog['stop'].strftime('%z')
        
        prog_elem = ET.SubElement(tv_root, "programme", {
            "start": start_time_str,
            "stop": stop_time_str,
            "channel": prog['channel']
        })

        title_elem = ET.SubElement(prog_elem, "title", {"lang": "en"})
        title_elem.text = prog['title']

        # Ensure subtitle is added if present
        if prog.get('subtitle'):
            sub_elem = ET.SubElement(prog_elem, "sub-title", {"lang": "en"})
            sub_elem.text = prog['subtitle']
            
        # --- NEW: Add Description if present ---
        if prog.get('desc'):
            desc_elem = ET.SubElement(prog_elem, "desc", {"lang": "en"})
            desc_elem.text = prog['desc']

    # Finalize and write the XML file
    xml_string = ET.tostring(tv_root, encoding='utf-8').decode('utf8')
    
    # Manually prepend the XML declaration and re-introduce basic indentation
    formatted_xml = '<?xml version="1.0" encoding="utf-8"?>\n' + xml_string.replace('><', '>\n<')

    # --- Use the exact safe writing logic ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, OUTPUT_FILENAME)
    output_path = os.path.join(script_dir, OUTPUT_PATH_PKCHANNELS)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(formatted_xml)
    
    print(f"Successfully created {output_path} with {len(all_programs)} programs.")


# --- Main Execution ---
if __name__ == "__main__":
    
    all_programs = []
    
    for channel in CHANNELS:
        # Get the corresponding scraper function based on the channel's 'scraper' key
        scraper_func = globals().get(channel['scraper'])
        
        if scraper_func:
            print(f"--- Scraping {channel['display_name']} ---")
            try:
                programs = scraper_func(channel)
                all_programs.extend(programs)
                print(f"-> Scraped {len(programs)} programs for {channel['display_name']}.")
            except Exception as e:
                # Catch errors per-channel so one failure doesn't stop the whole script
                print(f"!!! CRITICAL ERROR scraping {channel['display_name']}: {e}")
        else:
            print(f"!!! WARNING: No scraper function found for {channel['display_name']}.")

    # --- GUARANTEED XML GENERATION BLOCK ---
    try:
        generate_xmltv(all_programs, CHANNELS)
    except Exception as e:
        print(f"!!! FAILED to generate XML file at the end of execution: {e}")
