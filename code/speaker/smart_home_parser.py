import re
import spacy
import requests
import ephem
from datetime import datetime
import holidays
from phrases import PHRASES
from dont_tell import HOME_ASSISTANT_TOKEN
from db_operations import save_conversation
from transit_routes import fetch_subway_status, train_status_phrase

nlp = spacy.load("en_core_web_sm")
HOME_ASSISTANT_URL = 'http://homeassistant.local:8123/api/'
HEADERS = {'Authorization': f'Bearer {HOME_ASSISTANT_TOKEN}', 'content-type': 'application/json'}

def get_date(date_text):
    try:
        return datetime.strptime(date_text, '%m/%d')
    except ValueError:
        return get_holiday_date(date_text)

def get_holiday(date):
    us_holidays = holidays.US()
    return us_holidays.get(date)

def get_holiday_date(holiday_name):
    us_holidays = holidays.US(years=datetime.now().year)
    for date, name in us_holidays.items():
        if holiday_name.lower() in name.lower():
            return date
    return None

def get_next_holiday():
    us_holidays = holidays.US(years=datetime.now().year)
    for date, name in sorted(us_holidays.items()):
        if date > datetime.now().date():
            return date, name
    return None, None

def get_moon_phase():
    moon_phase_num = ephem.Moon(datetime.now()).phase
    if 0 <= moon_phase_num < 7.4:
        return "New Moon"
    elif 7.4 <= moon_phase_num < 14.8:
        return "First Quarter"
    elif 14.8 <= moon_phase_num < 22.1:
        return "Full Moon"
    else:
        return "Last Quarter"

def is_home_assistant_available():
    try:
        response = requests.get(f'{HOME_ASSISTANT_URL}states', headers=HEADERS)
        return True if response.status_code == 200 else False
    except requests.RequestException:
        return False

def home_assistant_request(endpoint, method, payload=None):
    url = f'{HOME_ASSISTANT_URL}{endpoint}'
    print(f"Sending request to URL: {url}, with payload: {payload}")  # Debug line
    print(f"Using headers: {HEADERS}")  # Debug line
    try:
        if method == 'get':
            response = requests.get(url, headers=HEADERS, timeout=10)
        elif method == 'post':
            print(f"About to send payload: {payload}")  # Debug line
            response = requests.post(url, headers=HEADERS, json=payload, timeout=10)

        
        response.raise_for_status()
        
        # Additional debug lines for response
        print(f"Response received: {response.text}")
        print(f"Response status code: {response.status_code}")
        
        return response
    except (requests.RequestException, ValueError) as e:
        print(f"Exception occurred: {e}")  # Debug line
        return None



def smart_home_parse_and_execute(command_text):
    print(f"Command received: {command_text}")
    doc = nlp(command_text)
    command_text_stripped = command_text.strip().lower()
    response = home_assistant_request('states', 'get')
    
    if not response:
        if "light" in command_text:
            return False, "Home Assistant is missing, dude."
    light_on_patterns = [r'\b(turn\s+on\s+the\s+light|turn\s+the\s+light\s+on|light\s+on)\b']
    light_off_patterns = [r'\b(turn\s+off\s+the\s+light|turn\s+the\s+light\s+off|light\s+off|dark)\b']
    
    if any(re.search(pattern, command_text, re.IGNORECASE) for pattern in light_on_patterns):
        response = home_assistant_request('services/light/turn_on', 'post', payload={"entity_id": "light.bedroom"})
        if response and response.status_code == 200:
            return True, "done"
        return False, "Failed to turn on light"
    elif any(re.search(pattern, command_text, re.IGNORECASE) for pattern in light_off_patterns):
        response = home_assistant_request('services/light/turn_off', 'post', payload={"entity_id": "light.bedroom"})
        if response and response.status_code == 200:
            return True, "done"
        return False, "Failed to turn off light"
    
    if "mta" in command_text.lower() or ("train" in command_text.lower() and ("status" in command_text.lower() or "running" in command_text.lower())):
        train_line_match = re.search(r'\b([A-Z0-9])\b\s*(?:train)?', command_text, re.IGNORECASE)
        if train_line_match:
            train_line = train_line_match.group(1).upper()
            status = fetch_subway_status(train_line)
            response = train_status_phrase(train_line, status)
            return True, response
    holiday_match = re.search(r"when is (\w+)", command_text, re.IGNORECASE)
    
    if holiday_match:
        holiday_name = holiday_match.group(1)
        holiday_date = get_holiday_date(holiday_name)
        if holiday_date:
            response = f"{holiday_name} is on {holiday_date.strftime('%A, %B %d, %Y')}"
            return True, response
    day_of_week_match = re.search(r"what day of the week is ((\w+)|(\d{1,2}/\d{1,2}))", command_text, re.IGNORECASE)
    if day_of_week_match:
        date_text = day_of_week_match.group(1)
        date = get_date(date_text)
        if date:
            day_of_week = date.strftime('%A')
            response = f"{date_text} is on a {day_of_week}."
            return True, response
    
    if command_text_stripped in ["time", "what time is it"]:
        current_time = datetime.now().strftime('%I:%M %p')
        return True, f"It's {current_time}"
    
    if command_text.lower().strip() in ["date", "what's the date today"]:
        date = datetime.now().strftime('%A, %d %B %Y')
        holiday_name = get_holiday(datetime.now().date())
        if holiday_name:
            date += f" - {holiday_name}"
        return True, date
    
    if re.search(r'\b(moon\s+phase)\b', command_text, re.IGNORECASE):
        moon_phase = get_moon_phase()
        response = f'The moon phase today is {moon_phase}.'
        return True, response
    
    if command_text_stripped in PHRASES:
        response = PHRASES[command_text_stripped]
        return True, response
    
    return False, "Query not handled by smart home commands, falling back to GPT."
