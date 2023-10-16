from datetime import datetime, timedelta
import requests
import json
import sqlite3
sys.path.append('../speaker')
from dont_tell import OPEN_WEATHER_MAP_API_KEY 

# Fetch solar events for the given day
def fetch_solar_events(date):
    latitude = 40.6862
    longitude = -73.9373
    url = f"https://api.sunrise-sunset.org/json?lat={latitude}&lng={longitude}&date={date}&formatted=0"
    response = requests.get(url)
    data = json.loads(response.text)
    return data['results']

# Convert time to seconds from midnight
def time_to_seconds(time_str):
    t = datetime.fromisoformat(time_str).time()
    return t.hour*3600 + t.minute*60 + t.second

# Calculate the time when a specific percentage of a quadrant has passed
def calc_time(start_seconds, end_seconds, percentage):
    return start_seconds + ((end_seconds - start_seconds) * (percentage / 100))

# Get tomorrow's date
date_tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
tomorrow_str = date_tomorrow

# Fetch solar events
solar_data = fetch_solar_events(date_tomorrow)

# Convert times to seconds from midnight
sunrise_seconds = time_to_seconds(solar_data['sunrise'])
sunset_seconds = time_to_seconds(solar_data['sunset'])
solar_noon_seconds = time_to_seconds(solar_data['solar_noon'])
# Add more solar events here ...

# Define quadrants
quadrants = {
    'Quadrant 1': (0, sunrise_seconds),
    'Quadrant 2': (sunrise_seconds, solar_noon_seconds),
    'Quadrant 3': (solar_noon_seconds, sunset_seconds),
    'Quadrant 4': (sunset_seconds, 86400)  # 86400 seconds in a day
}

# Define percentages
percentages = [19.59, 39.56, 59.52, 79.49, 99.46, 13.92, 28.22, 42.53, 56.83, 71.14, 85.44, 99.75, 14.08, 28.41, 42.75, 57.08, 71.42, 85.75]

# Calculate times for each percentage in each quadrant
schedule = {}
for q_name, (start, end) in quadrants.items():
    schedule[q_name] = {}
    for percentage in percentages:
        time_at_percentage = calc_time(start, end, percentage)
        schedule[q_name][f"{percentage}%"] = time_at_percentage

# SQLite DB Setup
sqlite_file_name = f"lighting_schedule_{tomorrow_str}.db"
conn = sqlite3.connect(sqlite_file_name)
c = conn.cursor()
table_name = f"schedule_{tomorrow_str.replace('-', '_')}"
c.execute(f'''CREATE TABLE IF NOT EXISTS {table_name}
             (event_or_percentage TEXT, seconds_after_midnite TEXT)''')


# Insert the solar events
c.execute(f"INSERT INTO {table_name} VALUES (?, ?)", ("Sunrise", sunrise_seconds))
c.execute(f"INSERT INTO {table_name} VALUES (?, ?)", ("Sunset", sunset_seconds))
c.execute(f"INSERT INTO {table_name} VALUES (?, ?)", ("Solar Noon", solar_noon_seconds))
# Add more solar events here ...

# Insert the calculated percentages
for q_name, times in schedule.items():
    for percentage, time in times.items():
        c.execute(f"INSERT INTO {table_name} VALUES (?, ?)", (f"{q_name}: {percentage}", time))

conn.commit()
conn.close()

print(f"Schedule for {tomorrow_str} has been saved.")