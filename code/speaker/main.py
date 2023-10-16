# Import the necessary modules and the wake_words list
#works
import threading
import queue
import expressive_light
from time import sleep
import logging
logging.basicConfig(level=logging.INFO)

from wake_words import wake_words
from db_operations import initialize_db, save_conversation, save_to_db
from text_to_speech_operations import talk_with_tts
from speech_to_text_operations import capture_speech
from gpt_operations import handle_conversation
from smart_home_parser import smart_home_parse_and_execute

WAKE_WORD_ACTIVE = True
mp3_queue = queue.Queue()



def main():
    global mp3_queue  # Access the global mp3_queue
    initialize_db()
    messages = []

    try:
        while True:
            text, error = capture_speech()
            agent_output = None  # Initialize agent_output to None
            
            logging.info(f"Initial agent_output: {agent_output}")  # Debugging line

            if text:
                # Check for wake words if the feature is active
                if WAKE_WORD_ACTIVE:
                    if any(wake_word in text.lower() for wake_word in wake_words):
                        for wake_word in wake_words:
                            if text.lower().startswith(wake_word):
                                text = text[len(wake_word):].strip()  # Remove the wake word from the text
                                break
                    else:
                        continue

                is_command_executed, command_response = smart_home_parse_and_execute(text)

                if is_command_executed:
                    print(f"Entered is_command_executed block. command_response: {command_response}")  # Debugging line
                    
                    if isinstance(command_response, tuple) and command_response[0] == "SECRET_PHRASE_FLAG":
                        print("Entered the SECRET_PHRASE_FLAG condition.")  # Debugging line
                        
                        # Special handling for secret phrases
                        secret_response = command_response[1]
                        
                        print(f"Secret response determined: {secret_response}")  # Debugging line
                        
                        print("About to call talk_with_tts for secret_response.")  # Debugging line
                        talk_with_tts(secret_response)  # Send secret response to TTS
                        
                        print("Secret response sent to TTS.")  # Debugging line
                        
                        print("About to save the conversation.")  # Debugging line
                        save_conversation(text, "I can't print that")
                        
                        print("Conversation saved.")  # Debugging line
                    else:
                        print("Entered the else block, setting agent_output.")  # Debugging line
                        
                        agent_output = command_response
                        
                        print(f"agent_output set to: {agent_output}")  # Debugging line

                        print("About to call talk_with_tts for agent_output.")  # Debugging line
                        talk_with_tts(agent_output)  # Send agent_output to TTS
                        
                        print("Agent_output sent to TTS.")  # Debugging line


                else:
                    if agent_output is not None:
                        messages.append({"role": "user", "content": text})
                        logging.info(f"Messages before handle_conversation: {messages}")# New logging statement
                    else:
                        messages.append({"role": "user", "content": text})
                        logging.info(f"Messages before further processing: {messages}")  # New logging statement
                        
                        # Here you could set agent_output based on the output from expressive_light.create_command_text_list
                        command_text_list = expressive_light.create_command_text_list(text)



                        for command, text in command_text_list:
                            # Generate TTS for the text associated with the command
                            talk_with_tts(text, command)

                        # Save the conversation to the database
                        save_conversation(text, agent_output)

                   


                logging.info(f"agent_output before tuple check: {agent_output}")  # Debugging line

                if isinstance(agent_output, tuple) and agent_output[0] == "SECRET_PHRASE_FLAG": 
                    # Special handling for secret phrases
                    secret_response = agent_output[1]
                    talk_with_tts(secret_response)  # Send secret response to TTS
                    save_conversation(text, "I can't print that")
                else:
                    command_text_list = expressive_light.create_command_text_list(text)
    
                    for command, txt in command_text_list:
                        talk_with_tts(txt, command) # Debugging line
                    
            logging.info("Entering the block to check agent_output.")  # Debugging line


                # Output agent's message (existing code continues)
            print("Entering the block to check agent_output.")
                                

                # Output agent's message
            print("Entering the block to check agent_output.")  # Debugging line

                    
            if text and "exit" in text.lower():  # Check if text is not None
                print("Exiting the conversation.")
                talk_with_tts("Exiting the conversation.")
                break

            elif error:
                talk_with_tts(error)
                save_to_db('System', error)  # Assuming save_to_db is the correct function, replace if necessary
    finally:
        # Add any cleanup operations for your threads here, if needed
        pass

if __name__ == "__main__":
    main()
    play_thread.join()
