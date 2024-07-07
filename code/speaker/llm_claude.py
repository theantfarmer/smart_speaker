from anthropic import AsyncAnthropic
import os
import json
import asyncio
from queue_handling import llm_response_queue, llm_response_condition
from centralized_tools import tools_for_claude, handle_tool_request
from dont_tell import CLAUDE_KEY

client = AsyncAnthropic(api_key=CLAUDE_KEY)

class EventHandler:
    def on_text(self, text: str):
        llm_response_queue.put(text)

def get_or_create_custom_instructions():
    file_path = 'claude_custom_instructions.txt'
    # custom instructions are set in the file mentioned above.
    # use them to shape the voice and store persistant info about the user
    # they are meant to be private and personal, so we create a fresh file
    # when you first run the the program.
    # the default instructions below are for the fresh file.
    # NOTE:  Editing the default instructions below will not
    # alter model behavior.  You must change them in the file mentioned above.
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            file.write("""You are a voice assistant for a smart speaker. Provide extremely concise responses suitable for speech. Aim for 1-3 short sentences max unless more detail is explicitly requested. Be direct and to the point. Prioritize brevity above all else in every response.""")
    
    with open(file_path, 'r') as file:
        return file.read()

# Load instructions on startup
system_prompt = get_or_create_custom_instructions()

async def async_llm_model(user_input):
    
    # these models can be mixed and matched as needed
    # they can call the others as needed
    # set the base model for default claude model
    opus = "claude-3-opus-20240229" #high model
    sonnet = "claude-3-5-sonnet-20240620" #mid model
    haiku = "claude-3-haiku-20240307"  #low model
    base_model=haiku
    
    try:
        with llm_response_condition:
            llm_response_queue.put(True)
            llm_response_condition.notify()
        
        messages = [{"role": "user", "content": user_input}]
   
        full_response = ""
        tool_calls = []

        async def stream_process(messages):
            accumulated_json = ""
            tool_name = None
            tool_input = None 
            nonlocal full_response, tool_calls
            async with client.messages.stream(
                model=base_model,
                max_tokens=1000,
                temperature=0.4,
                system=system_prompt,
                messages=messages,
                tools=tools_for_claude,
                tool_choice={"type": "auto"}
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            tool_name = event.content_block.name

                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            # Handle text responses 
                            text = event.delta.text
                            llm_response_queue.put(text)
                            full_response += text
                        elif event.delta.type == "input_json_delta":
                            # Accumulate JSON for complex tools
                            accumulated_json += event.delta.partial_json

                    elif event.type == "message_stop" and event.message.stop_reason == "tool_use":
                        if accumulated_json:
                            # Handle complex tool (JSON-based)
                            try:
                                json_data = json.loads(accumulated_json)
                                tool_input = next(iter(json_data.values()), None)
                            except json.JSONDecodeError:
                                print(f"Failed to parse JSON: {accumulated_json}")
          
                        tool_request = {tool_input: tool_name} if tool_input else tool_name
                        is_command_executed, result = await handle_tool_request(tool_request)
                       
                        # Return result to Claude 
                        if is_command_executed:
                            # two messages to alter nateuser / agent
                            messages.append({"role": "assistant", "content": f"I used the {tool_name} tool."})
                            messages.append({"role": "user", "content": f"Tool '{tool_name}' result: {result}"})
                            return await stream_process(messages)
                       
                        accumulated_json = ""
                        tool_name = None

        await stream_process(messages)

        print(f"Full response: {full_response}")
        return full_response

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise


# Global event loop
loop = asyncio.get_event_loop()

# llm_model is the standard model name called by llm_operations.
# it makes the llm modules easily swappable. In this case,
# llm model calls the async def to take care of business on its behalf
# asyncronously  
def llm_model(user_input):
    return loop.run_until_complete(async_llm_model(user_input))

# Shutdown function to close the event loop
def shutdown():
    loop.close()