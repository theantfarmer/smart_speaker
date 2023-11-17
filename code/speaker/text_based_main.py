import threading
import queue
from time import sleep
import logging
import sys

logging.basicConfig(level=logging.INFO)

from db_operations import initialize_db, save_to_db
from gpt_operations import handle_conversation
from smart_home_parser import smart_home_parse_and_execute

def main():
    command_text_stripped = ""
    initialize_db()
    messages = []
    command_text_list = []
    agent_output = "Hey. Ready"
    print(agent_output)  # Replaces talk_with_tts

    try:
        while True:
            text = sys.argv[1] if len(sys.argv) > 1 else "No input provided"  # Replaces capture_speech()

            if text is None:
                continue
            agent_output = None

            save_to_db('User', text)  # Save user text to the database
            
            is_command_executed, command_response = smart_home_parse_and_execute(text)
            if is_command_executed:
                save_to_db('Agent', command_response)
                print(f"About to call talk_with_tts with command_response: {command_response}")  # Debug print
                talk_with_tts(command_response)
                print(f"Returned from talk_with_tts.")  # Debug print
                continue
            else:
                messages.append({"role": "user", "content": text})
                agent_output = handle_conversation(messages)
                messages.append({"role": "agent", "content": agent_output})
                
                if isinstance(agent_output, tuple):
                    continue
                
                if agent_output is None:
                    print(None)  # Replaces talk_with_tts(None, None)
                else:
                    print(agent_output)  # Replaces talk_with_tts

    except Exception as e:
        pass

if __name__ == "__main__":
    main()
