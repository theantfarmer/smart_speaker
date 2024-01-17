import re
import os
import json
import spacy
import requests
import ephem
from datetime import datetime
import holidays
from fuzzywuzzy import process
from phrases import PHRASES
from dont_tell import HOME_ASSISTANT_TOKEN
from db_operations import save_conversation
from transit_routes import fetch_subway_status, train_status_phrase
from home_assistant_interactions import is_home_assistant_available, home_assistant_request


nlp = spacy.load("en_core_web_sm")

def load_commands():
    with open('command_list.json', 'r') as file:
        command_list = json.load(file)
        commands = {}
        for command_dict in command_list:
            if len(command_dict) == 1:
                # Single key-value pair, add directly
                key, value = next(iter(command_dict.items()))
                commands[key] = {'command': value}
            elif 'replacement' in command_dict:
                # Handle the replacement case
                command_key = command_dict['replacement']
                for key, value in command_dict.items():
                    if key != 'replacement':
                        commands[key] = {'command': value, 'replacement': command_key}
        return commands

commands = load_commands()
flattened_commands = {v['command'].lower(): k for k, v in commands.items()}

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

def smart_home_parse_and_execute(command_text, testing_mode=False):
    print(f"Command received: {command_text}")
    doc = nlp(command_text)
    commands = load_commands()
    command_text_stripped = command_text.strip().lower()

    # Fuzzy matching
    flattened_commands = {v["command"].lower(): k for k, v in commands.items()}
    best_match, score = process.extractOne(command_text_stripped, flattened_commands.keys())

    if score > 85:
        command_data = commands[flattened_commands[best_match]]

        # Determine which command to use
        if "replacement" in command_data and command_data["replacement"]:
            best_match = command_data["replacement"]
        else:
            best_match = command_data["command"]
            
        if is_home_assistant_available():
            # Sending a POST request with the sentence to the conversation API
            endpoint = "conversation/process"
            payload = {"text": best_match, "language": "en"}  # Assuming English language
            response = home_assistant_request(endpoint, 'post', payload)

            if response and response.status_code == 200:
                return True, f" "
            else:
                print(f"Failed to trigger automation: {response.text if response else 'No response'}")
                return True, "Error in triggering automation in Home Assistant."
        else:
            print("Home Assistant is not available")
            return True, "Home Assistant is not available."


   
    
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