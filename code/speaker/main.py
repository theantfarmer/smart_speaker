import threading
import time
import string
import asyncio
import uuid
from dont_tell import SECRET_PHRASES
import traceback
from queue import Queue
from wake_words import wake_words
from db_operations import initialize_db, save_to_db
from text_to_speech_operations import talk_with_tts, tts_outputs
from speech_to_text_operations_fasterwhisper import capture_speech
from home_assistant_interactions import flattened_home_assistant_commands, execute_command_in_home_assistant
from llm_operations import handle_conversation
from queue_handling import send_to_tts_queue, send_to_tts_condition
from shared_variables import most_recent_wake_word, user_response_window, user_response_en_route
from centralized_tools import handle_tool_request, tool_commands_list, tool_names_list, tool_commands_map_dict

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

wake_word_active = True 
function_wake_word_active  = True
slow_wake_word_active = False
previous_user_input_text = "" 

# user function request is the function requested by a function wake word
# this allows certain wake words to send user input directly to a specified function
user_function_request = None

# Disable wake word briefly so user can speak slowly or respond to agent
def disable_normal_wake_word():
    global wake_word_active  
    wake_word_active = False
    print("Wake word disabled for a few seconds.")
    time.sleep(7)  
    wake_word_active = True
    print("Wake word re-enabled.")

# a similar system for for function wake words.  
def disable_function_wake_word():
    global function_wake_word_active, user_function_request  
    function_wake_word_active = False
    print("Function wake word disabled for a few seconds.")
    time.sleep(7)  
    function_wake_word_active = True
    user_function_request = None
    print("Function wake word re-enabled.")

# this allows the wake word to arrive in seperate strings 
# so the user can pause mid wake word
def enable_slow_wake_word():
    global slow_wake_word_active, previous_user_input_text
    slow_wake_word_active = True
    print("Slow wake word is True for a few seconds.")
    time.sleep(7)
    slow_wake_word_active = False
    previous_user_input_text = "" 
    print("Slow wake word false.")

def send_to_tts(text):
    with send_to_tts_condition:
        send_to_tts_queue.put(text)
        # print("MAIN Added to send_to_tts_queue.")
        send_to_tts_condition.notify()
        # print("MAIN send_to_tts_condition set.")

def main():
    global user_input_text, mp3_queue, wake_word_active, function_wake_word_active, slow_wake_word_active, user_function_request, previous_user_input_text  
    print("Main function started.")
    initialize_db()
    # stop_recording()
    messages = []
       

       
    user_input_text = "" 
    #command text stripped is the user input minus the wake word after the wake word is processed

    normal_wake_words = []
    # basic wake words that only execute what follows them

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
    
    response_text = None
    # user response after TTS finishes speaking
        
    direct_wake_word_chopper = []    
    
    function_input_dict = {}
    function_map = {}

    # talk_with_tts("")
    send_to_tts("hey. ready.")
    #startup complete

    # below, the special wake words list
    # is built.  For every command with 
    # "[command]" in it, "[command]" is 
    # replaced with a command from the 
    # list "flattened_home_assistant_commands". This is 
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
    
    # BUILD wake words here:
    for wake_word in wake_words:
        if "[command]" in wake_word:
            chop_index = wake_word.find("[command]")
            direct_wake_word = wake_word[:chop_index].strip()
            direct_wake_word_chopper.append(direct_wake_word)
            all_commands = flattened_home_assistant_commands + tool_commands_list
            # this is a list of all commands imported from other modules
            # it will automatically be turned into command wake words   
            for command in all_commands:
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
            normal_wake_words.append(wake_word)

    print(f"wake_to_functions_dict: {wake_to_functions_dict}")
    print(f"function_wake_words: {function_wake_words}")

    # we need a list of all the wake words combined
    # for the slow wake word feature. 
    all_wake_words_list = normal_wake_words.copy()
    all_wake_words_list.extend(function_wake_words)
    all_wake_words_list.extend(command_wake_words)


    try:
        while True:
            model=None
            # print("Waiting for speech...")
            print("Before capture speech in main")
            text = capture_speech() if response_text is None else response_text
            print("after capture speech in main")
            print(f"returned to main: {text}")
            stop_iteration = False
            function_wake_word_found = False
            command_wake_word = False
            user_input_text = ""

            if not text and not response_text:
                continue

            print(f"Captured text: {text}")
            print(f"Checking for echo: {text}")
            if check_for_echo(text, tts_outputs):
                print("Echo detected, ignoring...")
                continue 

            wake_word_found = False
            command_wake_word_found = False

            if text or response_text:
                if response_text:
                    text = response_text
                    response_text = None
                print(f"Captured text: {text}")
                user_input_text = text.strip()
                if slow_wake_word_active:
                    print("if slow word block used")
                    user_input_text = previous_user_input_text + " " + user_input_text
                    print(f"old and new user txt combined: {user_input_text}")
                # Remove punctuation and convert to lowercase
                user_input_text = user_input_text.translate(str.maketrans('', '', string.punctuation)).replace('-', ' ').lower()
                 
                # DETECT wake words here:        
                for command_wake_word in command_wake_words:
                    if command_wake_word.lower() in user_input_text:
                        wake_word_found = True
                        print(f"Special wake word detected: {command_wake_word}")
                        # Correctly use the command_wake_word to fetch the command from the dictionary
                        if command_wake_word.lower() in wake_to_commands_dict:
                            # Fetch the command associated with the special wake word
                            user_input_text = wake_to_commands_dict[command_wake_word.lower()]
                            print(f"Command to execute: {user_input_text}")
                            command_wake_word = True
                            break
                        else:
                            print(f"No matching command found for: {command_wake_word}")

                for function_wake_word in function_wake_words:
                    if function_wake_word.lower() in user_input_text:
                        print(f"Function wake word detected: {function_wake_word}")
                        index = user_input_text.find(function_wake_word.lower())
                        if index != -1:
                            end_index = index + len(function_wake_word)
                            most_recent_wake_word.value = function_wake_word.encode('utf-8')
                            print(f"Updated most recent function wake word: {most_recent_wake_word.value.decode('utf-8')}")
                            user_input_text = user_input_text[end_index:].strip()
                            print(f"Query to function: {user_input_text}")
                            if function_wake_word.lower() in wake_to_functions_dict:
                                user_function_request = wake_to_functions_dict[function_wake_word.lower()]
                                print(f"Function to call: {user_function_request}")
                                # Check if the input text is empty after trimming and cleaning
                                if not user_input_text or user_input_text.isspace():
                                    print("No command provided after the function wake word. Ignoring...")
                                    threading.Thread(target=disable_function_wake_word).start()
                                    stop_iteration = True
                                elif user_input_text:
                                    print("command found after the function wake word.")   
                                    function_input_dict[user_function_request] = user_input_text
                                    wake_word_found = True
                                    function_wake_word_found = True
                      

                # Check for wake words. If True, remove the wake word.
                # even if wake word is disabled, if the user uses a wake word we need to scrub it
             
                for wake_word in wake_words:
                    if wake_word.lower() in user_input_text:
                        print(f"Normal wake word detected: {wake_word}")
                        index = user_input_text.find(wake_word.lower())
                        if index != -1:
                            end_index = index + len(wake_word)
                            most_recent_wake_word.value = wake_word.encode('utf-8')
                            print(f"Updated most recent wake word: {most_recent_wake_word.value.decode('utf-8')}")
                            user_input_text = user_input_text[end_index:].strip()
                            print(f"Processed user_input_text: '{user_input_text}'")
                            # Check if the input text is empty after trimming and cleaning
                            if not user_input_text or user_input_text.isspace():
                                print("No command provided after the wake word. Ignoring...")
                                threading.Thread(target=disable_normal_wake_word).start()
                                stop_iteration = True
                            else:
                                wake_word_found = True
                                print(f"Command to execute: {user_input_text}")
                            break
                
                if stop_iteration:
                    with user_response_en_route.get_lock():
                        if user_response_en_route.value:
                            user_response_en_route.value = False
                            with most_recent_wake_word.get_lock():
                                # most_recent_wake_word.value = -0b' ' * 150
                                print(f"stop iteration reset most recent ww: {most_recent_wake_word.value.decode('utf-8')}")
                    response_text = None
                    stop_iteration = False
                    continue

                # this handles query text that arrives seperately from the command wake word, allowing user pause            
                if not function_wake_word_active:
                    if user_function_request is not None:
                        print("command found after the function wake word.")   
                        function_input_dict[user_function_request] = user_input_text
                        wake_word_found = True
            
                #ignore everything without a wake word or special wake word
                if not wake_word_found and wake_word_active:
                        
                    # If TTS just finished speaking and a previous wake word
                    #  is stored, we tack it on on to incoming text if 
                    # no other wake word is present so the user can converse
                    # with the model

                    with user_response_en_route.get_lock():
                        print(f"With user_response_en_route.get_lock(). Current value: {user_response_en_route.value}")
                        if user_response_en_route.value:
                            print(f"Inside if user_response_en_route.value. Value is True.")
                            with most_recent_wake_word.get_lock():
                                if most_recent_wake_word.value:
                                    response_text = f"{most_recent_wake_word.value.decode('utf-8')} {user_input_text}"
                                    most_recent_wake_word.value = b' ' * 150
                                    user_response_en_route.value = False
                                    continue
                            
                    # This is where slow wake words are handled.  If a user says
                    # simply "hey," we check it against the all wake words list
                    # and make a new list of all the wake words that start with
                    # "hey."  We the count the number of items in that list and
                    # if it equals 2 or more, we turn on slow wake word for a 
                    # few seconds.  While its on, we combine the previous user
                    # input ("hey") with what ever comes in next and see if the 
                    # combined string triggers any of the wake word logic.  This
                    # allows to the user to pause mid wake word and corrects 
                    # errors where the wake word was accidently split up.

                    slow_wake_word_working_list = [wake_word for wake_word in all_wake_words_list if wake_word.startswith(user_input_text)]
                    num_of_matches = len(slow_wake_word_working_list)
                    print(f"Number of matches in slow_wake_word_working_list: {num_of_matches}")
                    
                    if num_of_matches < 2:
                        continue
                    else:
                        threading.Thread(target=enable_slow_wake_word).start()
                        previous_user_input_text = user_input_text
                    continue  
                                                                                                        
            is_command_executed = False
            
            # if not function_wake_word:
            #secret phrases are listed in a separate file.
            #they are not recorded in the db
            
            if not function_wake_word_found:
                if user_input_text in SECRET_PHRASES:
                    secret_response = SECRET_PHRASES[user_input_text]
                    talk_with_tts(secret_response)
                    continue
            
                save_to_db('User', user_input_text)
            
            if user_input_text in tool_commands_list or user_function_request in tool_names_list:
                if not function_wake_word_found:
                    tool_name = tool_commands_map_dict[user_input_text]
                else:
                    tool_name = user_function_request
                tool_input_dict = {user_input_text: tool_name}
                # Generate a unique tool_use_id to track tool call
                main_tool_use_id = f"main_toolu_{uuid.uuid4()}"
                print("calling tool")
                is_command_executed, command_response, _ = asyncio.run(handle_tool_request(tool_input_dict, main_tool_use_id))
                if is_command_executed:
                    save_to_db('Agent', command_response)
                    print(f"About to call talk_with_tts with command_response: {command_response}")
                    with send_to_tts_condition:
                        send_to_tts_queue.put(command_response)
                        send_to_tts_condition.notify()
                continue
            
            if user_function_request == "speak_to_home_assistant" or user_input_text in flattened_home_assistant_commands:
                success, ha_response = execute_command_in_home_assistant(user_input_text)
                if success:
                    talk_with_tts(ha_response)
                continue

            # If the command is not executed by the smart home system, 
            # it is passed to language model.  

            if any(func in function_input_dict for func in ("chat_with_gpt", "chat_with_claude", "chat_with_dolphin")):
                handle_conversation(function_input_dict)
                print(f"Conversation handled by {next(func for func in function_input_dict if func in ('chat_with_gpt', 'chat_with_claude', 'chat_with_dolphin'))}")
                continue


            if not is_command_executed and not function_wake_word_found:
                print(f"Text before handle_conversation call: {user_input_text}")
                handle_conversation(user_input_text)
                print("Conversation handled by LLM operations")

    except Exception as e:
        print(f"An exception occurred in the main else block: {e}")
        traceback.print_exc()


    print(f"Updated function_map: {function_map}")


def check_for_echo(text, tts_outputs, echo_threshold_seconds=60):
    # print(f"Checking for echo: {text}")
    return


if __name__ == "__main__":
    main()
