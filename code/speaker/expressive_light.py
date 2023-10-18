import re
import json
import logging
from text_to_speech_operations import talk_with_tts  # Assuming this import is correct in your original code

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

def format_for_home_assistant(command):
    try:
        if command is None:
            return None
        
        # Split the command string into values
        values = command.split(",")
        
        # Validate the number of values
        if len(values) != 4:
            logging.error(f"Invalid command format: {command}. Expected 4 values separated by commas.")
            return None

        # Convert and validate each value
        try:
            x = float(values[0])
            y = float(values[1])
            brightness = int(values[2])
            transition = float(values[3])
        except (ValueError, IndexError):
            logging.error(f"Invalid values detected: {values}. Expected float,float,int,float.")
            return None

        if not (0 <= x <= 1 and 0 <= y <= 1 and 0 <= brightness <= 254 and transition >= 0):
            logging.error(f"Invalid value ranges in the command: {values}")
            return None

        # Create the formatted command dictionary
        formatted_command = {
            "xy": [x, y],
            "brightness": brightness,
            "transition": transition
        }
        
        logging.info(f"Formatted command: {formatted_command}")
        
        # Return the formatted command as a JSON-formatted string
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
        
        if text and not text.startswith('@['):
            command_text_list.append((None, texts.pop(0).strip()))
            
        for command, txt in zip(commands, texts):
            formatted_command = format_for_home_assistant(command) if command is not None else None
            txt = txt if txt != '' else ' '
            if formatted_command is not None: 
                command_text_list.append((formatted_command, txt.strip() if txt else None))
            
        print(f"Command-text list created: {command_text_list}")

        return command_text_list
    except Exception as e:
        logging.error(f"An unexpected error occurred in create_command_text_list: {e}")
        return []

