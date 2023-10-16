import re
import json
import sys
import logging
from text_to_speech_operations import talk_with_tts
# Initialize logging
logging.basicConfig(level=logging.INFO)

def find_lighting_commands(text):
    """Find lighting commands in the text."""
    if not isinstance(text, str):
        logging.warning("Text is not a string. Returning an empty list.")
        return []
    pattern = r'@\[(.*?)\]@'
    commands = re.findall(pattern, text)
    logging.info(f"Commands found: {commands}")
    return commands



def split_text_by_commands(text):
    """Split the text by lighting commands."""
    if text is None:
        return []
    texts = re.split(r'@\[.*?\]@', text)
    return texts



def format_for_home_assistant(command):
    if command is None:
        return None
    # Split the command string into values
    values = command.split(",")
    
    # Ensure the correct number of values (4 values: x, y, brightness, transition)
    if len(values) != 4:
        raise ValueError("Invalid command format. Expected 4 values separated by commas.")

    # Convert each value to the appropriate data type (float or int)
    try:
        x = float(values[0])
        y = float(values[1])
        brightness = int(values[2])
        transition = float(values[3])
    except (ValueError, IndexError):
        raise ValueError("Invalid values in the command.")

    # Create the formatted command dictionary
    formatted_command = {
        "xy": [x, y],
        "brightness": brightness,
        "transition": transition
    }
    
    logging.info(f"Formatted command: {formatted_command}")
    
    # Return the formatted command as a JSON-formatted string
    return json.dumps(formatted_command)


def create_command_text_list(text):
    logging.info(f"Text received: {text}")
    
    commands = find_lighting_commands(text) if text is not None else []
    texts = split_text_by_commands(text) if text is not None else []
    command_text_list = []

    # Handle text starting without a command
    if text and not text.startswith('@['):
        command_text_list.append((None, texts.pop(0).strip()))

    for command, txt in zip(commands, texts):
        formatted_command = format_for_home_assistant(command) if command is not None else None
        
        # Handle consecutive commands without text in between
        txt = txt if txt != '' else ' '
        command_text_list.append((formatted_command, txt.strip() if txt else None))
        
    logging.info(f"Command-text list created: {command_text_list}")

    return command_text_list

    

