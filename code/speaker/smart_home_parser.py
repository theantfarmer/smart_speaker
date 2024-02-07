import re
import os
import json
import magic
import magic
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
from home_assistant_interactions import is_home_assistant_available, home_assistant_request, load_commands, flattened_commands, execute_command_in_home_assistant 


nlp = spacy.load("en_core_web_sm")



           

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

def smart_home_parse_and_execute(command_text_stripped, raw_commands_dict, testing_mode=False):
    if command_text_stripped is None:
        return False, ""

    print(f"Command received: {command_text_stripped}")
    doc = nlp(command_text_stripped) 
    # print(f"raw commands: {raw_commands_dict}")
    
    # Fuzzy matching
        
    # Assuming 'command_text_stripped' is the user's input
    command_to_execute, score = process.extractOne(command_text_stripped, flattened_commands)
    print(f"Fuzzy match: {command_to_execute} with score {score}")
    if score > 90:
        command_matched = None
        for command_dict in raw_commands_dict:
            if command_to_execute in command_dict.values():
                command_matched = command_dict
                break
        
        if command_matched:
            # New logic to refine the matched command
            if "replacement" in command_matched and command_matched["replacement"]:
                command_to_execute = command_matched["replacement"]
            else:
                # Assuming the default command key is "command" which might need to be adjusted
                command_to_execute = command_matched.get("command", command_to_execute)
    
            execute_command_in_home_assistant(command_to_execute)
            print(f"Executing refined command: {command_to_execute}")
            return {"executed": True, "boink": command_to_execute}
        else:
            print("No matching command found.")
            return {"executed": False, "message": "No matching command found"}
  
    
    if "mta" in command_to_execute or ("train" in command_text_stripped.lower() and ("status" in command_text_stripped.lower() or "running" in command_text_stripped.lower())):
        train_line_match = re.search(r'\b([A-Z0-9])\b\s*(?:train)?', command_text_stripped, re.IGNORECASE)
        if train_line_match:
            train_line = train_line_match.group(1).upper()
            # Assuming fetch_subway_status is a function you've defined elsewhere
            status = fetch_subway_status(train_line)
            # Assuming train_status_phrase is a function you've defined elsewhere
            response = train_status_phrase(train_line, status)
            return True, response


                
    holiday_match = re.search(r"when is (\w+)", command_text_stripped, re.IGNORECASE)

    if holiday_match:
        holiday_name = holiday_match.group(1)
        holiday_date = get_holiday_date(holiday_name)
        if holiday_date:
            response = f"{holiday_name} is on {holiday_date.strftime('%A, %B %d, %Y')}"
            return True, response
                
    day_of_week_match = re.search(r"what day of the week is ((\w+)|(\d{1,2}/\d{1,2}))", command_text_stripped, re.IGNORECASE)
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
    
    if command_text_stripped in ["date", "what's the date today"]:
        date = datetime.now().strftime('%A, %d %B %Y')
        holiday_name = get_holiday(datetime.now().date())
        if holiday_name:
            date += f" - {holiday_name}"
        return True, date
    
    if re.search(r'\b(moon\s+phase)\b', command_text_stripped, re.IGNORECASE):
        moon_phase = get_moon_phase()
        response = f'The moon phase today is {moon_phase}.'
        return True, response
    
    if command_text_stripped in PHRASES:
        response = PHRASES[command_text_stripped]
        return True, response
    
    return False, "Query not handled by smart home commands, falling back to GPT."