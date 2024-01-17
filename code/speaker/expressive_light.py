import re
import logging
import json
from text_to_speech_operations import talk_with_tts
# from home_assistant_interactions import get_entity_state

# Initialize logging
logging.basicConfig(level=logging.INFO)

# def get_current_light_state():
#     # Fetch the current state of the light
#     response = home_assistant_request('states/light.your_hue_light', 'get')
#     if response and response.status_code == 200:
#         state_data = response.json()
#         attributes = state_data.get("attributes", {})
#         return {
#             "is_on": state_data.get("state") == "on",
#             "scene": attributes.get("scene"),
#             "brightness": attributes.get("brightness"),
#             "color_temp": attributes.get("color_temp")
#         }
#     else:
#         return None


def find_lighting_commands(text):
    """Find lighting commands in the text."""
    try:
        if not isinstance(text, str):
            logging.warning("Text is not a string. Returning an empty list.")
            return []
        pattern = r'@\[(.*?)\]@'
        commands = re.findall(pattern, text)
        logging.info("Commands found: %s", commands)
        return commands
    except Exception as e:
        logging.error("An unexpected error occurred in find_lighting_commands: %s", e)
        return []

def split_text_by_commands(text):
    """Split the text by lighting commands."""
    try:
        if text is None:
            return []
        texts = re.split(r'@\[.*?\]@', text)
        return texts
    except Exception as e:
        logging.error("An unexpected error occurred in split_text_by_commands: %s", e)
        return []

def validate_and_convert(values):
    """Validate and convert the values."""
    try:
        x = float(values[0])
        y = float(values[1])
        brightness = int(values[2])
        transition = int(float(values[3]))  # Convert float to int
        return x, y, brightness, transition
    except (ValueError, IndexError):
        logging.error("Invalid values detected: %s. Expected float,float,int,float.", values)
        return None

def format_for_home_assistant(command, include_only=None):
    """Format the command for Home Assistant."""
    try:
        if command is None:
            return None

        values = command.split(",")
        
        if len(values) != 4:
            logging.error("Invalid command format: %s. Expected 4 values separated by commas.", command)
            return None

        try:
            x = float(values[0])
            y = float(values[1])
            brightness = int(values[2])
            transition = int(float(values[3]))  # Convert float to int
        except (ValueError, IndexError):
            logging.error("Invalid values detected: %s. Expected float,float,int,float.", values)
            return None

        if not (-10 <= x <= 10 and -10 <= y <= 10 and 0 <= brightness <= 254 and transition >= 0):
            logging.error("Invalid value ranges in the command: %s", values)
            return None

        formatted_command = {
            "entity_id": "light.bedroom"  # Add the entity ID
        }
        
        if include_only is None or 'xy' in include_only:
            formatted_command['xy_color'] = [x, y]

        if include_only is None or 'brightness' in include_only:
            formatted_command['brightness'] = brightness

        if include_only is None or 'transition' in include_only:
            formatted_command['transition'] = transition

        logging.info("Formatted command: %s", formatted_command)

        return json.dumps(formatted_command)
    except Exception as e:
        logging.error("An unexpected error occurred in format_for_home_assistant: %s", e)
        return None

def create_command_text_list(text):
    """Create a list of command texts."""
    try:
        print("Inside create_command_text_list")
        print("Text received: %s", text)
        
        commands = find_lighting_commands(text) if text is not None else []
        texts = split_text_by_commands(text) if text is not None else []
        command_text_list = []

        # Iterate through the texts and commands simultaneously
        for i, (command, txt) in enumerate(zip(commands, texts)):
            formatted_command = format_for_home_assistant(command) if command is not None else None
            
            # If it's not the first text segment and the previous text doesn't end with a full stop,
            # append ellipses to indicate continuation
            if i > 0 and not texts[i-1].strip().endswith('.'):
                txt = '...' + txt

            txt = txt if txt != '' else ' '
            if formatted_command is not None: 
                command_text_list.append((formatted_command, txt.strip() if txt else None))

        if texts and len(texts) > len(commands):
            # Handle any remaining text after the last command
            last_text = texts[-1].strip()
            if last_text:
                command_text_list.append((None, '…' + last_text if not last_text.endswith('.') else last_text))

        print("Command-text list created: %s", command_text_list)

        return command_text_list
    except Exception as e:
        logging.error("An unexpected error occurred in create_command_text_list: %s", e)
        return []