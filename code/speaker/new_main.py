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
from gpt_operations import talk_to_gpt
from smart_home_parser import smart_home_parse_and_execute

WAKE_WORD_ACTIVE = False




def main():
    initialize_db()

    agent_output = "Hey. Ready"
    talk_with_tts(agent_output)

    while True:
        logging.info("About to capture speech")
        text, _ = capture_speech()  # Capture once and reuse
        logging.info(f"Captured text: {text}")

        if text:
            if WAKE_WORD_ACTIVE:
                for wake_word in wake_words:
                    if text.lower().startswith(wake_word):
                        text = text[len(wake_word):].strip()
                        break
                else:
                    continue
                
            agent_output = capture_and_process_speech()
            if agent_output:
                # agent_output is set, you can use it wherever you need to
                pass

                command_text_list = [("some_command", "some_text"), ("another_command", "another_text")]  # Replace this

                for command, txt in command_text_list:
                if isinstance((command, txt), tuple):
                    talk_with_tts(txt, command)
                else:
                    talk_with_tts(None, txt)

                    
                captured_text = capture_speech()  # Assuming capture_speech() returns the speech as text
                command_text_list = expressive_light.create_command_text_list(captured_text)  # Assuming this function generates your command_text_list
                
                agent_output = None  # Initialize to default value
                captured_text = capture_speech()  # Assuming capture_speech() returns the speech as text
                
                is_command_executed, command_response = smart_home_parse_and_execute(captured_text)
                
                if is_command_executed:
                    agent_output = command_response
                    logging.info("Command executed by smart_home_parse_and_execute.")
                else:
                    try:
                        command_text_list = expressive_light.create_command_text_list(captured_text)
                        logging.info("Proceeding to expressive_light processing.")
                        
                        for command, text in command_text_list:
                            if text.strip() in SECRET_PHRASES:
                                agent_output = ("SECRET_PHRASE_FLAG", SECRET_PHRASES[text.strip()])
                                logging.info("Text is a secret phrase.")
                            else:
                                is_command_executed, command_response = smart_home_parse_and_execute(command)
                                logging.info("Text is not a secret phrase, sending to smart_home_parse_and_execute.")
                                
                                if is_command_executed:
                                    agent_output = command_response
                    except NameError:
                        logging.error("expressive_light is not defined.")
        
                    # Send to TTS
                    if isinstance(agent_output, tuple):
                        talk_with_tts(agent_output[1])
                    else:
                        talk_with_tts(None, agent_output)

                    # Print agent_output
                    print(agent_output)

            # Reset agent_output at the very end
            agent_output = None

            # # Exit condition
            # if text and "exit" in text.lower():
            #     print("Exiting the conversation.")
            #     talk_with_tts("Exiting the conversation.")
            #     break

    # finally:
    #     pass  # Placeholder in case you want to add cleanup code later

if __name__ == "__main__":
    main()
