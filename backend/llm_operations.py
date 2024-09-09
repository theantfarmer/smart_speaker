import re
import db_operations 
from expressive_light import create_command_text_list, format_for_home_assistant
from llm_chatgpt import llm_model as chat_with_llm_chatgpt
from llm_claude import llm_model as chat_with_llm_claude
from llm_gpt_dolphinmini import llm_model as chat_with_llm_dolphin
from queue_handling import llm_response_queue, llm_response_condition, send_to_tts_queue, send_to_tts_condition
import inspect
import queue
import threading 

def handle_conversation(user_input, user_request_id):
    # this is where we handle which llm model to use
    # a default model is used when plain text arrives
    # a specific model can be specified in a dict containing user text : model

    default_model = chat_with_llm_dolphin

    if isinstance(user_input, dict):
        if "chat_with_llm_chatgpt" in user_input:
            user_input_text = user_input["chat_with_llm_chatgpt"]
            llm_response = chat_with_llm_chatgpt(user_input_text, user_request_id)
        elif any(key.startswith("chat_with_llm_claude") for key in user_input):
            key = next(key for key in user_input if key.startswith("chat_with_llm_claude"))
            llm_response = chat_with_llm_claude(user_input, user_request_id)
        elif "chat_with_llm_dolphin" in user_input:
            user_input_text = user_input["chat_with_llm_dolphin"]
            thread = threading.Thread(target=chat_with_llm_dolphin, args=(user_input_text, user_request_id))
            thread.start()
        else:
            user_input_text = user_input.get(None)
            llm_response = default_model(user_input_text, user_request_id)
    else:
        llm_response = default_model(user_input, user_request_id)

def handle_llm_response(): 
    # this function handles streaming and non streaming functions
    # text may arrive as a block of text or in streaming chunks
    # if streaming, it must be proceeded by a True boolean
    # streaming text is broken at line breaks, end of sentence, or other appropriate marks
    # the text preceeding the break is sent to text to speech, the remaining text is held

    # llm response holdsthe the incoming item.  it is constantly reset.
    # streaming response holds text between iterations so it can be added to the next item
    # llm response will aquire any held text and will be processed and sent to ttsd
        # llm response contains the current working text
        # streaming response holds any text that is not needed in the current itaration and applies it to the next iteration

    # llm responses may include commands marked between @[ and ]@
    # they are very simple to sort out in non-streaming text
    # but in streaming mode, complicated logic is required
    # if streaming text contains a @[, it is treated similarly to a line break or sentence end
        # the preceeding text goes off to tts, while the command is held
        # at this point, the streaming text variable BEGINS with @[
        # once the comlete command has arrived, it is held in the variable streaming command
            # if the command is followed by text, streaming_command is held between iterations until the next line break, sentence end, or another command
            # llm_response will be set to a tuple containing comamand and text
            # if the command is followed immediately by a line break, sentence end or another command, then llm_response, 
            # llm_response is first set to None, and then a tuple containing command, None
            # in either case, llm_response is sent to the expressive light module for processing
            # and then to tts
            # the tts module will handle text paired with commands so they can be executed together
            
    incoming_text_debug = ""
    tts_text_debug = "" 
    streaming = False
    command_text_tuple = None
    user_request_id = None
    streaming_response = ""
    command_response = ""
    command_text_tuple = ""
    formatted_command = ""
    creating_command_tuple = False

    with llm_response_condition:
        # print("Waiting for notification...")
        llm_response_condition.wait()
        # print("Received notification from llm_response_condition")
  
    while True:  
        # get the first item from the queue  
        
        #llm_response is our current working item
        # it can be a boolean
        # or if its text,it is manipulated and sent to tts
        llm_response = llm_response_queue.get()
        if isinstance(llm_response, tuple):
            if len(llm_response) == 3:
                llm_response, user_request_id, streaming = llm_response
            elif len(llm_response) == 2:
                llm_response, user_request_id = llm_response
                streaming = False
            else:
                raise ValueError("Unexpected tuple length in llm_response")
        # when streaming, the first and last items should be booleans
        # when the boolean is True, we turn on streaming mode
        # when the boolean is false, we turn off streaming mode
        if isinstance(llm_response, bool): #if the first item is a boolean, we must retrieve again to get text
            streaming = llm_response
            if not streaming:
                # when streaming becomes false, we process the remaining contents of streaming response
                llm_response = streaming_response
                print("Incoming text debug:")
                print(incoming_text_debug)
                print("TTS text debug:")
                print(tts_text_debug)
                print("Final llm_response:")
                print(llm_response)
                streaming_response = ""
                command_response = ""
                command_text_tuple = ""
                formatted_command = ""
                creating_command_tuple = False
                
        if isinstance(llm_response, str):        
            llm_response = llm_response.replace("**", "")
            if streaming:
                # print(f"llm_response 1: {llm_response}")
                # the incoming content is tacked on to held content in streaming response
                streaming_response += llm_response
                # print(f"streaming_response 1: {streaming_response}")
                # we set the pattens to look for when to break up text and send to TTS
                command_pattern = r'@\['
                sentence_end_pattern = r'[.!?:](?=\s+[A-Z])|[.!?:]$|,(?=\s+)'
                line_break_pattern = r'\r?\n'
                # if a command is streaming in
                # if streaming response BEGINS with a command, we need to seperate the command
                # if it contains a command not at the beginning, we must first processes the preceeding text.    
                if streaming_response.strip() == "@":
                    continue
                if streaming_response.strip().startswith("@["):
                    #while another command is held
                    if creating_command_tuple:
                        # if another command comes in while one is already held,
                        # we must move its contents to a tuple right away
                        # we pair it with None in place of text
                        llm_response = None
                        formatted_command = format_for_home_assistant(streaming_command)
                        command_text_tuple = (formatted_command, llm_response)
                        creating_command_tuple = False
                    if ']@' in streaming_response:
                        # if a complete command has finished streaming, we cut it out and save it as streaming command
                        command_end_idx = streaming_response.index("]@") + 2
                        streaming_command = streaming_response[:command_end_idx].strip()
                        streaming_response = streaming_response[command_end_idx:].strip()
                        # after the full command is extracted, we set a boolean to say we are holding a command
                        creating_command_tuple = True
                        # print(f"Streaming command: {streaming_command}")
                    else:
                        continue
                else:
                    # if text is coming in
                    if llm_response is not None:
                        if "<thinking>" in streaming_response:
                            if "</thinking>" in streaming_response:
                                streaming_response = re.sub(r'<thinking>.*?</thinking>', '', streaming_response, flags=re.DOTALL)
                            else: 
                                continue
                        # streaming text will be severed at a line break, end of sentence, or start of a command
                        match = re.search(sentence_end_pattern, streaming_response) or re.search(line_break_pattern, streaming_response) or re.search(command_pattern, streaming_response)
                        if match:
                            # if it contains a command, we must preserve the whole command
                            if re.search(command_pattern, streaming_response):
                                end_idx = match.start()
                            # if it contains a line break or or end of sentence: 
                            else:
                                end_idx = match.end() if re.search(sentence_end_pattern, streaming_response) else match.start()
                                # llm response becomes the text preceeding the line break or end of sentence
                                # llm_response is routinely replaced through out iteration
                                llm_response = streaming_response[:end_idx]
                                # and streaming retains is the text after
                                # streaming response retains its contents throughout itteration
                                streaming_response = streaming_response[end_idx:]
                                print(f"llm_response 2: {llm_response}")
                                print(f"streaming_response 2: {streaming_response}")
                                # if llm response contains no letters or numbers, set i to None
                        else:
                            continue
                if not re.search(r'[a-zA-Z0-9]', llm_response):
                    llm_response = None
                if creating_command_tuple:
                    formatted_command = format_for_home_assistant(streaming_command)
                    command_text_tuple = (formatted_command, llm_response)
                    print(f"Command text tuple: {command_text_tuple}")

            if isinstance(command_text_tuple, tuple):
                llm_response = command_text_tuple
                # print(f"Command text tuple: {command_text_tuple}")
                command_text_tuple = ""
                formatted_command = ""

            # for non streaming, the logic remains how it was before streaming was implemented
            # db logic needs to be rethought for streaming 
            if not streaming:
                if "<thinking>" in llm_response:
                    if "</thinking>" in llm_response:
                        llm_response = re.sub(r'<thinking>.*?</thinking>', '', llm_response, flags=re.DOTALL)
                if '@[' in llm_response and ']@' in llm_response:
                    # print("Lighting commands found. Parsing and sending to expressive_light.")
                    llm_response = create_command_text_list(llm_response)
                    stripped_response = re.sub(r'@\[(.*?)\]@', '', llm_response)
                    # db_operations.save_to_db('Agent', stripped_response)
                    pass
                else:
                    # db_operations.save_to_db('Agent', llm_response)
                    pass
                
        if llm_response is not None:  
            tts_text_debug += str(llm_response) + "\n"
            with send_to_tts_condition:
                send_to_tts_queue.put((llm_response, user_request_id, streaming))
                # print("Added to send_to_tts_queue.")
                send_to_tts_condition.notify()
                # print("send_to_tts_condition set.")
                creating_command_tuple = False
                llm_response = ""


thread = threading.Thread(target=handle_llm_response,)
thread.start()