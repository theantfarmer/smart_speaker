import threading
import expressive_light
import time
import string
import spacy
from spacy.matcher import PhraseMatcher
import logging
import pyaudio
import audioop
import subprocess
import webrtcvad
from dont_tell import SECRET_PHRASES
import traceback
from queue import Queue
from wake_words import wake_words
from db_operations import initialize_db, save_to_db
from text_to_speech_operations import talk_with_tts, tts_outputs
from speech_to_text_operations_fasterwhisper import capture_speech
from smart_home_parser import smart_home_parse_and_execute
from home_assistant_interactions import flattened_commands, raw_commands_dict
from llm_operations import handle_conversation, all_llm_functions

WAKE_WORD_ACTIVE = True
nlp = spacy.load("en_core_web_sm")
# matcher = PhraseMatcher(nlp.vocab) 
# transcribed_texts = Queue()
mp3_queue = Queue()

# This script manages the other modules in this 
# program, beginning with speech recognition, then
# checks for wake words and otherwise discards all
# speech.

# A separate file contains a list of user defined 
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

# Function wake words allow the user to direct 
# their input to a specific function.  This means
# saying "hey gpt" or "hey home assistant" before
# a query will ensure it is directed to that specific
# function.  It allows access to multiple agents.
# "Hey system" will eventually allow changing user 
# prefs. 

# The rest of this script checks the command
# for secret phrases, sends to smart home parser
# to check for smart home commands, sends to
# gpt operations to interact with large language
# models, and sends returns to text to speech to 
# be spoken.  

#All interactions are saved to a DB unless they
#are marked secret.

def prepare_for_tts(result):
    if isinstance(result, list):
        for command, text in result:
            print(f"MAIN About to call talk_with_tts with text: {text}, command: {command}")
            talk_with_tts(text, command)
    else:
        print("main llm else, non tuple")
        llm_response = result
        if llm_response:
            talk_with_tts(llm_response, None)

# directory services is used to direct specialty wake words that immediately call a function.  
# for example, a wake word such as "hey gpt" will use it to send user input directly to chatgpt
# and bypass everything else.  


def directory_services(function_input_dict):
    print(f"Received function_input_dict: {function_input_dict}")
    
    if any(func in function_input_dict for func in ("chat_with_gpt", "chat_with_claude", "chat_with_dolphin")):
        result = handle_conversation(function_input_dict)
        prepare_for_tts(result)  # Call the common function
        return result
    
    else:
        pass

def main():
    
    print("Main function started.")
    initialize_db()
    # stop_recording()
    messages = []
    global mp3_queue
    
    global user_input_text
    user_input_text = "" 
    #command text stripped is the user input minus the wake word after the wake word is processed

    command_text_list = []
    # this is what goes to gpt.  clean it up.
    
    command_wake_words = []
    # command wake words is a list that uses commands as wake words and executes the command immediately.  

    wake_to_commands_dict = {}
    # this ties each special wake word to the command it is based on to revert it to pre-wake word form for processing
    
    function_wake_words = []
    # these wake words call direct functions so you can direct your query to a specific place

    wake_to_functions_dict = {}
    # These dictionaries map function wake words to their functions 
    
    direct_wake_word_chopper = []    
    
    function_wake_word_found = False
    user_function_request = None
    function_input_dict = {}
    function_map = {}

    # talk_with_tts("")
    talk_with_tts("hey. ready.")
    #startup complete

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
                command_wake_word = wake_word.replace("[command]", command)
                command_wake_words.append(command_wake_word)

                # Populate the wake_to_commands_dict
                full_wake_word = direct_wake_word + " " + command
                wake_to_commands_dict[full_wake_word.lower()] = command
        elif "f[" in wake_word and "]" in wake_word:
            start_index = wake_word.find("f[") + 2
            end_index = wake_word.find("]")
            function_call = wake_word[start_index:end_index]
            function_wake_word = wake_word[:start_index - 2].strip()
            wake_to_functions_dict[function_wake_word] = function_call
            function_wake_words.append(function_wake_word)
        else:
            continue

    print(f"wake_to_functions_dict: {wake_to_functions_dict}")
    print(f"function_wake_words: {function_wake_words}")

      
    try:
        while True:
            model=None
            # print("Waiting for speech...")
            print("Before capture speech in main")
            text = capture_speech()
            print("after capture speech in main")
            print(f"returned to main: {text}")
            
            if not text:
                continue

            text = text.strip()  
            print(f"Captured text: {text}")
            print(f"Checking for echo: {text}")
            if check_for_echo(text, tts_outputs):
                print("Echo detected, ignoring...")
                continue 

            wake_word_found = False
            command_wake_word_found = False

            if not text:
                continue

            if text:
                print(f"Captured text: {text}")
                user_input_text = text.strip()
                
                # Remove punctuation and convert to lowercase
                user_input_text = user_input_text.translate(str.maketrans('', '', string.punctuation)).lower()
                
                if WAKE_WORD_ACTIVE:
                    # Check for wake words.  If True, remove the wake word.  
                    for wake_word in wake_words:
                        if wake_word.lower() in user_input_text:
                            wake_word_found = True
                            print(f"Normal wake word detected: {wake_word}")
                            index = user_input_text.find(wake_word.lower())
                            if index != -1:  # If the wake word is found
                                end_index = index + len(wake_word)
                                user_input_text = user_input_text[end_index:].strip().replace('-', ' ')
                                print(f"Command to execute: {user_input_text}")

                    for command_wake_word in command_wake_words:
                        if command_wake_word.lower() in user_input_text:
                            command_wake_word_found = True
                            print(f"Special wake word detected: {command_wake_word}")
                            # Correctly use the command_wake_word to fetch the command from the dictionary
                            if command_wake_word.lower() in wake_to_commands_dict:
                                # Fetch the command associated with the special wake word
                                user_input_text = wake_to_commands_dict[command_wake_word.lower()]
                                print(f"Command to execute: {user_input_text}")
                                break
                            else:
                                print(f"No matching command found for: {command_wake_word}")

                    for function_wake_word in function_wake_words:
                        if function_wake_word.lower() in user_input_text:
                            function_wake_word_found = True
                            print(f"Function wake word detected: {function_wake_word}")
                            index = user_input_text.find(function_wake_word.lower())
                            if index != -1:
                                end_index = index + len(function_wake_word)
                                user_input_text = user_input_text[end_index:].strip()
                                print(f"Query to function: {user_input_text}")
                                if function_wake_word.lower() in wake_to_functions_dict:
                                    user_function_request = wake_to_functions_dict[function_wake_word.lower()]
                                    print(f"Function to call: {user_function_request}")
                                    function_input_dict[user_function_request] = user_input_text
                                    directory_services(function_input_dict)
                                    break
                                                
                    #ignore everything without a wake word or special wake word
                    if not wake_word_found and not command_wake_word_found:
                        continue
             
            #secret phrases are listed in a separate file.
            #they are not recorded in the db
            if user_input_text in SECRET_PHRASES:
                secret_response = SECRET_PHRASES[user_input_text]
                talk_with_tts(secret_response)
                continue
           
            save_to_db('User', user_input_text)
            
            # Here the command is checked for smart home commands.  
            # Commands are predictable and stop commands from proceeding
            # further.  
            user_text_stripped = user_input_text.translate(str.maketrans('', '', string.punctuation))
            is_command_executed, command_response = smart_home_parse_and_execute(user_text_stripped, raw_commands_dict)
            if is_command_executed:
                save_to_db('Agent', command_response) #command response holds the string to be read, as returned from smart home parser
                print(f"About to call talk_with_tts with command_response: {command_response}")  # Debug print
                talk_with_tts(command_response)
                print("Returned from talk_with_tts.")  # Debug print
                continue

            # If the command is not executed by the smart home system, 
            # it is passed to language model.  
            if not is_command_executed:
                print(f"Text before handle_conversation call: {user_input_text}")
                result = handle_conversation(user_input_text)
                print(f"Result after handle_conversation: {result}")
                prepare_for_tts(result)


    except Exception as e:
        print(f"An exception occurred in the main else block: {e}")
        traceback.print_exc()

# build the function map 
    for function_dict in all_llm_functions:
        function_name = function_dict["function_name"]
        function_map[function_name] = function_dict

    print(f"Updated function_map: {function_map}")





def check_for_echo(text, tts_outputs, echo_threshold_seconds=60):
    # print(f"Checking for echo: {text}")
    # # Normalize the input text for comparison
    # text_no_punctuation = text.translate(str.maketrans('', '', string.punctuation)).lower()
    # text_segments = text_no_punctuation.split()

    # # Initialize a flag to track echo detection status
    # echo_detected = False

    # # Iterate through each segment of the input text
    # for i, segment in enumerate(text_segments):
    #     segment_text = ' '.join(text_segments[i:]) 
    #     for spoken_text, timestamp in tts_outputs.items():
    #         # Normalize stored TTS output for comparison
    #         spoken_text_no_punctuation = spoken_text.translate(str.maketrans('', '', string.punctuation)).lower()

    #         # Check if the segment matches any recent TTS outputs within the echo threshold
    #         if time.time() - timestamp <= echo_threshold_seconds and segment_text.startswith(spoken_text_no_punctuation):
    #             print(f"Echo detected, ignoring: {segment_text}")
    #             echo_detected = True
    #             break 
            
    #     if echo_detected:
    #         break 
        
    # if not echo_detected:
    #     print("No echo detected, processing further...")
    #     return False  # Indicates no echo was detected, and further processing should occur

    return


if __name__ == "__main__":
    main()
