import re
import logging
import json
import logging
from text_to_speech_operations import talk_with_tts
from smart_home_parser import get_entity_state

# Initialize logging
logging.basicConfig(level=logging.INFO)

def find_lighting_commands(text):
    """Find lighting commands in the text."""
    try:
        if not isinstance(text, str):
            logging.warning("Text is not a string. Returning an empty list.")
            return []
        pattern = r'@\[(.*?)\]@'
        commands = re.findall(pattern, text)
        logging.info(f"Commands found: {commands}")
        return commands
    except Exception as e:
        logging.error(f"An unexpected error occurred in find_lighting_commands: {e}")
        return []

def split_text_by_commands(text):
    """Split the text by lighting commands."""
    try:
        if text is None:
            return []
        texts = re.split(r'@\[.*?\]@', text)
        return texts
    except Exception as e:
        logging.error(f"An unexpected error occurred in split_text_by_commands: {e}")
        return []

import json
import logging

def validate_and_convert(values):
    try:
        x = float(values[0])
        y = float(values[1])
        brightness = int(values[2])
        transition = int(float(values[3]))  # Convert float to int
        return x, y, brightness, transition
    except (ValueError, IndexError):
        logging.error(f"Invalid values detected: {values}. Expected float,float,int,float.")
        return None



def format_for_home_assistant(command, include_only=None):
    try:
        if command is None:
            return None

        values = command.split(",")
        
        if len(values) != 4:
            logging.error(f"Invalid command format: {command}. Expected 4 values separated by commas.")
            return None

        try:
            x = float(values[0])
            y = float(values[1])
            brightness = int(values[2])
            transition = int(float(values[3]))  # Convert float to int
        except (ValueError, IndexError):
            logging.error(f"Invalid values detected: {values}. Expected float,float,int,float.")
            return None

        if not (-10 <= x <= 10 and -10 <= y <= 10 and 0 <= brightness <= 254 and transition >= 0):
            logging.error(f"Invalid value ranges in the command: {values}")
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

        logging.info(f"Formatted command: {formatted_command}")

        return json.dumps(formatted_command)
    except Exception as e:
        logging.error(f"An unexpected error occurred in format_for_home_assistant: {e}")
        return None


def create_command_text_list(text):
    try:
        print("Inside create_command_text_list")
        print(f"Text received: {text}")
        
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

        print(f"Command-text list created: {command_text_list}")

        return command_text_list
    except Exception as e:
        logging.error(f"An unexpected error occurred in create_command_text_list: {e}")
        return []
