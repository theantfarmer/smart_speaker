import re
import json
import sys

def find_lighting_commands(text):
    """Identify lighting commands in the text."""
    # Regular expression to find @[x,y,brightness,transition]@
    pattern = r'@\[(.*?)\]@'
    return re.findall(pattern, text)

def split_text_by_commands(text):
    """Split text based on lighting commands."""
    # Splits text by @[...]@
    return re.split(r'@\[.*?\]@', text)

def format_for_home_assistant(command):
    """Format lighting command for Home Assistant."""
    # Convert command string to individual float values
    x, y, brightness, transition = map(float, command.split(","))
    formatted_command = {
        "xy": [x, y],
        "brightness": brightness,
        "transition": transition
    }
    return json.dumps(formatted_command)

def create_command_text_list(text):
    """Create a list of dictionaries containing the formatted command and associated text."""
    commands = find_lighting_commands(text)
    texts = split_text_by_commands(text)
    command_text_list = []

    # Create key-value pairs for each command and text chunk
    for command, txt in zip(commands, texts):
        formatted_command = format_for_home_assistant(command)
        command_text_list.append({
            "command": formatted_command,
            "text": txt.strip()
        })

    return command_text_list

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text_with_commands = sys.argv[1]
        command_text_list = create_command_text_list(text_with_commands)
        print(command_text_list)
    else:
        print("Please provide a text string with lighting commands.")
