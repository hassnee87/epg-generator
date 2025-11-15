# HumTV.py - Python EPG Scraper and XML Generator
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET
import os
import re

# --- Main Configuration ---
OUTPUT_FILENAME = os.path.join("channels", "Hum-TV.xml")
OUTPUT_PATH_PKCHANNELS = os.path.join("pkchannels", "Hum-TV.xml")
EPG_DAYS = 7 

# Custom Timezone Definitions
TIMEZONES = {
    "Asia/Karachi": pytz.timezone("Asia/Karachi"),
}

# Consolidated Channel List
CHANNELS = [
    {
        "xmltv_id": "Hum.TV.pk", 
        "display_name": "Hum TV", 
        "url": "https://hum.tv/schedule/", 
        "logo_url": "https://thefilmtuition.com/tvlogo/Hum-TV.png", 
        "timezone": "Asia/Karachi", 
        "scraper": "scrape_humtv"
    },
]

# Helper map to convert HUM TV's 3-letter day codes to datetime weekday index (Monday=0)
DAY_MAP = {
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3, 
    "FRI": 5, "SAT": 6, "SUN": 7, # Adjusted to avoid conflict: 5=Fri, 6=Sat, 7=Sun
}
# Helper map for weekday check (Monday=0 to Friday=4)
WEEKDAY_INDEX_MAP = {
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4
}


# --- Shared Functions (No changes needed here) ---

def get_epg_dates(tz_str, days):
    """Returns a dictionary mapping Day Code (MON) to their upcoming datetime.date objects."""
    local_tz = TIMEZONES[tz_str]
    now = datetime.now(local_tz)
    date_map = {}
    
    # We use python's 0=Mon, 6=Sun indexing for calculation
    for i in range(days):
        target_date = now.date() + timedelta(days=i)
        weekday_index = target_date.weekday()
        # Map python's 0-6 index back to site's 3-letter code
        site_day_code = [key for key, value in WEEKDAY_INDEX_MAP.items() if value == weekday_index]
        if not site_day_code:
            if weekday_index == 5: site_day_code = ["SAT"]
            elif weekday_index == 6: site_day_code = ["SUN"]
        
        if site_day_code:
            date_map[site_day_code[0]] = target_date
    return date_map


def clean_title(href_url, fallback_img_alt):
    """Extracts, cleans, and Title-cases the program title from the 'a href' URL."""
    try:
        match = re.search(r'dramas/([^/]+)/?$', href_url)
        if match:
            title_slug = match.group(1)
            title = title_slug.replace('-', ' ').title()
            if title.strip() not in ["", "dramas"]: 
                return title.strip()
                
        if fallback_img_alt:
            title = fallback_img_alt.strip()
            if title.lower() in ['', 'program', 'hum kahaniyan', '2']:
                 return "Hum Kahaniyan" 
            return title.replace('-', ' ').title()

    except Exception:
        pass
        
    return "Generic Program" 

# --- Description Scraper (No changes needed here) ---

def fetch_program_details(program_url):
    """
    Visits the program's dedicated page and scrapes the structured description.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(program_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        content_section = soup.find('section', class_='category-content')
        if not content_section:
             return None
             
        description_parts = []
        # ... (rest of description fetching logic remains the same) ...
        # 1. <div class="cat_desc"> content
        cat_desc_div = content_section.find('div', class_='cat_desc')
        if cat_desc_div:
            description_parts.append(cat_desc_div.get_text(strip=True))

        # 2. <div class="auth_cat"> content (followed by a line break)
        auth_cat_div = content_section.find('div', class_='auth_cat')
        if auth_cat_div:
            auth_rows = [row.get_text(strip=True) for row in auth_cat_div.find_all('div', class_='auth_cat_row')]
            if auth_rows:
                description_parts.append("\n" + ", ".join(auth_rows) + ".")

        # 3. <div class="key_cat"> and <div class="val_cat"> content (followed by a line break)
        key_cat_div = content_section.find('div', class_='key_cat')
        val_cat_div = content_section.find('div', class_='val_cat')
        
        if key_cat_div and val_cat_div:
            key_text = key_cat_div.get_text(strip=True)
            val_text = val_cat_div.get_text(strip=True)
            
            val_text_formatted = val_text.replace(',', ', ')
            description_parts.append("\n" + key_text + " " + val_cat_div.get_text(strip=True).replace(',', ', '))
            
        final_description = "\n".join(description_parts).strip()
        
        # FIX: Remove the last line if it contains "Writer:"
        lines = final_description.split('\n')
        if lines and "Writer:" in lines[-1]:
            lines.pop()
            final_description = "\n".join(lines).strip()
            
        # FIX: Replace stray ",." with just "."
        final_description = final_description.replace(',.', '.')
            
        return final_description

    except Exception as e:
        # If any fetching error occurs, return None
        return None 

# --- Main Scraper Function (FINAL SOLUTION) ---

def scrape_humtv(channel_info):
    """
    Scrapes the Hum TV schedule, fetches details, then injects known missing slots.
    """
    all_airings = []
    tz_info = TIMEZONES[channel_info['timezone']]
    date_map = get_epg_dates(channel_info['timezone'], EPG_DAYS)
    channel_id = channel_info['xmltv_id']
    
    # 1. Fetch and Parse HTML
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(channel_info['url'], headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"    -> Network Error fetching Hum TV schedule: {e}")
        return []

    schedule_root = soup.find('div', id='divShowHide')
    if not schedule_root:
        return []

    # 2. Extract Data
    day_panels = soup.find_all('div', class_='vc_tta-panel')
        
    for panel in day_panels:
        day_code_elem = panel.find('span', class_='vc_tta-title-text')
        if not day_code_elem: continue
        day_code = day_code_elem.text.strip()
        
        if day_code not in date_map: continue
            
        program_date = date_map[day_code]
        raw_daily_airings = []

        program_blocks = panel.find_all('div', class_='wpb_text_column wpb_content_element')
        
        for block in program_blocks:
            
            # --- Time Extraction ---
            time_tag = block.find('div', class_='sch_time')
            if not time_tag: continue
            time_text = time_tag.find('div', class_='inner_time').get_text(strip=True)
            if '–' not in time_text: continue
                
            try:
                start_time_str = time_text.split('–')[0].strip()
                end_time_str = time_text.split('–')[1].strip()

                hour, minute = map(int, start_time_str.split(':'))
                end_hour, end_minute = map(int, end_time_str.split(':'))
                
                naive_start = datetime.combine(program_date, datetime.min.time()).replace(hour=hour, minute=minute, second=0)
                start_dt = tz_info.localize(naive_start)
                naive_stop = datetime.combine(program_date, datetime.min.time()).replace(hour=end_hour, minute=end_minute, second=0)
                stop_dt_scraped = tz_info.localize(naive_stop)
                
                if stop_dt_scraped <= start_dt:
                    stop_dt_scraped += timedelta(days=1)


                # --- Title & URL Extraction (using the broader search logic) ---
                primary_link_tag = block.find('a')
                img_tag = block.find('img')
                
                href_url = None
                if primary_link_tag:
                    potential_url = primary_link_tag.get('href')
                    # Check if the URL is a relative link or points to hum.tv
                    if potential_url and ('hum.tv' in potential_url or potential_url.startswith('/')):
                        href_url = potential_url
                
                img_alt = img_tag.get('alt', '').strip() if img_tag else ''

                title = clean_title(href_url, img_alt)
                
                # Filter out zero-duration duplicates 
                if (stop_dt_scraped - start_dt) <= timedelta(minutes=1): continue
                
                # --- FINAL FIX: M-F 06:00 is forced, 05:00 generic is skipped ---
                description = None 
                
                # Check for the specific problematic time slots
                is_0600_slot = start_dt.hour == 6
                is_0500_slot = start_dt.hour == 5
                is_weekday = day_code in WEEKDAY_INDEX_MAP
                is_generic_title = title in ["Generic Program", "Hum Kahaniyan"]

                # 1. Handle the 05:00 persistent generic issue (Skip to allow OST injection)
                if is_0500_slot and is_generic_title:
                    continue # Skip the 05:00 generic program entirely (cleared for OST injection)

                # 2. Handle the 06:00 M-F No-Link issue (Force title/description)
                if is_0600_slot and is_weekday and not href_url:
                    title = "Hum Kahaniyan"
                    description = "Start every morning with Hum Kahaniyan! Watch your favourite blockbuster drama serials, first thing in the morning."
                    # Do not attempt to fetch details, rely on forced values.
                    
                elif href_url:
                    # For all other programs (including 06:00 SAT/SUN, 15:00, and non-generic 05:00), fetch details.
                    description = fetch_program_details(href_url)
                
                # If description is inaccessible/unavailable (None or empty string) after fetch attempt, use the title
                if not description:
                    description = title

                raw_daily_airings.append({
                    "start": start_dt,
                    "stop": stop_dt_scraped, 
                    "title": title,
                    "subtitle": None,
                    "channel": channel_id,
                    "desc": description, 
                    "url": href_url
                })

            except Exception as e:
                # print(f"    -> Error processing program block at {time_text}: {e}")
                continue
        
        # --- MANDATORY INJECTION STEP (To place OST at 05:00 and 15:00) ---
        
        OST_TITLE = "Hum TV OST"
        OST_DESC = "A show that plays the best Hum TV Original Soundtracks from famous dramas, back to back."
        daily_airings = []
        
        # Target the slots that MUST be OST 
        OST_SLOTS_HOURS = [5, 15] # 05:00 and 15:00 hours
        
        # 1. Inject the mandatory OST entries
        for hour in OST_SLOTS_HOURS:
            ost_start = tz_info.localize(datetime.combine(program_date, datetime.min.time()).replace(hour=hour))
            ost_stop = ost_start + timedelta(hours=1)
            
            # We ONLY inject if no real program already exists at that time.
            # We already removed the generic 05:00 placeholder, so this is guaranteed for 05:00.
            if not any(p['start'] == ost_start and p['title'] != OST_TITLE for p in raw_daily_airings):
                 daily_airings.append({
                    "start": ost_start,
                    "stop": ost_stop,
                    "title": OST_TITLE,
                    "subtitle": None,
                    "channel": channel_id,
                    "desc": OST_DESC, 
                    "url": None
                })
            else:
                pass 

        # 2. Add all remaining original programs 
        for p in raw_daily_airings:
             # Ensure we don't duplicate the 15:00 OST if the raw data had it correctly titled
             if p['start'].hour == 5 and p['title'] == OST_TITLE:
                 continue
             daily_airings.append(p)

        # 3. Sort the final list
        daily_airings.sort(key=lambda x: x['start'])

        # 4. Enforce EPG Rule: Current program stops when next one starts.
        for i in range(len(daily_airings) - 1):
            daily_airings[i]['stop'] = daily_airings[i+1]['start']
            
        all_airings.extend(daily_airings)

    # 5. Final Sort and Cleanup (for cross-day airings)
    all_airings.sort(key=lambda x: x['start'])
    
    final_airings = []
    # Re-enforce duration link across days
    for i in range(len(all_airings)):
        current_airing = all_airings[i]
        
        if i + 1 < len(all_airings):
            # Final check to link stop time to next start time
            current_airing['stop'] = all_airings[i+1]['start']
                
        # Only include programs with positive duration
        if current_airing['stop'] > current_airing['start']:
            final_airings.append(current_airing)

    return final_airings


#
# >>>>> XML GENERATION FUNCTION (Reused from previous scripts) <<<<<
#
def generate_xmltv(all_programs, channel_infos):
    """Creates the epg.xml file in XMLTV format, including channel logos."""
    
    print(f"\n--- Generating XML File ---")
    tv_root = ET.Element("tv")

    # 1. Add <channel> definitions for all channels
    for info in channel_infos:
        channel_elem = ET.SubElement(tv_root, "channel", {"id": info['xmltv_id']})
        
        display_name = ET.SubElement(channel_elem, "display-name")
        display_name.text = info['display_name']

        if info.get('logo_url'):
             icon_elem = ET.SubElement(channel_elem, "icon", {"src": info['logo_url']})


    # 2. Add <programme> data
    if not all_programs:
        print("WARNING: No program data was found.")
    
    all_programs.sort(key=lambda x: x['start'])

    for prog in all_programs:
        start_time_str = prog['start'].strftime('%Y%m%d%H%M%S ') + prog['start'].strftime('%z')
        stop_time_str = prog['stop'].strftime('%Y%m%d%H%M%S ') + prog['stop'].strftime('%z')
        
        prog_elem = ET.SubElement(tv_root, "programme", {
            "start": start_time_str,
            "stop": stop_time_str,
            "channel": prog['channel']
        })

        title_elem = ET.SubElement(prog_elem, "title", {"lang": "en"})
        title_elem.text = prog['title']

        if prog.get('subtitle'):
            sub_elem = ET.SubElement(prog_elem, "sub-title", {"lang": "en"})
            sub_elem.text = prog['subtitle']
            
        if prog.get('desc'):
            desc_elem = ET.SubElement(prog_elem, "desc", {"lang": "en"})
            desc_elem.text = prog['desc']

    xml_string = ET.tostring(tv_root, encoding='utf-8').decode('utf8')
    formatted_xml = '<?xml version="1.0" encoding="utf-8"?>\n' + xml_string.replace('><', '>\n<')

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
                print(f"-> Scraped {len(programs)} airings for {channel['display_name']}.")
            except Exception as e:
                print(f"!!! CRITICAL ERROR scraping {channel['display_name']}: {e}")
        else:
            print(f"!!! WARNING: No scraper function found for {channel['display_name']}.")

    try:
        generate_xmltv(all_programs, CHANNELS)
    except Exception as e:
        print(f"!!! FAILED to generate XML file at the end of execution: {e}")