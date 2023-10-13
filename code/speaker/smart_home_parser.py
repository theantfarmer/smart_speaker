import re 
import spacy
import requests
from dont_tell import HOME_ASSISTANT_TOKEN, MTA_API_KEY  # Importing the tokens from gpt_key.py
from db_operations import initialize_db, save_conversation  # Assuming these imports are correct
from text_to_speech_operations import talk_with_tts  # Assuming these imports are correct
from speech_to_text_operations import capture_speech  # Assuming these imports are correct
from gpt_operations import handle_conversation  # Assuming these imports are correct
from transit_routes import fetch_subway_status

nlp = spacy.load("en_core_web_sm")

def smart_home_parse_and_execute(command_text):
    print(f"Command received: {command_text}")  # Print the command text received
    doc = nlp(command_text)
    print(f"Spacy Doc: {doc}")  # Print the spacy doc object

    HOME_ASSISTANT_URL = 'http://localhost:8123/api/'
    HEADERS = {
        'Authorization': f'Bearer {HOME_ASSISTANT_TOKEN}',
        'content-type': 'application/json',
    }

    try:
        response = requests.get(f'{HOME_ASSISTANT_URL}states', headers=HEADERS)
        print(f"Response from states API: {response.text}")  # Print the response from the states API
    except requests.RequestException as e:
        print(f"Failed to fetch states from Home Assistant: {e}")  # Print error if unable to fetch states

    # Define regex patterns for light control commands
    light_on_patterns = [r'\b(turn\s+on\s+the\s+light|turn\s+the\s+light\s+on|light\s+on)\b']
    light_off_patterns = [r'\b(turn\s+off\s+the\s+light|turn\s+the\s+light\s+off|light\s+off|dark)\b']

    # Check if any of the light on patterns match the command text
    if any(re.search(pattern, command_text, re.IGNORECASE) for pattern in light_on_patterns):
        payload = {"entity_id": "light.school_show"}  # Use correct entity_id
        try:
            response = requests.post(
                f'{HOME_ASSISTANT_URL}services/light/turn_on',
                headers=HEADERS,
                json=payload  # Include payload in the request
            )
            print(f"Response from turn on light API: {response.text}")  # Print the response from the turn on light API
            if response.status_code == 200:
                print("Light turned on.")
                return True, "Light turned on."  # return a tuple
        except requests.RequestException as e:
            print(f"Failed to turn on light: {e}")  # Print error if unable to turn on light
            return False, f"Failed to turn on light: {e}"  # return a tuple

    # Check if any of the light off patterns match the command text
    elif any(re.search(pattern, command_text, re.IGNORECASE) for pattern in light_off_patterns):
        payload = {"entity_id": "light.school_show"}  # Use correct entity_id
        try:
            response = requests.post(
                f'{HOME_ASSISTANT_URL}services/light/turn_off',
                headers=HEADERS,
                json=payload  # Include payload in the request
            )
            print(f"Response from turn off light API: {response.text}")  # Print the response from the turn off light API
            if response.status_code == 200:
                print("Light turned off.")
                return True, "Light turned off."  # return a tuple
        except requests.RequestException as e:
            print(f"Failed to turn off light: {e}")  # Print error if unable to turn off light
            return False, f"Failed to turn off light: {e}"  # return a tuple

    if "mta" in command_text.lower() or ("train" in command_text.lower() and ("status" in command_text.lower() or "running" in command_text.lower())):
        train_line_match = re.search(r'\b([A-Z0-9])\b\s*(?:train)?', command_text, re.IGNORECASE)
        if train_line_match:
            train_line = train_line_match.group(1).upper()  # Updated this line to correctly extract the train line
            status = fetch_subway_status(train_line)
            response = f'"The {train_line}" Trains Status is: {status}'
            print(response)
            return True, response  # return True to indicate a command was executed, and the response

    print("No smart home command identified.")  # Print message if no smart home command is identified
    return False, None  # return False to indicate no command was executed, and None for the response
