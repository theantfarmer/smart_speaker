
#works
import threading
import queue
import expressive_light
from time import sleep
import logging
from dont_tell import SECRET_PHRASES
logging.basicConfig(level=logging.INFO)
import traceback
from wake_words import wake_words
from db_operations import initialize_db, save_to_db
from text_to_speech_operations import talk_with_tts
from speech_to_text_operations import capture_speech
from gpt_operations import handle_conversation, talk_to_gpt
from smart_home_parser import smart_home_parse_and_execute

WAKE_WORD_ACTIVE = True
mp3_queue = queue.Queue()

def main():
    command_text_stripped = ""
    global mp3_queue
    initialize_db()
    messages = []
    command_text_list = []
    agent_output = "Hey. Ready"
    talk_with_tts(agent_output)
    try:
        while True:
            text, error = capture_speech()
            agent_output = None  # Initialize agent_output to None
            
            if text:
                command_text_stripped = text.strip()  # Initialize and define command_text_stripped

                if WAKE_WORD_ACTIVE:
                    if any(wake_word in text.lower() for wake_word in wake_words):
                        for wake_word in wake_words:
                            if text.lower().startswith(wake_word):
                                text = text[len(wake_word):].strip()  # Remove the wake word from the text
                                break
                    else:
                        continue
                if text in SECRET_PHRASES:
                    secret_response = SECRET_PHRASES[text]
                    talk_with_tts(secret_response)
                    continue
                print(f"Text before saving to DB: {text}")  # Debug print
                save_to_db('User', text)
            # else:
            #     print(f"Text before saving to DB: {text}")
            #     save_to_db('User', text)
            if text is None:
                continue
            is_command_executed, command_response = smart_home_parse_and_execute(text)
            if is_command_executed:
                save_to_db('Agent', command_response)
                print(f"About to call talk_with_tts with command_response: {command_response}")  # Debug print
                talk_with_tts(command_response)
                print(f"Returned from talk_with_tts.")  # Debug print
                continue

            # If the command is not executed by the smart home system, pass it to GPT
            if not is_command_executed:
                # Append the user's input to the messages list
                messages.append({"role": "user", "content": text})
                # Handle the conversation with GPT
                command_text_list, gpt_response = handle_conversation(messages)

            # Process any commands returned from GPT
            if command_text_list:
                # Use command_text_list as needed
                for command, txt in command_text_list:
                    print(f"About to call talk_with_tts with command: {command}, text: {txt}")
                    talk_with_tts(txt, command)

            else:
                if gpt_response:
                    talk_with_tts(gpt_response, None)


    except Exception as e:
        print(f"An exception occurred in the main else block: {e}")
        traceback.print_exc()

    finally:
        pass

if __name__ == "__main__":
    main()
