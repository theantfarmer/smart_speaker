import anthropic
import os
from queue_handling import llm_response_queue, llm_response_condition
from dont_tell import CLAUDE_KEY

client = anthropic.Anthropic(api_key=CLAUDE_KEY)

class EventHandler:
    def on_text(self, text: str):
        llm_response_queue.put(text)

def get_or_create_basic_instructions():
    # the following sets up basic instructions for claude
    # You should edit them in the sepearte file to make them personal.
    file_path = 'claude_custom_instructions.txt'
    default_instructions = """You are a voice assistant for a smart speaker. Provide extremely concise responses suitable for speech. Aim for 1-3 short sentences max unless more detail is explicitly requested. Be direct and to the point. Prioritize brevity above all else in every response."""

    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            file.write(default_instructions)
    
    with open(file_path, 'r') as file:
        return file.read()

def get_custom_instructions():
    file_path = 'claude_custom_instructions.txt'
    if not os.path.exists(file_path):
        return ""
    with open(file_path, 'r') as file:
        return file.read()

# Load instructions on startup
basic_instructions = get_or_create_basic_instructions()
custom_instructions = get_custom_instructions()
system_prompt = f"{basic_instructions}\n\n{custom_instructions}".strip()

def llm_model(user_input, model="claude-3-opus-20240229"):
    try:
        streaming = True
        with llm_response_condition:
            llm_response_queue.put(streaming)
            llm_response_condition.notify()

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_input
                    }
                ]
            }
        ]

        with client.messages.stream(
            model=model,
            max_tokens=1000,
            temperature=0.4,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                EventHandler().on_text(text)

        llm_response_queue.put(False)  
        return ""
    except Exception as e:
        print(f"Error occurred in llm_model: {e}")
        raise e