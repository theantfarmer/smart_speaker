import re
import json
import requests
import logging
import time
import db_operations 
import expressive_light
from llm_chatgpt import llm_model as chat_with_gpt
from llm_claude import llm_model as chat_with_claude
from llm_gpt_dolphinmini import llm_model as chat_with_dolphin
import inspect
import queue

llm_response_queue = queue.Queue()

#makes a list of all functions in this module to be called via directory services in main.py
def list_llm_functions():
    current_module = inspect.getmodule(list_llm_functions)
    module_functions = inspect.getmembers(current_module, inspect.isfunction)
    function_dicts = [{"function_name": name, "module": "llm_operations"} for name, _ in module_functions]
    return function_dicts

all_llm_functions = list_llm_functions()


def handle_conversation(user_input):

    default_model = chat_with_dolphin

    if isinstance(user_input, dict):
        if "chat_with_gpt" in user_input:
            user_input_text = user_input["chat_with_gpt"]
            llm_response = chat_with_gpt(user_input_text)
        elif "chat_with_claude" in user_input:
            user_input_text = user_input["chat_with_claude"]
            llm_response = chat_with_claude(user_input_text)
        elif "chat_with_dolphin" in user_input:
            user_input_text = user_input["chat_with_claude"]
            llm_response = chat_with_dolphin(user_input_text)
        else:
            user_input_text = user_input.get(None)
            llm_response = default_model(user_input_text)
    else:
        llm_response = default_model(user_input)
             
    if inspect.isgenerator(llm_response):
        """
        Passing streaming text responses requires use of a generator.  
        But that creates huge problems for subsequint processing logic.  
        One work around is using queues to strings as indavidual strings,
        though that lead to circular errors.  Using queues to extract strings
        immediately was another idea.  But passing between functions and modules
        meant a confusing and complicated system of queues to iterate each generator.
        This system didn't quite make sense to me.  So for now, I am 
        over riding streaming by merging incoming streams until I come
        up with a better solution.      
        """
        merged_response = ""
        for chunk in llm_response:
            if chunk is not None:
                merged_response += chunk
        llm_response = merged_response

    print(f"Stripped Response: {llm_response}")

    if '@[' in llm_response and ']@' in llm_response:
        print("Lighting commands found. Parsing and sending to expressive_light.")
        command_text_list = expressive_light.create_command_text_list(llm_response)
        stripped_response = re.sub(r'@\[(.*?)\]@', '', llm_response)
        print(f"Stripped Response: {stripped_response}")
        db_operations.save_to_db('Agent', stripped_response)
        return command_text_list
    else:
        db_operations.save_to_db('Agent', llm_response)
        print(f"into db: {llm_response}")
        return llm_response

    
