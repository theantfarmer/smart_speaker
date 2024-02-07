import threading
import queue
import expressive_light
from time import sleep
import logging
import pyaudio
import audioop
import webrtcvad
from dont_tell import SECRET_PHRASES
logging.basicConfig(level=logging.INFO)
import traceback
from wake_words import wake_words
from db_operations import initialize_db, save_to_db
from text_to_speech_operations import talk_with_tts
from speech_to_text_operations import capture_speech
from gpt_operations import handle_conversation, talk_to_gpt
from smart_home_parser import smart_home_parse_and_execute
from home_assistant_interactions import flattened_commands, raw_commands_dict

# This script manages the other modules in this 
# program, beginning with speech recognition, then
# checks for wake words and otherwise discards all
# speech.

# A separate file contains a list of user define 
# wake words and phrases used to wake the system. 
# If a wake phrase is "hey Karen," then to turn 
# on the lights, the user would say "hey karen
# turn on the lights."  "Hey karen" would then 
# be cut and only "turn on the lights" would be 
# further processed.  A wake word may contain 
# "[command]" as a placeholder to shorten the 
# wake word.  For example, if "hey [command]" 
# is on the wake word list, the word "hey" 
# will be added to the front of all available 
# commands, which are then added to a list 
# of special wake words.  In this case, the 
# user could simply say "hey turn on the lights" 
# to turn on the lights.  

# The rest of this script checks the command
# for secret phrases, sends to smart home parser
# to check for smart home commands, sends to
# gpt operations to interact with large language
# models, and sends returns to text to speech to 
# be spoken.  

#All interactions are saved to a DB unless they
#are marked secret.

WAKE_WORD_ACTIVE = True
mp3_queue = queue.Queue()

def main():
    
    initialize_db()
    messages = []
    global mp3_queue
    
    global command_text_stripped
    command_text_stripped = "" 
    #command text stripped is the user input minus the wake word after the wake word is processed

    command_text_list = []
    # this is what goes to gpt.  clean it up.
    
    special_wake_words = []
    # special wake words is a list that uses commands as wake words.  
    
    wake_to_commands_dict = {}
    # this ties each special wake word to the command it is based on to revert it to pre-wake word form for processing
    
    direct_wake_word_chopper = []
    
    agent_output = "Hey. Ready"
    #agent output is the return that is sent to text to speech
    
    
    
    talk_with_tts(agent_output)
    #calls text to speech


    # below, the special wake words list
    # is built.  For every command with 
    # "[command]" in it, "[command]" is 
    # replaced with a command from the 
    # list "flattened_commands". This is 
    # repeated for each command and each
    # wake word containing "[command]".
    # The results are added to a list
    # of special wake words that the
    # script will listen for.  The
    # special wake words are also
    # added to a list of dictionaries
    # so the special wake word can
    # be reverted to its associated
    # command after the wake word is
    # used.
    
    for wake_word in wake_words:
        if "[command]" in wake_word:
            chop_index = wake_word.find("[command]")
            direct_wake_word = wake_word[:chop_index].strip()
            direct_wake_word_chopper.append(direct_wake_word)
            for command in flattened_commands:
                special_wake_word = wake_word.replace("[command]", command)
                special_wake_words.append(special_wake_word)

                # Populate the wake_to_commands_dict
                full_wake_word = direct_wake_word + " " + command
                wake_to_commands_dict[full_wake_word.lower()] = command
        else:
            continue

    # print(f"special_wake_words: {special_wake_words}")
    # print(f"wake_words: {wake_words}")
    # print(f"wake_to_commands_dict: { wake_to_commands_dict}")
    # print(f"flattened_commands: {flattened_commands}")
    # print(f"raw_commands_dict: {raw_commands_dict}")
      
    try:
        while True:
            text, error = capture_speech()
            if not text:
                continue

            command_text_stripped = text.strip()  
            print(f"Captured text: {text}")
            wake_word_found = False
            special_wake_word_found = False

            if not text:
                continue

            if text:
                command_text_stripped = text.strip()
                if WAKE_WORD_ACTIVE:
                    # Check for wake words.  If True, remove the wake word.  
                    for wake_word in wake_words:
                        if wake_word in command_text_stripped.lower():
                            wake_word_found = True
                            print(f"Normal wake word detected: {wake_word}")
                            if command_text_stripped.lower().startswith(wake_word):
                                command_text_stripped = command_text_stripped[len(wake_word):].strip()
                                print(f"to execute: {command_text_stripped}")
                                break
                    
                    #Check for special wake words.  If True, revert to command form.  
                    for special_wake_word in special_wake_words:
                        if special_wake_word in command_text_stripped.lower():
                            special_wake_word_found = True
                            spoken_phrase = command_text_stripped.lower()
                            if spoken_phrase in wake_to_commands_dict:
                                command_text_stripped = wake_to_commands_dict[spoken_phrase]
                                print(f"to execute: {command_text_stripped}")
                                break
                            
                    #ignore everything without a wake word or special wake word
                    if not wake_word_found and not special_wake_word_found:
                        continue
             
            #secret phrases are listed in a separate file.
            #they are not recorded in the db
            if command_text_stripped in SECRET_PHRASES:
                save_to_db('User', command_text_stripped)
            
            # Here the command is checked for smart home commands.  
            # Commands are predictable and stop commands from proceeding
            # further.  
            is_command_executed, command_response = smart_home_parse_and_execute(command_text_stripped, raw_commands_dict)
            if is_command_executed:
                save_to_db('Agent', command_response)
                print(f"About to call talk_with_tts with command_response: {command_response}")  # Debug print
                talk_with_tts(command_response)
                print(f"Returned from talk_with_tts.")  # Debug print
                continue

            # If the command is not executed by the smart home system, 
            # it is passed to a large language model.  
            if not is_command_executed:
                # Append the user's input to the messages list
                messages.append({"role": "user", "content": text})
                # Handle the conversation with GPT
                command_text_list, gpt_response = handle_conversation(messages)

            # Process any commands returned from the LLM.
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


if __name__ == "__main__":
    main()
