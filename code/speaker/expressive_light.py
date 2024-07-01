import re
import logging
import json
from text_to_speech_operations import talk_with_tts
from home_assistant_interactions import check_machine_name
# from home_assistant_interactions import get_entity_state

# Initialize logging
logging.basicConfig(level=logging.INFO)

# expressive light takes abbreviated commands out of text and replaces them with properly formatted commands
# if text comes in as one block, it breaks it up by end of sentence and line break
    # this is importent to keep the comand syncronized with the the text
# if the text is streamed in, more aggressive sentence breaking will have already be applied
    # this can wreck havoc on the commands
    # to avoid this, use format_for_home_assistant directly

hostname = check_machine_name()

def format_for_home_assistant(command, include_only=None):
    """Format the command for Home Assistant."""
    try:
        if command is None:
            return None

        # remove @[ ... ]@
        command = command[2:-2]
        values = command.split(",")
        
        if len(values) != 4:
            logging.error("Invalid command format: %s. Expected 4 values separated by commas.", command)
            return None

        try:
            x = float(values[0])
            y = float(values[1])
            brightness = int(values[2])
            # transition = int(float(values[3]))  # Convert float to int
            transition = 0
        except (ValueError, IndexError):
            logging.error("Invalid values detected: %s. Expected float,float,int,float.", values)
            return None

        if not (-10 <= x <= 10 and -10 <= y <= 10 and 0 <= brightness <= 254 and transition >= 0):
            logging.error("Invalid value ranges in the command: %s", values)
            return None

        entity_id = f"light.{hostname}"

        formatted_command = {
            "entity_id": entity_id
        }
        
        if include_only is None or 'xy' in include_only:
            formatted_command['xy_color'] = [x, y]

        if include_only is None or 'brightness' in include_only:
            formatted_command['brightness'] = brightness

        if include_only is None or 'transition' in include_only:
            formatted_command['transition'] = transition


        return json.dumps(formatted_command)
    except Exception as e:
        logging.error("An unexpected error occurred in format_for_home_assistant: %s", e)
        return None

def create_command_text_list(text):
    try:
        print("Inside create_command_text_list")
        print(f"Text received create_command_text_list: {text}")
        if text is None:
            return []
        # Break up the text into individual strings based on line breaks and end of sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        command_text_tuples = []
        for sentence in sentences:
            segments = re.split(r'(@\[.*?\]@)', sentence)
            segments = [segment for segment in segments if segment.strip()]
            print("Segments:")
            for segment in segments:
                print(segment)
            for i in range(0, len(segments), 2):
                txt = segments[i].strip() if i < len(segments) else ''
                command_str = segments[i + 1].strip() if i + 1 < len(segments) else None
                print(f"\nProcessing segment {i // 2 + 1}:")
                print(f"Text: {txt}")
                print(f"Command string: {command_str}")
                if command_str:
                    command = format_for_home_assistant(command_str)  # Pass the command string with @[ ]@
                    print(f"Formatted command: {command}")
                else:
                    command = None
                    print("No command found")
                command_text_tuple = (command, txt)
                print(f"Appending tuple: {command_text_tuple}")
                command_text_tuples.append(command_text_tuple)
        return command_text_tuples
    except Exception as e:
        logging.error("An unexpected error occurred in create_command_text_list: %s", e)
        return []