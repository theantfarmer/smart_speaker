# THIS MODULE IS DEPRECIATED
# it is replaced by centeralized_tools.py
# but I havent transferred all the tools yet




# this is early code I had chatgpt write for me in the beginning
# it is scheduled to be scrapped and completely re-written because it is messy and confusing
# but it works
# its job is check user text for words and phrases and determine if any its APIs are relevent
# for example, if the user is looking for train status or the time,
# this is the section that will identify and send the request to the correct place
# and receieve its return
# if no matches are found, it returns the query to main.py which then sends it to a language model


import re
import os
import json
import magic
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

def smart_home_parse_and_execute(command_text_stripped,  testing_mode=False):
    if command_text_stripped is None:
        return False, ""

    print(f"Command received: {command_text_stripped}")
    doc = nlp(command_text_stripped) 
        


    command_to_execute = command_text_stripped  
    
    mta_line_status_questions = [
    "Is the [mta-line] running",
    "Is the [mta-line] train running",
    "Is the [mta-line]train running",
    "Is the [mta-line]-train running",
    "how is the [mta-line] train",
    "how is the [mta-line]train",
    "how is the [mta-line]-train",
    "how is the [mta-line] train today",
    "how is the [mta-line]train today",
    "how is the [mta-line]-train today",
    "What's the status of the [mta-line] train?",
    "Can you check if the [mta-line] is on schedule?",
    "Is there any delay on the [mta-line] line?",
    "How's the [mta-line] line doing?",
    "Are there any issues with the [mta-line] today?",
    "Is the [mta-line] operating normally?",
    "What's up with the [mta-line] line?",
    "Is the [mta-line] delayed?",
    "Any service changes for the [mta-line]?",
    "Is the [mta-line] running on time?",
    "Status of the [mta-line]?",
    "[mta-line] train status?",
    "Is the [mta-line] running today?",
    "Are there any alerts for the [mta-line]?"
            ]
    if "mta" in command_to_execute or ("train" in command_text_stripped.lower() and ("status" in command_text_stripped.lower() or "running" in command_text_stripped.lower())):
        train_line_match = re.search(r'\b([A-Z0-9])(?:[ -]?train)?\b', command_text_stripped, re.IGNORECASE)

        if train_line_match:
            train_line = train_line_match.group(1).upper()
            status = fetch_subway_status(train_line)
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

    time_triggers = [
    "time",
    "what time is it?",
    "what time is it now",
    "can you tell me what time it is",
    "what is the time",
    "whats the time"
    ]
    if any(trigger.lower() in command_text_stripped.lower() for trigger in time_triggers):
        current_time = datetime.now().strftime('%I:%M %p')
        return True, f"It's {current_time}"
        
    date_triggers = [
    "date",
    "what's the date today",
    "what is the date today",
    "can you tell me the date",
    "tell me the date",
    "what day is it today",
    "day",
    "what's today",
    "what day is it"
    ]
    if any(trigger.lower() in command_text_stripped.lower() for trigger in date_triggers):
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