# gpt_operations.py


import os
import openai
import expressive_light
import text_to_speech_operations
from dont_tell import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def load_custom_instructions(file_path=None):
    
    if file_path is None:
        # Get the directory where the script is located
        dir_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(dir_path, 'custom_instructions.txt')

    with open(file_path, 'r') as f:
        return f.read().strip()
    
# for newer gpt models:

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
    # Get the response from GPT
    gpt_response = talk_to_gpt(messages)
    print(f"Received GPT response: {gpt_response}")  # Debugging

    # Check if there are any lighting commands in the GPT response
    if '@[' in gpt_response and ']@' in gpt_response:
        print("Lighting commands found. Parsing and sending to expressive_light.")  # Debugging

        # Parse the commands and texts
        command_text_list = expressive_light.create_command_text_list(gpt_response)
        
        # Process them for lighting command execution
        for command, text in command_text_list:
            print(f"Sending command: {command} to lighting control.")  # Debugging
            # Your function here to send `command` to the lighting control system

        # Strip commands and save to DB
        clean_text = expressive_light.strip_commands(gpt_response)  # Assuming you have a function for this
        save_to_db(clean_text)  # Your function here to save `clean_text` to the database

    else:
        print("No lighting commands found. Sending directly to TTS.")  # Debugging
        text_to_speech_operations.mp3_queue.put((gpt_response, None))
        send_to_main(gpt_response)  # Your function here to send `gpt_response` back to main.py
