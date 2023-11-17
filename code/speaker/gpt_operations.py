# gpt_operations.py


import os
import openai
import expressive_light
import text_to_speech_operations
import re
from dont_tell import OPENAI_API_KEY
import db_operations 
openai.api_key = OPENAI_API_KEY

def load_custom_instructions(file_path=None):
    
    if file_path is None:
        dir_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(dir_path, 'custom_instructions.txt')

    with open(file_path, 'r') as f:
        return f.read().strip()
    
# for gpt4 assistant:


# def talk_to_gpt(messages, assistant_id="asst_BPTPmSLF9eaaqyCkVZVCmK07"):

#     openai.api_key = OPENAI_API_KEY

#     thread = openai.Thread.create()
#     thread_id = thread["id"]

#     for message in messages:
#         openai.Message.create(
#             thread_id=thread_id,
#             role=message["role"],
#             content=message["content"]
#         )

#     run = openai.Run.create(
#         thread_id=thread_id,
#         assistant_id=assistant_id
#     )

#     response_messages = openai.Message.list(thread_id=thread_id)
    
#     assistant_response = response_messages["data"][-1]["content"]

#     return assistant_response



for gpt 3.5:

def talk_to_gpt(messages):
    custom_instructions = load_custom_instructions()
    messages.insert(0, {"role": "system", "content": custom_instructions})
    
    model_engine = "gpt-3.5-turbo"
    response = openai.ChatCompletion.create(
        model=model_engine, messages=messages, temperature=0.9
    )
    return response.choices[0].message['content'].strip()

# for older gpt models:

# def talk_to_gpt(messages):
#     custom_instructions = load_custom_instructions()
    
#     model_engine = "davinci-002"
#     prompt = custom_instructions + " " + " ".join([msg["content"] for msg in messages if msg["role"] != "system"])

#     response = openai.Completion.create(
#         engine=model_engine,
#         prompt=prompt,
#         max_tokens=100,  # Set your desired max tokens here
#         temperature=0.6
#     )
#     return response.choices[0].text.strip()

def handle_conversation(messages):
    gpt_response = talk_to_gpt(messages)
    print(f"Received GPT response: {gpt_response}")

    if '@[' in gpt_response and ']@' in gpt_response:
        print("Lighting commands found. Parsing and sending to expressive_light.")
        command_text_list = expressive_light.create_command_text_list(gpt_response)
        for command, text in command_text_list:
            print(f"Sending command: {command} to lighting control.")
        
        stripped_response = re.sub(r'@\[.*?\]@', '', gpt_response)
        print(f"Stripped Response: {stripped_response}")
        db_operations.save_to_db('Agent', stripped_response)

        return command_text_list, None  # return the command_text_list and a None for the text

    else:
        db_operations.save_to_db('Agent', gpt_response)
        return None, gpt_response  # return a None for the command_text_list and the text
