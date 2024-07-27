from anthropic import AsyncAnthropic, APIError
import os
import json
import asyncio
from queue_handling import llm_response_queue, llm_response_condition
from centralized_tools import tools_for_claude, handle_tool_request, tools_list_for_claude, tools_bot_schema
from dont_tell import CLAUDE_KEY
  
# these models can be mixed and matched as needed
# they can call the others as needed
opus = "claude-3-opus-20240229" #high model
sonnet = "claude-3-5-sonnet-20240620" #mid model
haiku = "claude-3-haiku-20240307"  #low model

base_model = sonnet # default model

model_params = None
history_length = None
calling_model = None
full_readable_text = ""
role = "user"

# the base model is the default model the user 
# interacts with when they sau "hey claude",
# but any model can be called specificly.  
# the tools model handles all tool use
# the base_model calls the tool model when
# it wants use tools
    
client = AsyncAnthropic(api_key=CLAUDE_KEY)

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

def create_tools_list_prompt():
    return f"""Available tools: {', '.join(tools_list_for_claude)}. 
 
Use tools when necessary for accurate responses."""

# Generate both prompts
system_prompt = get_or_create_custom_instructions()
tools_list_prompt = create_tools_list_prompt()

async def claude_operations():
    global model_params, history_length, calling_model, full_readable_text, role

    try:  
        content = []
        tool_use_id = getattr(claude_operations, 'tool_use_id', None)
        tool_name = getattr(claude_operations, 'tool_name', None)
        tool_input = getattr(claude_operations, 'tool_input', None)
        result = getattr(claude_operations, 'result', None)
        print(f"fStart of claude_operations: tool_use_id={tool_use_id}")
        # construct the content block to append to history
        # content differs by weather it contains a tool block or not
        # not tool content is very straight forward

        if not tool_use_id:
            content = full_readable_text  
        else:
            # we first build the tool bloc
            # with lements common to tool use and response types
            # we then add elements unique to each type
            if role == "assistant":
                print("Creating assistant tool use block")
                # this is the agent's request to use the tool
                tool_block = {
                    "type": "tool_use",
                    "id": tool_use_id,
                    "name": tool_name,
                    "input": tool_input if isinstance(tool_input, dict) else {"value": tool_input} if tool_input is not None else {}
                }
                # some tools require user input, such as a web earch
                # others, such as a time check, do not
                # if there is no user input, please omit
                
            elif role == "user":
                print("Creating user tool result block")
                # this is the response from the tool
                # and is considered a user message
                tool_block = {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result
                }
             # we first build the tool bloc
            # with lements common to tool use and response types
            content = [tool_block]
            print(f"Final tool block: {tool_block}")
            # text to be read alloud is not necisary for tools
            # if is blank, omit it
            if full_readable_text and full_readable_text.strip():
                text_block = {
                    "type": "text",
                    "text": full_readable_text
                }
                content = [tool_block, text_block]
        print(f"calling model:  {calling_model}")
        print(f"Final content to be added to history: {content}")
        # Now handle history setup and append
        # each model has its own history
        model_history = f"{calling_model}_history"
        if not hasattr(claude_operations, model_history):
            setattr(claude_operations, model_history, [])
        current_history = getattr(claude_operations, model_history)
        current_history.append({"role": role, "content": content})
        print(f"Debug: Appended to history: {json.dumps(current_history[-1], indent=2)}")
        # Trim the history if it exceeds the specified length
        if len(current_history) > history_length * 2:  # *2 because each exchange is two messages
            current_history = current_history[-(history_length):]
            # print(f"Debug: History trimmed. New length: {len(current_history)}")
        
        accumulated_json = ""
        tool_name = None
        tool_input = { }
        setattr(claude_operations, 'tool_input', tool_input)
        tool_use_id = None
        setattr(claude_operations, 'tool_use_id', tool_use_id)
        streaming_text = None
        full_readable_text = None
        result = None
        full_readable_text = ""
        print(f"reset: {tool_use_id}")
        # print(f"API request payload: {json.dumps(model_params, indent=2)}")
        
        print("\n--- Full History ---")
        for idx, msg in enumerate(current_history):
            print(f"Message {idx}:")
            print(json.dumps(msg, indent=2))
        print("--- End of Full History ---\n")
            
        
        if role == 'user':
        # send to claude
            async with client.messages.stream(**model_params, messages=current_history) as stream:
                print("Entered message stream")
                # set variables here at the function level
                # to be reset after send to Claude
                
                # claude's response
                try:
                    async for event in stream:
                        # print(f"Received event: {event.type}")
                        # claude response beginning
                        if event.type == "content_block_start":
                            with llm_response_condition:
                                print("Putting True in queue (start streaming)")
                                llm_response_queue.put(True)
                                llm_response_condition.notify() 
                            if event.content_block.type == "tool_use":
                                # tool use id is asigned by the model
                                tool_use_id = event.content_block.id
                                setattr(claude_operations, 'tool_use_id', tool_use_id)
                                # tool name calls the tool
                                tool_name = event.content_block.name  
                                setattr(claude_operations, 'tool_name', tool_name)
                                #we wait to get tool input because we don't want tool name
                                # running off by itself if there is one.  
                                # print(f"Full tool use content block: {json.dumps(event.content_block.model_dump(), indent=2)}")
                                print(f"Tool use ID created: {tool_use_id}, Tool name: {tool_name}")
                        #claude response middle
                        elif event.type == "content_block_delta":
                            # this is the response as it streams in,
                            # to be read aloud ASAP
                            if event.delta.type == "text_delta":
                                # print(f"Received text: {event.delta.text}")
                                streaming_text = event.delta.text
                                if calling_model != "tools_bot": 
                                    with llm_response_condition:
                                        # print(f"Putting text chunk in queue: {streaming_text}")
                                        llm_response_queue.put(streaming_text)
                                        llm_response_condition.notify()
                                # the accumulated response will be appended to the history
                                full_readable_text += streaming_text
                            elif event.delta.type == "input_json_delta":
                                print(f"Tool input JSON: {event.delta.partial_json}")
                                #json indicates a tool input text
                                accumulated_json += event.delta.partial_json
                        # claude response end
                        elif event.type == "message_stop":
                            with llm_response_condition:
                                print("Putting False in queue (end streaming)")
                                llm_response_queue.put(False)
                                print(f"Message stop reason: {event.message.stop_reason}")
                            if event.message.stop_reason == "tool_use":
                                if accumulated_json:
                                    try:
                                        json_data = json.loads(accumulated_json)
                                        print(f"Parsed JSON data: {json.dumps(json_data, indent=2)}")
                                        # tool input is only needed for some tools
                                        # it is ok if there is no tool input,
                                        # but we want to be sure if there is or isn't
                                        # before calling the tool
                                        tool_input = next(iter(json_data.values()), None)
                                        setattr(claude_operations, 'tool_input', tool_input)
                                        print(f"Parsed tool input: {tool_input}")
                                    except json.JSONDecodeError:
                                        print(f"Failed to parse JSON: {accumulated_json}")
                        
                            # recall the current function here to add
                            # claude's response to history
                            role = "assistant"
                            print(f"is it none?: {tool_use_id}")
                            response_to_return = full_readable_text
                            # response tor return is stored for a moment so it is not cleared after history append
                            await claude_operations()
                            if calling_model == "tools_bot" and tool_use_id is None:
                                # responses from tools bot are returned to the calling
                                # function if they do not include a tool use id
                                full_readable_text = ""
                                return response_to_return
                            
                            print("After calling claude_operations")

                            # here we handle the tool call
                            # if there is a tool call, we call the tool,
                            # its response will be added to the history
                            # after claude's response
                            if tool_use_id is not None:
                                #tag the tool use id so we can track it and return it to the right place
                                tagged_tool_use_id = f"{calling_model}${tool_use_id}"
                                tool_request = {tool_name: tool_input}
                                tool_use_id = None
                                setattr(claude_operations, 'tool_use_id', tool_use_id)
                                print(f"Constructed tool request: {tool_request}")  
                                is_command_executed, result, tool_use_id = await handle_tool_request(tool_request, tagged_tool_use_id)
                                print(f"After handle_tool_request: executed={is_command_executed}, result='{result}', id={tool_use_id}")  
                                if is_command_executed:
                        
                                    # tool responses will arrive out of order
                                    # so the tool response set all the variables, replacing what was
                                    # set from claude's response, which have already
                                    # been logged to the history at this point.  

                                    # we split and remove the calling model
                                    # so the tool_use_id is as claude gave it
                                    return_model, tool_use_id = tool_use_id.split('$', 1)
                                    setattr(claude_operations, 'result', result)
                                    setattr(claude_operations, 'tool_use_id', tool_use_id)
                                    print(f"Tool use ID split: return_model={return_model}, tool_use_id={tool_use_id}")
                                    # we send the response to the model functions
                                    # so they are logged as user input
                                    if return_model == "base_model":
                                        await call_base_model()
                                    elif return_model == "tools_bot":
                                        tool_result_skips_tools_bot = False
                                        # when true, the tool result returns directly to the calling function
                                        # when false, it is first returned to tools bot, 
                                        # and the tools bot response is sent to the calling function
                                        if tool_result_skips_tools_bot:
                                            return result
                                        else: 
                                            return await call_tools_bot(result)
                                    else:
                                        raise ValueError(f"Invalid return model: {return_model}")
                    
                    print("Full Raw Response from Claude:")
                    print(json.dumps([event.model_dump() for event in full_raw_response], indent=2))

                except APIError as e:
                    print(f"An API error occurred: {e}")
                except Exception as e:
                    print(f"An unexpected error occurred: {e}")
                except asyncio.TimeoutError:
                    print("Stream processing timed out. Retrying...")
                except Exception as stream_error:
                    print(f"An error occurred during stream processing: {stream_error}")
                    return None
            
            return full_readable_text 
        
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise

async def call_tools_bot(incoming=None, incloming_tool_use_id=None):
    # requests for tools bot are routed through centeralized_tools/
    # this adds some complexity to the set up, but we do this 
    # to keep tool sorting logic centeralized, so it may
    # easily be called by various entities
    
    # the tool use ID in this function stores the use id from the calling function
    # a tool use id is not required. If there is incoming no tool use id argument,
    # we preserve the existing tool use id.  this helps us juggle multiple
    # tool use IDs.  The tool use id in this function is unique to this scope.
    
    # this is because each tool request has a unique id.  This helps us direct the response
    # from the tool.  Because tools bot itself is a tool, a unique ID is created when calling it, and again
    # when it calls a tool.  This function holds and returns the tool use id asigned when calling
    # tools bot.  The tool use ID for calling the actual tool is not returned to this function with its result.
    # This means the tool use id for this call is not over riden.  If the tool use ID for the actual tool 
    # call must be returned to Claude, it is stored in Claude operations.  We dont need it here.
    
    global model_params, history_length, calling_model, base_model, full_readable_text, role
    if incoming:
        full_readable_text = incoming
        incoming = None
    if incloming_tool_use_id:
        tool_use_id = incloming_tool_use_id
    print(f"Calling tools bot with input: {full_readable_text}, tool_use_id: {tool_use_id}")
    calling_model = "tools_bot"
    role = "user"
    history_length = 2 # (1 = 2 messaages: 1 user and 1 assistant) 
    model_params = {
        "model": haiku,
        "max_tokens": 1000,
        "temperature": 0.0,
        "system": "You are a tool-focused assistant. Your role is to determine when to use tools and how to use them effectively. Return their results carefully",
        "tools": tools_for_claude,
        "tool_choice": {"type": "auto"}
    }
    result = await claude_operations()
    return result, tool_use_id

async def call_base_model():
    global model_params, history_length, calling_model, base_model, role
    calling_model = "base_model"
    role = "user"
    history_length = 5 # number of user / assistantant exchanges
    model_params = {
        "model": base_model,
        "max_tokens": 1000,
        "temperature": 0.4,
        "system": f"{system_prompt}\n\n{tools_list_prompt}",
        "tools": [tools_bot_schema],
        "tool_choice": {"type": "auto"}
    }
    print(f"call_base_model received: {full_readable_text}")  
    return await claude_operations()

# tools base model combined for testing

# async def call_base_model():
#     global model_params, history_length, calling_model, base_model, role
#     calling_model = "base_model"
#     role = "user"
#     history_length = 5 # number of user / assistantant exchanges
#     model_params = {
#         "model": base_model,
#         "max_tokens": 1000,
#         "temperature": 0.0,
#         "system": f"{system_prompt}\n\n{tools_list_prompt}",
#         "tools": tools_for_claude,
#         "tool_choice": {"type": "auto"}
#     }
#     print(f"call_base_model received: {full_readable_text}")  
#     return await claude_operations()

# llm_model is the standard model name called by llm_operations.
# it makes the llm modules easily swappable. In this case,
# llm model calls the async def to take care of business on its behalf
# asyncronously  

def llm_model(input_content):
    async def async_llm_model():
        global base_model, full_readable_text
        full_readable_text = input_content
        print(f"llm_model received: {full_readable_text}")  
        return await call_base_model()
    return asyncio.run(async_llm_model())

def shutdown():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.stop()
        if not loop.is_closed():
            loop.close()
    except Exception as e:
        print(f"Error during shutdown: {e}")

# Shutdown function to close the event loop
def shutdown():
    loop.close()