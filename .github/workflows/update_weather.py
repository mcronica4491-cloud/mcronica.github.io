import requests
import json
import datetime as dt
from datetime import datetime
import re

# --- Configuration ---
# API Endpoint URL (The one you provided)
API_URL = "https://api.open-meteo.com/v1/forecast?latitude=42.3584&longitude=-71.0598&hourly=temperature_2m,precipitation_probability,weather_code,wind_speed_10m&forecast_days=1&wind_speed_unit=mph&temperature_unit=fahrenheit&precipitation_unit=inch&timezone=America%2FNew_York"
README_FILE = "README.md"
START_TAG = ""
END_TAG = ""
CITY_NAME = "Boston, MA"

# --- Weather Code Mapping (Simplified based on WMO codes) ---
# Source: https://www.nodc.noaa.gov/archive/arc0021/0002199/1.1/data/0-data/HTML/WMO-CODE/WMO4677.HTM
# We only need icons for the most common current conditions.
WEATHER_MAP = {
    0: {"phrase": "Clear Sky", "icon_svg_color": "#FF8700", "svg_path": "M144 0v48M144 240v48M0 144h48M211.872 76.128l33.936-33.936M245.808 245.808l-33.936-33.936M76.128 76.128 42.192 42.192M76.128 211.872l-33.936 33.936M240 144h48"}, # Sun
    1: {"phrase": "Mostly Clear", "icon_svg_color": "#FF8700", "svg_path": "M144 0v48M144 240v48M0 144h48M211.872 76.128l33.936-33.936M245.808 245.808l-33.936-33.936M76.128 76.128 42.192 42.192M76.128 211.872l-33.936 33.936M240 144h48"}, # Sun
    2: {"phrase": "Partly Cloudy", "icon_svg_color": "#A9A9A9", "svg_path": "M144 144l-45 0 0 -45 45 0 0 45ZM144 144l-45 0 0 -45 45 0 0 45Z M189 144c0 24.853-20.147 45-45 45s-45-20.147-45-45c0-24.853 20.147-45 45-45s45 20.147 45 45ZM189 144"}, # Cloud
    3: {"phrase": "Overcast", "icon_svg_color": "#808080", "svg_path": "M144 144l-45 0 0 -45 45 0 0 45ZM144 144l-45 0 0 -45 45 0 0 45Z M189 144c0 24.853-20.147 45-45 45s-45-20.147-45-45c0-24.853 20.147-45 45-45s45 20.147 45 45ZM189 144"}, # Cloud
    45: {"phrase": "Fog", "icon_svg_color": "#808080", "svg_path": "M144 144l-45 0 0 -45 45 0 0 45ZM144 144l-45 0 0 -45 45 0 0 45Z M189 144c0 24.853-20.147 45-45 45s-45-20.147-45-45c0-24.853 20.147-45 45-45s45 20.147 45 45ZM189 144"}, # Cloud
    51: {"phrase": "Light Drizzle", "icon_svg_color": "#5379AE", "svg_path": "M144 144l-45 0 0 -45 45 0 0 45ZM144 144l-45 0 0 -45 45 0 0 45Z M189 144c0 24.853-20.147 45-45 45s-45-20.147-45-45c0-24.853 20.147-45 45-45s45 20.147 45 45ZM189 144 M144 240v20M124 240v20M164 240v20"}, # Cloud/Rain
    61: {"phrase": "Moderate Rain", "icon_svg_color": "#5379AE", "svg_path": "M144 144l-45 0 0 -45 45 0 0 45ZM144 144l-45 0 0 -45 45 0 0 45Z M189 144c0 24.853-20.147 45-45 45s-45-20.147-45-45c0-24.853 20.147-45 45-45s45 20.147 45 45ZM189 144 M144 240v20M124 240v20M164 240v20 M144 260v20M124 260v20M164 260v20"}, # Cloud/Heavy Rain
    71: {"phrase": "Light Snowfall", "icon_svg_color": "#FFFFFF", "svg_path": "M144 144l-45 0 0 -45 45 0 0 45ZM144 144l-45 0 0 -45 45 0 0 45Z M189 144c0 24.853-20.147 45-45 45s-45-20.147-45-45c0-24.853 20.147-45 45-45s45 20.147 45 45ZM189 144 M144 240v20M124 240v20M164 240v20 M144 260v20M124 260v20M164 260v20"}, # Cloud/Snow (re-using rain for simplicity)
    95: {"phrase": "Thunderstorm", "icon_svg_color": "#5379AE", "svg_path": "M144 144l-45 0 0 -45 45 0 0 45ZM144 144l-45 0 0 -45 45 0 0 45Z M189 144c0 24.853-20.147 45-45 45s-45-20.147-45-45c0-24.853 20.147-45 45-45s45 20.147 45 45ZM189 144 M120 220l48 0 0 20-48 0 0 -20ZM144 240v20l20 0-32 20-32 -20 20 0 0 -20"} # Cloud/Thunderstorm
}
# Default for unknown codes
DEFAULT_WEATHER = {"phrase": "Unknown", "icon_svg_color": "#333", "svg_path": "M144 144l-45 0 0 -45 45 0 0 45ZM144 144l-45 0 0 -45 45 0 0 45Z M189 144c0 24.853-20.147 45-45 45s-45-20.147-45-45c0-24.853 20.147-45 45-45s45 20.147 45 45ZM189 144"}


def fetch_weather_data():
    """Fetches weather data from the Open-Meteo API."""
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

def get_current_data(data):
    """Extracts the data for the current hour."""
    
    # 1. Determine the current index (nearest hour)
    now = datetime.now()
    # The API returns data for the start of the hour (e.g., 16:00, 17:00)
    # We find the index that matches the current hour in New York time.
    hourly_times = data['hourly']['time']
    current_hour_str = now.strftime('%Y-%m-%dT%H:00')

    try:
        current_index = hourly_times.index(current_hour_str)
    except ValueError:
        # If the exact current hour isn't found (e.g. if the action runs late/early),
        # use the first index (the start of the forecast day)
        current_index = 0
    
    # 2. Extract values for that index
    current_temp = round(data['hourly']['temperature_2m'][current_index])
    precip_prob = data['hourly']['precipitation_probability'][current_index]
    wind_speed = round(data['hourly']['wind_speed_10m'][current_index])
    weather_code = data['hourly']['weather_code'][current_index]
    
    return {
        'temp': current_temp,
        'precip_prob': precip_prob,
        'wind_speed': wind_speed,
        'code': weather_code
    }

def generate_markdown(current_data):
    """Generates the Markdown/HTML block for the README."""
    
    temp = current_data['temp']
    wind = current_data['wind_speed']
    precip = current_data['precip_prob']
    
    weather_info = WEATHER_MAP.get(current_data['code'], DEFAULT_WEATHER)
    phrase = weather_info['phrase']
    icon_color = weather_info['icon_svg_color']
    svg_path = weather_info['svg_path']
    
    # The time is static, but accurate for when the action ran.
    current_time_str = datetime.now().strftime('%I:%M %p')

    # The HTML template uses minimal styling supported by GitHub's Markdown parser
    markdown_content = f"""
<div align="center">
  
  <h2 style="font-size: 1.5em; border-bottom: 2px solid #ccc; padding-bottom: 5px;">
    Current Weather in {CITY_NAME}
  </h2>

  <div style="display: flex; align-items: center; justify-content: center; margin: 15px 0; padding: 10px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9;">
    
    <svg viewBox="0 0 288 288" width="80" height="80" style="min-width: 80px; margin-right: 20px;">
        <g stroke="{icon_color}" stroke-width="9.6" fill="none" fill-rule="evenodd">
            {svg_path}
        </g>
    </svg>
    
    <div style="text-align: left;">
      <div style="font-size: 3em; font-weight: bold; line-height: 1em;">{temp}°<span style="font-size: 0.5em; font-weight: normal;">F</span></div>
      <div style="font-size: 1em; color: #555; margin-top: 5px;">As of {current_time_str} EDT</div>
      <div style="font-size: 1.2em; font-weight: 500; margin-top: 10px; color: #1e7e34;">{phrase}</div>
    </div>
  </div>

  <div style="margin-top: 20px; padding: 10px;">
    
    <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px dashed #eee;">
      <span style="font-weight: 400; color: #555;">Wind Speed</span>
      <span style="font-weight: bold; color: #333;">{wind} mph</span>
    </div>
    
    <div style="display: flex; justify-content: space-between; padding: 5px 0;">
      <span style="font-weight: 400; color: #555;">Precipitation Chance</span>
      <span style="font-weight: bold; color: #333;">{precip}%</span>
    </div>
  </div>

</div>
"""
    return markdown_content

def update_readme(new_content):
    """Replaces the content between the start/end tags in README.md."""
    try:
        with open(README_FILE, "r") as f:
            readme_content = f.read()
    except FileNotFoundError:
        print(f"Error: {README_FILE} not found. Ensure it exists.")
        return

    # Use regex to replace content between the tags
    pattern = re.compile(f"{START_TAG}.*?{END_TAG}", re.DOTALL)
    
    # Create the full block to insert
    new_block = f"{START_TAG}\n{new_content}\n{END_TAG}"
    
    updated_content = pattern.sub(new_block, readme_content)

    if updated_content == readme_content:
        print("README content not changed (or tags were not found).")
    else:
        with open(README_FILE, "w") as f:
            f.write(updated_content)
        print("Successfully updated README.md with new weather data.")


def main():
    data = fetch_weather_data()
    if data:
        current_data = get_current_data(data)
        markdown = generate_markdown(current_data)
        update_readme(markdown)

if __name__ == "__main__":
    main()
