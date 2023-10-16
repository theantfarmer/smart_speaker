import threading
import queue
from time import sleep
import logging
from dont_tell import SECRET_PHRASES
logging.basicConfig(level=logging.INFO)

from wake_words import wake_words
from db_operations import initialize_db, save_conversation, save_to_db
from text_to_speech_operations import talk_with_tts
from speech_to_text_operations import capture_speech
from gpt_operations import ????
from smart_home_parser import smart_home_parse_and_execute

WAKE_WORD_ACTIVE = True
mp3_queue = queue.Queue()



def main():
    global mp3_queue  # Access the global mp3_queue
    initialize_db()

    # Indicate that the script is ready
    agent_output = "Hey. Ready"
    talk_with_tts(agent_output)
    print(agent_output)

    try:
        while True:
            text, _ = capture_speech()  # Ignore errors
            agent_output = None  # Reset agent_output to None

            if text:
                # Check for wake words
                if WAKE_WORD_ACTIVE:
                    if any(wake_word in text.lower() for wake_word in wake_words):
                        for wake_word in wake_words:
                            if text.lower().startswith(wake_word):
                                text = text[len(wake_word):].strip()
                                break
                    else:
                        continue

                command_text_list = [("some_command", "some_text"), ("another_command", "another_text")]  # Replace this

                for command, text in command_text_list:
                    if text.strip() in SECRET_PHRASES:
                        agent_output = ("SECRET_PHRASE_FLAG", SECRET_PHRASES[text.strip()])
                    else:
                        is_command_executed, command_response = smart_home_parse_and_execute(command)
                        if is_command_executed:
                            agent_output = command_response

                    # Send to TTS
                    if isinstance(agent_output, tuple):
                        talk_with_tts(agent_output[1])
                    else:
                        talk_with_tts(None, agent_output)

                    # Print agent_output
                    print(agent_output)

            # Reset agent_output at the very end
            agent_output = None

            # Exit condition
            if text and "exit" in text.lower():
                print("Exiting the conversation.")
                talk_with_tts("Exiting the conversation.")
                break

    finally:
        pass  # Placeholder in case you want to add cleanup code later

if __name__ == "__main__":
    main()
