from anthropic import AsyncAnthropic
import os
import asyncio
from queue_handling import llm_response_queue, llm_response_condition
from dont_tell import CLAUDE_KEY
from claude_tools import get_tools_for_claude, handle_tool_request

client = AsyncAnthropic(api_key=CLAUDE_KEY)

class EventHandler:
    def on_text(self, text: str):
        llm_response_queue.put(text)

def get_or_create_custom_instructions():
    file_path = 'claude_custom_instructions.txt'
    # custom instructions for claude are stored in the above file
    # By default, they inform Claude only that it is a smart speaker
    # and to keep answers short.
    # Use custom instructions to shape its voice and add persistant
    # personal information, such as where you live.  
    # NOTE: updating the default instructions below will not
    # impact what you send to claude.  The default are only
    # for creating a new  custom instructions file if there is none
    default_instructions = """You are a voice assistant for a smart speaker. Provide extremely concise responses suitable for speech. Aim for 1-3 short sentences max unless more detail is explicitly requested. Be direct and to the point. Prioritize brevity above all else in every response."""

    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            file.write(default_instructions)
    
    with open(file_path, 'r') as file:
        return file.read()

# Load instructions on startup
system_prompt = get_or_create_custom_instructions()

DEBUG = True

async def async_llm_model(user_input, model):
    try:
        with llm_response_condition:
            llm_response_queue.put(True)
            llm_response_condition.notify()

        messages = [{"role": "user", "content": user_input}]
        
        async with client.messages.stream(
            model=model,
            max_tokens=1000,
            temperature=0.4,
            system=system_prompt,
            messages=messages,
            tools=get_tools_for_claude()
        ) as stream:
            async for text in stream.text_stream:
                EventHandler().on_text(text)
                print(text, end="", flush=True)
        
        full_response = ""
        async for chunk in stream:
            if chunk.type == "content_block":
                if chunk.content_block.type == "text":
                    text = chunk.content_block.text
                    EventHandler().on_text(text)
                    full_response += text
                    print(text, end="", flush=True)
            elif chunk.type == "tool_calls":
                for tool_call in chunk.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments
                    tool_result = handle_tool_request(tool_name, tool_args)
                    tool_info = f"\nTool Call: {tool_name}, Result: {tool_result}\n"
                    EventHandler().on_text(tool_info)
                    full_response += tool_info
                    print(tool_info, end="", flush=True)

        llm_response_queue.put(False)
        return full_response
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        llm_response_queue.put(False)
        raise

def llm_model(user_input, model="claude-3-5-sonnet-20240620"):
    return asyncio.run(async_llm_model(user_input, model))
        
  
