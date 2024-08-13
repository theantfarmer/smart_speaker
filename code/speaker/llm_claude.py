import os
import re
import json
import asyncio
import logging
import threading
from anthropic import AsyncAnthropic, APIError, APIStatusError
from queue_handling import llm_response_queue, llm_response_condition, tool_response_to_llm_claude_queue, tool_response_to_llm_claude_condition
from centralized_tools import tools_for_claude, handle_tool_request, handle_tool_response, tools_list_for_claude, tools_bot_schema
from dont_tell import CLAUDE_KEY
import traceback

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.debug(f"Module initialization. Main thread: {threading.current_thread().name}")
logger.debug(f"Initial event loop: {id(asyncio.get_event_loop())}")

def log_call_stack():
    stack = traceback.extract_stack()
    logger.debug("Current call stack:\n" + "".join(traceback.format_list(stack)))

  
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
  
# this is a complex system to experiment with multiple bots. 
# I built this to experiment with using different sized models for different tasks
# and having them work together.  

# the base model is the default model the user 
# interacts with when they sau "hey claude",
# but any model can be called specificly.  

# the tools bot is an experimental model that handles tool use
# Tools bot is a tool itself and can be called 
# anywhere else in the system
# the base_model calls the tool model when
# it wants use tools

# this was also put in place to reduce token usage
# by not sending full schemas for each tool on every call.  
  
# models can be mixed and matched as needed
# they can call the others as needed
opus = "claude-3-opus-20240229" #high model
sonnet = "claude-3-5-sonnet-20240620" #mid model
haiku = "claude-3-haiku-20240307"  #low model

base_model = sonnet # default model

model_params = None
history_length = None
calling_model = None
tool_name = None
tool_use_id = None
tool_input = { }
if_tool_use = None
full_readable_text = ""
role = "user"
result = None
    
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
            file.write("""You are a voice assistant for a smart speaker. Your primary goal is to provide extremely concise and helpful responses to user queries. Follow these key principles:

1. Limit spoken responses to 1-3 short sentences unless more detail is explicitly requested.
2. Use available tools immediately when needed without explanation.
3. Address the user directly in your spoken responses.
4. Prioritize brevity in all interactions.

When you receive a user query, process it as follows:

1. If the query requires using a tool, use it immediately without explanation.
2. For complex queries, use <thinking></thinking> tags to show your reasoning process. This won't be spoken aloud.
3. If the request is unclear, consider potential transcription errors and try to interpret the most likely intent.
4. If there's a problem you can't resolve, state it briefly and shut the hell up.  

Format your response like this:
<thinking>Your internal reasoning process (if needed) which the user will not hear.  Use this space to think and reason.</thinking>
Your spoken response to the user (1-3 short sentences).  This is the only part the user receives.

Remember:
- Don't explain tool usage or offer examples.
- Don't use unnecessary pleasantries or elaborate explanations.
- Don't tell the user what you are going to do.  Just do it.
- If there is a problem, say so briefly, then shut the hell up.  
- If more detail is explicitly requested, provide it concisely.
""")
    
    with open(file_path, 'r') as file:
        return file.read()
    
    
# Add this near the top of the file, with the other global variables and constants

tools_bot_prompt = """You are a tool-focused AI assistant. Your primary role is to determine when and how to use tools effectively to assist users with their queries. You only have access to the tools listed below and no others. Always consider using these tools when appropriate to provide accurate and helpful responses.

Here are the tools available to you:

Guidelines for using tools:
1. Carefully read the user's input to determine if a tool is necessary.
2. If a tool is needed, select the most appropriate one from the available list.
3. Use tools only when they can provide relevant information to answer the user's query.
5. Always interpret and explain the results of tool calls in your response.

When responding to the user:
1. If you use any tools, include your thought process in <thinking> tags before making the tool call.
2. Provide your final answer to the user's query.

Remember, you can only use the tools provided to you. Do not assume you have access to any other capabilities or information sources.
"""
    
def create_tools_list_prompt():
    return f"""Available tools: {', '.join(tools_list_for_claude)}. 
 
Use tools when necessary for accurate responses."""

# Generate both prompts
system_prompt = get_or_create_custom_instructions()
tools_list_prompt = create_tools_list_prompt()


async def history_maker():
    global model_params, history_length, calling_model, full_readable_text, role, tool_name, tool_use_id, tool_input, result
    print(f"Entering history_maker, role: {role}")
    print(f" history_maker if tool use {if_tool_use}")
    print(f" history_maker result {result}")
    # here we prepare messages to appened to history and send to Claude
    # this is centeralized for all models, user roles, and tool and non-tool

    try:  
        content = []
        print(f"fStart of history_maker: tool_use_id={tool_use_id}")
        # construct the content block to append to history
        # content differs by weather it contains a tool block or not
        # not tool content is very straight forward

        if not tool_use_id:
            print(f"if not tool_use_id:")
            if not isinstance(full_readable_text, str):
                content = json.dumps(full_readable_text)
            else:
                content = full_readable_text
        else:
            if '$' in tool_use_id:
                # we split and remove the calling model
                # so the tool_use_id is as claude gave it
                return_model, tool_use_id = tool_use_id.split('$', 1)
                setattr(history_maker, 'tool_use_id', tool_use_id)
            # we build the tool bloc
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
            # text to be read alloud is not necisary for tools
            # if is blank, omit it
            if full_readable_text and full_readable_text.strip():
                text_block = {
                    "type": "text",
                    "text": full_readable_text
                }
                content = [tool_block, text_block]
        print(f"calling model:  {calling_model}")
        # print(f"Final content to be added to history: {content}")
        # Now handle history setup and append
        # each model has its own history
        model_history = f"{calling_model}_history"
        if not hasattr(history_maker, model_history):
            setattr(history_maker, model_history, [])
        current_history = getattr(history_maker, model_history)
        current_history.append({"role": role, "content": content})
        # print(f"Debug: Appended to history: {json.dumps(current_history[-1], indent=2)}")
        # Trim the history if it exceeds the specified length
        if len(current_history) > history_length * 2:  # *2 because each exchange is two messages
            current_history = current_history[-(history_length):]
            # print(f"Debug: History trimmed. New length: {len(current_history)}")
        
        result = None
        full_readable_text = ""
       
        # print(f"API request payload: {json.dumps(model_params, indent=2)}")
        print("\n--- Full History ---")
        for idx, msg in enumerate(current_history):
            print(f"Message {idx}:")
            print(json.dumps(msg, indent=2))
        print("--- End of Full History ---\n")
            
        if role == 'user':
        # send to claude
            try:
                async with client.messages.stream(**model_params, messages=current_history) as stream:
                    logger.debug("Stream connection opened")
                    await handle_claude_response(stream)
            except Exception as e:
                logger.exception(f"Exception in history_maker: {e}")
                raise
            finally:
                logger.debug(f"Exiting history_maker. Event loop: {id(asyncio.get_running_loop())}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print(f"outter Exception occurred: {type(e).__name__}, {str(e)}")
        raise
                
async def handle_claude_response(stream):
    global full_readable_text, tool_name, tool_use_id, tool_input, role, calling_model, if_tool_use
    # here we pick apart claude's response
    print(f"inside handle_claude_respons")
    print(f"if_tool_use handle_claude_response: {if_tool_use}")
    tool_use_id = None
    tagged_tool_use_id = None
    accumulated_json = ""

    logger.debug("Stream connection opened")
    # claude's response
    try:
        response_to_return = None 
        async for event in stream:     
            # claude response beginning
            if event.type == "content_block_start":
                with llm_response_condition:
                    llm_response_queue.put(True)
                    llm_response_condition.notify() 
                if event.content_block.type == "tool_use":
                    # tool use id is asigned by the model
                    tool_use_id = event.content_block.id
                    tagged_tool_use_id = f"llm_claude_{calling_model}${tool_use_id}"
                    setattr(history_maker, 'tool_use_id', tool_use_id)
                    # tool name calls the tool
                    tool_name = event.content_block.name  
                    setattr(history_maker, 'tool_name', tool_name)
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
                    if not if_tool_use: 
                        with llm_response_condition:
                            # print(f"Putting text chunk in queue: {streaming_text}")
                            llm_response_queue.put(streaming_text)
                            llm_response_condition.notify()
                    # the accumulated response will be appended to the history
                    full_readable_text += streaming_text
                elif event.delta.type == "input_json_delta":
                    # print(f"Tool input JSON: {event.delta.partial_json}")
                    #json indicates a tool input text
                    accumulated_json += event.delta.partial_json
            # claude response end
            elif event.type == "message_stop":
                # print(f"Message stop event, stop_reason: {event.message.stop_reason}")
                with llm_response_condition:
                    # print("Putting False in queue (end streaming)")
                    llm_response_queue.put(False)
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
                            setattr(history_maker, 'tool_input', tool_input)
                            print(f"Parsed tool input: {tool_input}")
                        except json.JSONDecodeError:
                            print(f"Failed to parse JSON: {accumulated_json}")
                full_text_as_tool_response = re.sub(r'<thinking>.*?</thinking>', '', full_readable_text, flags=re.DOTALL).strip()
                # recall the current function here to add
                # claude's response to history
                role = "assistant"
                # response tor return is stored for a moment so it is not cleared after history append
                await history_maker() # to append to history
                tool_use_id = None
                
                
                if tagged_tool_use_id is not None:
                    print(f"Calling handle_tool_request with tagged_tool_use_id={tagged_tool_use_id}, tool_name={if_tool_use}, tool_input= {tool_input}, if tool use= {if_tool_use}")
                    await handle_tool_request(tagged_tool_use_id, tool_name, tool_input, if_tool_use)
                else:
                    if if_tool_use:
                        print(f"that was atool response.  calling handle tool response with tagged_tool_use_id={tagged_tool_use_id}, tool_name={if_tool_use}, tool_input= {full_text_as_tool_response}, if tool use= {if_tool_use}")
                        await handle_tool_response(full_text_as_tool_response, if_tool_use)
                tool_name = None
                tool_input = { }
                full_text_as_tool_response = ""
                
    except APIError as e:
        error_message = f"I'm sorry. Anthropic's servers are currently bullocks."
        
    except Exception as e:
        print(f"An unexpected error occurred.")
        logger.exception("Error during stream processing")
        error_message = "There is a problem with the code."

    if 'error_message' in locals():
        with llm_response_condition:
            llm_response_queue.put(error_message)
            llm_response_condition.notify()
        await remove_last_user_message()
 
async def call_tools_bot(incoming_text=None, incoming_if_tool_use=None):
   
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
    
    global model_params, history_length, calling_model, full_readable_text, if_tool_use, role
 
    if incoming_text:
        full_readable_text = incoming_text
        incoming_text = None  
    if incoming_if_tool_use:
        if_tool_use = incoming_if_tool_use
        incoming_if_tool_use = None
    
    calling_model = "tools_bot"
    role = "user"
    history_length = 5 # (1 = 2 messaages: 1 user and 1 assistant) 
    model_params = {
        "model": haiku,
        "max_tokens": 1000,
        "temperature": 0.0,
        "system": tools_bot_prompt,
        "tools": tools_for_claude,
        "tool_choice": {"type": "auto"}
    }
    print(f"About to call history_maker in call_tools_bot")
    await history_maker()
    

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
    await history_maker()
    
    
# combined tools/base model for testing:

# async def call_base_model(incoming_text=None, if_tool_use=None):
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
#     return await history_maker()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
logger.debug(f"Initial event loop created: {id(loop)}")


async def tool_response_listener(received_tool_use_id, received_result, received_if_tool_use):
    global tool_use_id, result, if_tool_use
    
    tool_use_id = received_tool_use_id
    result = received_result
    if_tool_use = received_if_tool_use
    print(f"tool_response_listener: {if_tool_use}")
    print(f"tool_response_listener result: {result}")
    
    try:
        if tool_use_id.startswith("llm_claude_base_model"):
            print("Received base_model response. Calling call_base_model.")
            await call_base_model()
        elif tool_use_id.startswith("llm_claude_tools_bot"):
            print("Received tools_bot response. Calling call_tools_bot.")
            await call_tools_bot()
    except asyncio.TimeoutError:
        print(f"Timeout waiting for tool response")
    except Exception as e:
        logger.exception(f"Exception in tool_response_listener: {e}")   
        
# llm_model is the standard model name called by llm_operations.
# it makes the llm modules easily swappable. In this case,
# llm model calls the async def to take care of business on its behalf
# asyncronously  

def llm_model(input_content):
    global loop, base_model, full_readable_text
    logger.debug(f"Entering llm_model. Current event loop status: {loop.is_closed()}")
    logger.debug(f"Current thread: {threading.current_thread().name}")
    log_call_stack()

    # if loop.is_closed():
    #     logger.warning("Event loop is closed. Creating a new one.")
    #     loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(loop)
        
    if isinstance(input_content, dict):
        claude_key = next(key for key in input_content if key.startswith("chat_with_llm_claude"))
        input_content = input_content[claude_key]
        if "_opus" in claude_key:
            base_model = opus
        elif "_sonnet" in claude_key:
            base_model = sonnet
        elif "_haiku" in claude_key:
            base_model = haiku
    full_readable_text = input_content
    try:
        loop.run_until_complete(call_base_model())
    except Exception as e:
        logger.exception(f"Exception in llm_model: {e}")
        raise
    finally:
        logger.debug(f"Exiting llm_model. Event loop status: {loop.is_closed()}")
        
# when there is a serever error, we must remove the last user message
# because the history must alternate between user/assistant
# and the error interrupts this
async def remove_last_user_message():
    global calling_model
    model_history = f"{calling_model}_history"
    current_history = getattr(history_maker, model_history, [])
    if current_history and current_history[-1]['role'] == 'user':
        current_history.pop()
    setattr(history_maker, model_history, current_history)

def shutdown():
    global loop
    try:
        if loop.is_running():
            loop.stop()
        pending = asyncio.all_tasks(loop=loop)
        loop.run_until_complete(asyncio.gather(*pending))
        loop.close()
    except Exception as e:
        print(f"Error during shutdown: {e}")