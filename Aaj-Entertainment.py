#!/usr/bin/env python3
"""
Aaj Entertainment EPG Generator
Scrapes schedule from aajentertainment.tv and generates XMLTV format EPG
"""

import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date, time
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
try:
    from zoneinfo import ZoneInfo
    _EPG_TZ = ZoneInfo('Asia/Karachi')  # Pakistan Standard Time (UTC+5)
except Exception:
    _EPG_TZ = None  # Fallback when zoneinfo/tzdata is unavailable

def get_schedule_html():
    """Fetch the schedule HTML from Aaj Entertainment website"""
    url = "https://www.aajentertainment.tv"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching website: {e}")
        return None

def parse_schedule(html_content):
    """Parse the schedule from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all day tables
    day_tables = soup.find_all('table', class_='w-full')
    
    schedule_data = {}
    
    for table in day_tables:
        # Get day name from thead
        day_header = table.find('h2', class_='bg-orange-900 uppercase text-white text-3.5 p-2 text-center font-bold')
        if not day_header:
            continue
            
        day_name = day_header.get_text(strip=True)
        
        # Get all program rows
        program_rows = table.find_all('tr', class_='flex flex-row w-full')
        
        programs = []
        for row in program_rows:
            time_div = row.find('div', class_='text-sm text-white')
            if not time_div:
                continue
                
            # Get time and program name
            time_text = time_div.get_text(strip=True)
            
            # Find the program name div (second div with same class)
            all_divs = row.find_all('div', class_='text-sm text-white')
            if len(all_divs) >= 2:
                program_name = all_divs[1].get_text(strip=True)
            else:
                continue
            
            programs.append({
                'time': time_text,
                'name': program_name
            })
        
        schedule_data[day_name] = programs
    
    return schedule_data

def create_xmltv_schedule(schedule_data):
    """Create XMLTV format schedule with proper timezone and chronological order"""
    # Create root element
    tv = ET.Element('tv')
    
    # Add channel information
    channel = ET.SubElement(tv, 'channel')
    channel.set('id', 'Aaj.Entertainment.pk')
    
    display_name = ET.SubElement(channel, 'display-name')
    display_name.set('lang', 'en')
    display_name.text = 'Aaj Entertainment'
    
    icon = ET.SubElement(channel, 'icon')
    icon.set('src', 'https://thefilmtuition.com/tvlogo/Aaj-Entertainment.png')
    
    # Get current date/time in EPG timezone
    now = datetime.now(_EPG_TZ) if _EPG_TZ else datetime.now()
    
    # Map day names to weekday numbers (Monday=0, Sunday=6)
    day_to_weekday = {
        'Monday': 0,
        'Tuesday': 1,
        'Wednesday': 2,
        'Thursday': 3,
        'Friday': 4,
        'Saturday': 5,
        'Sunday': 6
    }
    
    # Calculate the date for each day based on current date in target timezone
    current_weekday = now.weekday()  # Monday=0, Sunday=6

    # Helper to map a weekday name to the next occurrence (including today)
    def next_date_for_weekday(day_name: str) -> date:
        if day_name not in day_to_weekday:
            return now.date()
        target_weekday = day_to_weekday[day_name]
        days_diff = (target_weekday - current_weekday) % 7
        return (now + timedelta(days=days_diff)).date()

    # Helper to format datetime with timezone offset
    def format_xmltv_dt(dt_obj: datetime) -> str:
        if _EPG_TZ:
            return dt_obj.strftime('%Y%m%d%H%M%S %z')
        # Fallback to PST offset when timezone isn't available
        return dt_obj.strftime('%Y%m%d%H%M%S') + ' +0500'

    # Accumulate all programme entries to sort chronologically
    programme_entries = []
    
    # Add programs for each day (mapped to the next occurrence of that weekday)
    for day_name, programs in schedule_data.items():
        if day_name not in day_to_weekday:
            continue

        # Determine the calendar date for this weekday
        day_date_obj = next_date_for_weekday(day_name)

        # Process each program
        for i, program in enumerate(programs):
            # Parse start time
            start_t = parse_time(program['time'])
            if start_t is None:
                continue

            # Build timezone-aware datetimes
            start_dt = datetime(
                day_date_obj.year,
                day_date_obj.month,
                day_date_obj.day,
                start_t.hour,
                start_t.minute,
                0,
                0,
                tzinfo=_EPG_TZ
            ) if _EPG_TZ else datetime(
                day_date_obj.year,
                day_date_obj.month,
                day_date_obj.day,
                start_t.hour,
                start_t.minute,
                0,
                0
            )

            # Calculate end time (start of next program or reasonable default)
            if i < len(programs) - 1:
                next_t = parse_time(programs[i + 1]['time'])
                if next_t:
                    end_dt = datetime(
                        day_date_obj.year,
                        day_date_obj.month,
                        day_date_obj.day,
                        next_t.hour,
                        next_t.minute,
                        0,
                        0,
                        tzinfo=_EPG_TZ
                    ) if _EPG_TZ else datetime(
                        day_date_obj.year,
                        day_date_obj.month,
                        day_date_obj.day,
                        next_t.hour,
                        next_t.minute,
                        0,
                        0
                    )
                else:
                    end_dt = start_dt + timedelta(hours=1)
            else:
                end_dt = start_dt + timedelta(hours=2)

            # Extract episode and season information for description
            description = extract_episode_season_info(program['name'])

            # Accumulate entry for later chronological sorting
            programme_entries.append({
                'start_dt': start_dt,
                'end_dt': end_dt,
                'title': program['name'],
                'desc': description
            })

    # Sort all entries by start datetime, ascending
    programme_entries.sort(key=lambda e: e['start_dt'])

    # Emit programme elements in chronological order
    for entry in programme_entries:
        programme = ET.SubElement(tv, 'programme')
        programme.set('channel', 'Aaj.Entertainment.pk')
        programme.set('start', format_xmltv_dt(entry['start_dt']))
        programme.set('stop', format_xmltv_dt(entry['end_dt']))

        title_el = ET.SubElement(programme, 'title')
        title_el.set('lang', 'en')
        title_el.text = entry['title']

        desc_el = ET.SubElement(programme, 'desc')
        desc_el.set('lang', 'en')
        desc_el.text = entry['desc']
    
    return tv

def parse_time(time_str):
    """Parse time string to datetime.time object"""
    try:
        # Handle format like "00:00", "01:00", "02:30", etc.
        if ':' in time_str:
            hour, minute = map(int, time_str.split(':'))
            return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
        else:
            # Try to parse as HHMM format
            if len(time_str) == 4:
                hour = int(time_str[:2])
                minute = int(time_str[2:])
                return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
            elif len(time_str) == 3:
                hour = int(time_str[0])
                minute = int(time_str[1:])
                return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
    except (ValueError, IndexError):
        print(f"Could not parse time: {time_str}")
        return None

def extract_episode_season_info(program_name):
    """Extract episode and season information from program name"""
    description_lines = []
    
    # Look for Episode information (Ep # X, Ep # XX, etc.)
    episode_pattern = r'Ep\s*#\s*(\d+)'
    episode_match = re.search(episode_pattern, program_name, re.IGNORECASE)
    if episode_match:
        episode_number = episode_match.group(1)
        description_lines.append(f"Episode No: {episode_number}")
    
    # Look for Season information (S-X, S-XX, etc.)
    season_pattern = r'S-\s*(\d+)'
    season_match = re.search(season_pattern, program_name, re.IGNORECASE)
    if season_match:
        season_number = season_match.group(1)
        description_lines.append(f"Season: {season_number}")
    
    # If no episode/season info found, return original name as description
    if not description_lines:
        return program_name
    
    # Join description lines with newlines
    return '\n'.join(description_lines)

def clean_program_title(program_name):
    """Clean program title by removing episode/season info from display"""
    # Remove episode info (Ep # X)
    cleaned = re.sub(r'\s*Ep\s*#\s*\d+', '', program_name, flags=re.IGNORECASE)
    
    # Remove season info (S-X)
    cleaned = re.sub(r'\s*S-\s*\d+', '', cleaned, flags=re.IGNORECASE)
    
    # Remove extra whitespace and trailing characters
    cleaned = re.sub(r'\s*-?\s*$', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def prettify_xml(elem):
    """Return a pretty-printed XML string for the Element"""
    rough_string = ET.tostring(elem, 'unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def main():
    """Main function"""
    print("Fetching Aaj Entertainment schedule...")
    
    # Get HTML content
    html_content = get_schedule_html()
    if not html_content:
        print("Failed to fetch website content")
        return
    
    print("Parsing schedule...")
    # Parse schedule
    schedule_data = parse_schedule(html_content)
    
    if not schedule_data:
        print("No schedule data found")
        return
    
    print(f"Found schedule for {len(schedule_data)} days")
    
    # Create XMLTV format
    print("Creating XMLTV format...")
    xmltv_root = create_xmltv_schedule(schedule_data)
    
    # Generate pretty XML
    xml_content = prettify_xml(xmltv_root)
    
    # Save to files in both folders
    out_channels = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channels", "Aaj-Entertainment.xml")
    out_pkchannels = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pkchannels", "Aaj-Entertainment.xml")
    os.makedirs(os.path.dirname(out_channels), exist_ok=True)
    os.makedirs(os.path.dirname(out_pkchannels), exist_ok=True)
    with open(out_channels, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    with open(out_pkchannels, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    
    print(f"EPG saved to {out_channels}")
    print(f"EPG saved to {out_pkchannels}")
    print(f"Total programs: {len(xmltv_root.findall('.//programme'))}")

if __name__ == "__main__":
    main()