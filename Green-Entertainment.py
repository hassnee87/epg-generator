# GreenEntertainment.py - Python EPG Scraper and XML Generator
import requests
import json
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET
import os

# --- Main Configuration ---
OUTPUT_FILENAME = os.path.join("channels", "Green-Entertainment.xml")
OUTPUT_PATH_PKCHANNELS = os.path.join("pkchannels", "Green-Entertainment.xml")
EPG_DAYS = 7 # Scrape up to 7 days of EPG data

# Custom Timezone Definitions for channels
TIMEZONES = {
    "Asia/Karachi": pytz.timezone("Asia/Karachi"),
}

# Consolidated Channel List and Custom IDs/Names
CHANNELS = [
    {
        "xmltv_id": "Green.Entertainment.pk", 
        "display_name": "Green Entertainment", 
        "url": "https://backend.greenentertainment.tv/web/api/v1/dramas", # API Endpoint for all programs
        "logo_url": "https://thefilmtuition.com/tvlogo/Green-Entertainment.png", # Logo URL
        "timezone": "Asia/Karachi", 
        "scraper": "scrape_green_entertainment"
    },
]

# Helper map to convert day name (from API) to datetime weekday index (Monday=0)
DAY_MAP = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}

# --- Date and Time Helper Functions ---

def get_epg_dates(tz_str, days):
    """Returns a dictionary mapping Day Names to their upcoming datetime.date objects."""
    local_tz = TIMEZONES[tz_str]
    now = datetime.now(local_tz)
    
    date_map = {}
    today_weekday_index = now.weekday() # Monday is 0, Sunday is 6
    
    # Generate dates for the next EPG_DAYS
    for i in range(days):
        target_date = now.date() + timedelta(days=i)
        
        # Get the day name (e.g., 'Monday') for the target date
        day_name = target_date.strftime('%A')
        
        # Store the date object keyed by the day name
        date_map[day_name] = target_date
        
    return date_map

# --- Scraper Function ---

def scrape_green_entertainment(channel_info):
    """
    Scrapes Green Entertainment by fetching program details and weekly schedules 
    from a single JSON API endpoint.
    """
    programs = []
    tz_info = TIMEZONES[channel_info['timezone']]
    
    # Get the dictionary of upcoming dates, mapped by day name
    date_map = get_epg_dates(channel_info['timezone'], EPG_DAYS)
    
    # 1. Fetch Program Data from the API
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        all_programs = []
        for ep in [channel_info['url'], "https://backend.greenentertainment.tv/web/api/v1/tvshows"]:
            response = requests.get(ep, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and isinstance(data.get('data'), list):
                all_programs.extend(data['data'])
    except requests.exceptions.RequestException as e:
        print(f"    -> Network Error fetching API data: {e}")
        return []
    except json.JSONDecodeError:
        print("    -> ERROR: Failed to decode JSON response.")
        return []
    print(f"    -> Successfully fetched details for {len(all_programs)} programs (dramas + tvshows).")

    # 2. Iterate through Programs and Schedules
    
    # This set is used to collect all airings for all programs
    all_airings = [] 
    
    for program in all_programs:
        title = program.get('title')
        description = program.get('description', '').strip()
        schedule_entries = program.get('schedule', [])

        if not title or not schedule_entries:
            continue
            
        for schedule in schedule_entries:
            day_name = schedule.get('day')
            times = schedule.get('times', [])
            
            # Check if this day is within our next 7 days of interest
            if day_name not in date_map:
                continue
                
            program_date = date_map[day_name]

            for time_entry in times:
                time_str = time_entry.get('value') # e.g., "20:00"
                if not time_str:
                    continue
                    
                try:
                    hour, minute = map(int, time_str.split(':'))
                    
                    # Combine the program's date (from date_map) with its scheduled time
                    naive_start = datetime.combine(program_date, datetime.min.time()).replace(hour=hour, minute=minute, second=0)
                    start_dt = tz_info.localize(naive_start)

                    # --- Description Cleaning and Formatting ---
                    # Remove multiple spaces/newlines from the description
                    cleaned_description = ' '.join(description.split()).strip()

                    all_airings.append({
                        "start": start_dt,
                        "stop": start_dt + timedelta(hours=1), # Temporary default duration
                        "title": title,
                        "subtitle": None,
                        "channel": channel_info['xmltv_id'],
                        "desc": cleaned_description,
                    })
                except Exception as e:
                    # print(f"    -> Inner parsing error for {title} on {day_name} at {time_str}: {e}")
                    continue

    # 3. Time Correction: Calculate Durations
    
    # Sort all airings chronologically to properly calculate the stop time
    all_airings.sort(key=lambda x: x['start'])
    
    # Set the stop time of a program to the start time of the next program
    for i in range(len(all_airings)):
        if i + 1 < len(all_airings):
            # The stop time must be after the start time
            if all_airings[i+1]['start'] > all_airings[i]['start']:
                 all_airings[i]['stop'] = all_airings[i+1]['start']
        # If it's the last program in the list, leave the default duration (1 hour)
            
    seen = set()
    for a in all_airings:
        key = (a['start'], a['title'].lower())
        if key in seen:
            continue
        seen.add(key)
        programs.append(a)
    return programs


#
# >>>>> XML GENERATION FUNCTION (Central Function) <<<<<
#
# Reused from GeoEntertainment.py, modified to include the logo.
def generate_xmltv(all_programs, channel_infos):
    """Creates the epg.xml file in XMLTV format, including channel logos."""
    
    print(f"\n--- Generating XML File ---")
    tv_root = ET.Element("tv")

    # 1. Add <channel> definitions for all channels
    for info in channel_infos:
        channel_elem = ET.SubElement(tv_root, "channel", {"id": info['xmltv_id']})
        
        # Display Name
        display_name = ET.SubElement(channel_elem, "display-name")
        display_name.text = info['display_name']

        # Logo
        if info.get('logo_url'):
             icon_elem = ET.SubElement(channel_elem, "icon", {"src": info['logo_url']})


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
            
        # Add Description if present
        if prog.get('desc'):
            desc_elem = ET.SubElement(prog_elem, "desc", {"lang": "en"})
            desc_elem.text = prog['desc']

    # Finalize and write the XML file
    xml_string = ET.tostring(tv_root, encoding='utf-8').decode('utf8')
    
    # Manually prepend the XML declaration and re-introduce basic indentation
    formatted_xml = '<?xml version="1.0" encoding="utf-8"?>\n' + xml_string.replace('><', '>\n<')

    # --- Use the exact safe writing logic ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_channels = os.path.join(script_dir, OUTPUT_FILENAME)
    out_pkchannels = os.path.join(script_dir, OUTPUT_PATH_PKCHANNELS)
    os.makedirs(os.path.dirname(out_channels), exist_ok=True)
    os.makedirs(os.path.dirname(out_pkchannels), exist_ok=True)
    with open(out_channels, "w", encoding="utf-8") as f:
        f.write(formatted_xml)
    with open(out_pkchannels, "w", encoding="utf-8") as f:
        f.write(formatted_xml)
    print(f"Successfully created {out_channels} with {len(all_programs)} programs.")
    print(f"Successfully created {out_pkchannels} with {len(all_programs)} programs.")


# --- Main Execution ---
if __name__ == "__main__":
    
    all_programs = []
    
    for channel in CHANNELS:
        scraper_func = globals().get(channel['scraper'])
        
        if scraper_func:
            print(f"--- Scraping {channel['display_name']} ---")
            try:
                programs = scraper_func(channel)
                all_programs.extend(programs)
                print(f"-> Scraped {len(programs)} programs for {channel['display_name']}.")
            except Exception as e:
                print(f"!!! CRITICAL ERROR scraping {channel['display_name']}: {e}")
        else:
            print(f"!!! WARNING: No scraper function found for {channel['display_name']}.")

    # --- GUARANTEED XML GENERATION BLOCK ---
    try:
        generate_xmltv(all_programs, CHANNELS)
    except Exception as e:
        print(f"!!! FAILED to generate XML file at the end of execution: {e}")
