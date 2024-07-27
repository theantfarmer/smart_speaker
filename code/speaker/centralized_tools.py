from datetime import datetime
import holidays
import ephem
from transit_routes import fetch_subway_status, train_status_phrase, SUBWAY_LINES

# tools_bot_request_id = None #holds persistant request ID between iterations  

# these are centeralized tools that are shared by LLMs and the system.
# new tools added here will automaticlly be available to all entities
# that use this module.  Sentence triggers will automaticlly be added
# to command wake words unless excuded from the system.  

# each tool is executed when handle_tool_request recieves a tool_name.  
# some tools, such as time or date, require only a tool a tool_name to return.
# Others, like web search, need tool_input as well.  

# add extra trigger sentences to account for common transcription mistakes

# We make a lot of lists, such as all available tools, and dictionaries
# to map trigger sentences to tool names.  

# Some entities that use these tools requires a customized list.  Claude
# for example, requires a list of schemas.  This module is designed so
# costomized schema lists can easily be constructed.  

# tools that require tool_input are suitable for function wake words,
# allowing the user to address the tool directly.  
# To add a tool to function_wake_words, open the main and wake words modules
# and copy the convention of direct chatgpt calls.  

# Items may be excluded from AI to save tokens or from the sysem if they 
# require AI, or for any other reason. Items excluded from the system 
# will not recieve command wake words or be callable from the default system,
# but will be available to chatgpt and claude by default.
# Exclude items from the system that require AI.



# in aplphabetical order 
tools = {
    
    "get_date": {
    "name": "get_date",
    "description": "Get the current date from user system.",
    "notes": "",
    "exclude_from_system": False,
    "exclude_from_claude": False,
    "exclude_from_gpt": False,
    "type": "object",
    "properties": {},
    "required": [],
    "trigger_sentences": [
        "date",
        "what date is it",
        "what date is it today",
        "can you tell me what date it is",
        "what is the date",
        "what's the date"
    ],
    "has_sublist": False,
},
    
    "get_day_of_week": {
    "name": "get_day_of_week",
    "description": "Get the day of the week for a specific date.",
    "notes": "",
    "exclude_from_system": False,
    "exclude_from_claude": False,
    "exclude_from_gpt": False,
    "type": "object", 
    "properties": {
        "date_text": {
            "type": "string",
            "description": "The date to get the day of the week for, in the format 'MM/DD' or as a holiday name (e.g., '12/25' or 'Christmas')."
        }
    },
    "required": ["date_text"],
    "trigger_sentences": [
        "what day of the week is [date]",
        "what weekday is [date]",
        "what day is [date]",
        "which day of the week is [date]",
        "when is [date]"
    ],
    "has_sublist": False,
},
    
    "get_holiday_date": {
        "name": "get_holiday_date",
        "description": "Get the date of a specific holiday, the next upcoming holiday, or the holiday on a given date.",
        "notes": "",
        "exclude_from_system": False,
        "exclude_from_claude": False,
        "exclude_from_gpt": False,
        "type": "object",
        "properties": {
            "holiday_name": {
                "type": "string",
                "description": "The name of the holiday to get the date for (e.g., 'Memorial Day'). If not provided, returns the next upcoming holiday."
            },
            "date": {
                "type": "string",
                "description": "The date to check for a holiday, in the format 'MM/DD'."
            }
        },
        "required": [],
        "trigger_sentences": [
            "when is [holiday]",
            "what day is [holiday]",
            "when is the next holiday",
            "what is the next holiday",
            "what's the date of [holiday]",
            "what date is [holiday]",
            "when's [holiday]",
            "what holiday is on [date]"
        ],
        "has_sublist": False,
    },
    
    "get_time": {
        "name": "get_time",
        "description": "Get the current time from user system.",
        "notes": "",
        "exclude_from_system": False,
        "exclude_from_claude": False,
        "exclude_from_gpt": False,
        "type": "object",
        "properties": {},
        "required": [],
        "trigger_sentences": [
            "time", "what time is it",
            "what time is it now", "can you tell me what time it is",
            "what is the time", "whats the time"
        ],
        "has_sublist": False,
    },
    "get_moon_phase": {
        "name": "get_moon_phase",
        "description": "Get the current phase of the moon.",
        "notes": "",
        "exclude_from_system": False,
        "exclude_from_claude": True,
        "exclude_from_gpt": True,
        "type": "object",
        "properties": {},
        "required": [],
        "trigger_sentences": [
            "what phase is the moon",
            "what's the moon phase",
            "what is the moon phase",
            "what is the phase of the moon",
            "what is the current phase of the moon",
            "current moon phase",
            "what face is the moon",
            "what's the moon face",
            "what is the moon face",
            "what is the face of the moon",
            "what is the current face of the moon",
            "current moon phase",
            "moon phase",
            "moonphase",
            "moon face",
            "moonface"
        ],
        "has_sublist": False
    }, 
       
    "nyc_subway_status": {
        "name": "nyc_subway_status",
        "description": "NYC transit line check",
        "notes": "",
        "exclude_from_system": False,
        "exclude_from_claude": False,
        "exclude_from_gpt": False,
        "type": "object",
        "properties": {
            "train_line": {
                "type": "string",
                "description": "secify subway line"
            }
        },
        "required": ["train_line"],
        "trigger_sentences": [
            "Is the [mta-line] running",
            "Is the [mta-line] train running",
            "Is the [mta-line]train running",
            "Is the [mta-line]-train running",
            "Its the [mta-line] running",
            "Its the [mta-line] train running",
            "Its the [mta-line]train running",
            "Its the [mta-line]-train running",
            "this is the [mta-line] running",
            "this is the [mta-line] train running",
            "this is the [mta-line]train running",
            "this is the [mta-line]-train running",
            "how is the [mta-line] train",
            "how is the [mta-line]train",
            "how is the [mta-line]-train",
            "how is the [mta-line] train today",
            "how is the [mta-line]train today",
            "how is the [mta-line]-train today",
            "Whats the status of the [mta-line] train",
            "Can you check if the [mta-line] is on schedule",
            "Is there any delay on the [mta-line] line",
            "Hows the [mta-line] line doing",
            "Are there any issues with the [mta-line] today",
            "Is the [mta-line] operating normally",
            "Whats up with the [mta-line] line",
            "Is the [mta-line] delayed",
            "Any service changes for the [mta-line]",
            "Is the [mta-line] running on time",
            "Status of the [mta-line]",
            "[mta-line] train status",
            "Is the [mta-line] running today",
            "Are there any alerts for the [mta-line]",
            "[mta-line] line",
            "[mta-line]line",
            "[mta-line]-line",
            "[mta-line] train",
            "[mta-line]train",
            "[mta-line]-train",
        ],
        "has_sublist": True,
    }, 
   
    "tools_bot": {
        "name": "tools_bot",
        "description": "Use tool model to call tools and recieve results.",
        "notes": "",
        "exclude_from_claude": True,
        "type": "object",
        "properties": {
            "tool_input": {
                "type": "string",
                "description": "To use a tool, submit dict (tool_name : query_string)."
            }
        },
        "required": ["tool_input"],
        "trigger_sentences": [
            "use tool model",
            "process with tool model",
            "run tool model"
        ],
        "has_sublist": False,
    }
    }


def list_maker():
    mta_trigger_sentences = []
    subway_query_dict = {}
    tool_commands_list = []
    tool_names_list = []
    tool_commands_map_dict = {}
    list_of_available_tools = []
    tools_for_claude = []
    
    # Process MTA subway status tool
    mta_tool = tools["nyc_subway_status"]
    base_sentences = mta_tool["trigger_sentences"]

    for line in SUBWAY_LINES:
        for sentence in base_sentences:
            expanded_sentence = sentence.replace("[mta-line]", line).lower()  
            mta_trigger_sentences.append(expanded_sentence)
            subway_query_dict[expanded_sentence] = line
            tool_commands_list.append(expanded_sentence)
            tool_commands_map_dict[expanded_sentence] = "nyc_subway_status"

    for tool_name, tool in tools.items():
        list_of_available_tools.append(tool_name.lower())  
        if not tool["has_sublist"]:
            for sentence in tool["trigger_sentences"]:
                lowercased_sentence = sentence.lower()  
                tool_commands_list.append(lowercased_sentence)
                tool_names_list.append(tool_name.lower())
                tool_commands_map_dict[lowercased_sentence] = tool_name.lower()

        # Create minimal schema for LLMs
        # specialize lists for dif uses
    tools_for_claude = []
    tools_list_for_claude = []
    tools_bot_schema = None
    
    for tool_name, tool in tools.items():
        build_schema = {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": {
                "type": "object",
                "properties": tool["properties"],
                "required": tool["required"]
            }
        }
        
        if not tool.get("exclude_from_claude", False):
            tools_for_claude.append(build_schema)
            tools_list_for_claude.append(tool["name"])
        
        if tool["name"] == "tools_bot":
            tools_bot_schema = build_schema
          
    return (
        tools_bot_schema,
        list_of_available_tools,
        mta_trigger_sentences,
        subway_query_dict,
        tool_commands_list,
        tool_commands_map_dict,
        tool_names_list,
        tools_for_claude,
        tools_list_for_claude
    )

# Generate the lists when the module is imported
(
    tools_bot_schema,
    list_of_available_tools,
    mta_trigger_sentences,
    subway_query_dict,
    tool_commands_list,
    tool_commands_map_dict,
    tool_names_list,
    tools_for_claude,
    tools_list_for_claude
) = list_maker()
__all__ = ['tools_bot_schema']

async def handle_tool_request(input_data, tool_use_id):
        
    # When using tools bot to handle tools calls.
    # set to True to return tool results directlty 
    # to the original caller.  Set to false to return the
    # results to tools bot first.  

    print(f"handle_tool_request received: input_data={input_data}, tool_use_id={tool_use_id}")
    
    # # Initialize the tool request tracking list if it doesn't exist
    # if not hasattr(handle_tool_request, 'tool_request_list'):
    #     handle_tool_request.tool_request_list = []
    
    if isinstance(input_data, dict):
        tool_name = next(iter(input_data.keys()))
        tool_input = input_data[tool_name]
    else:
        tool_name = input_data
        tool_input = None
    print(f"Parsed tool request: tool_name={tool_name}, tool_input={tool_input}")

    # # Add the tool request to the tracking list
    # tool_request = {
    #     'tool_name': tool_name
    # }
    # # Only add tool_use_id and tool_input if they exist
    # if tool_use_id is not None:
    #     tool_request['tool_use_id'] = tool_use_id
    # if tool_input is not None:
    #     tool_request['tool_input'] = tool_input
    # handle_tool_request.tool_request_list.append(tool_request)
    # print(f"Added tool request to tracking list: {tool_request}")

    is_command_executed = True
    tool_response = None
  
    if tool_name == "get_date":
        current_date = datetime.now()
        date_string = current_date.strftime("%A, %B %d, %Y")     
        us_holidays = holidays.US()
        if current_date.date() in us_holidays:
            holiday_name = us_holidays[current_date.date()]
            tool_response = f"Today is {date_string}. Today is {holiday_name}."
        else:
            tool_response = f"Today is {date_string}."
            
    elif tool_name == "get_day_of_week":
        date_text = tool_input["date_text"]
        
        # Try parsing the date as MM/DD
        try:
            date = datetime.strptime(date_text, "%m/%d").date()
            date = date.replace(year=datetime.now().year)
        except ValueError:
            # If parsing fails, try to find the date of a holiday
            date = None
            for holiday_date, holiday_name in holidays.US(years=datetime.now().year).items():
                if date_text.lower() in holiday_name.lower():
                    date = holiday_date
                    break

            if not date:
                tool_response = f"Could not find a date for '{date_text}'."

        if date:
            day_of_week = date.strftime("%A")
            tool_response = f"{date_text} is on a {day_of_week}."
            
    elif tool_name == "get_holiday_date":
        holiday_name = tool_input.get("holiday_name") if tool_input else None
        date_str = tool_input.get("date") if tool_input else None
        
        current_year = datetime.now().year
        us_holidays = holidays.US(years=current_year)
        
        if date_str:
            # Get holiday on a specific date
            date = datetime.strptime(date_str, "%m/%d").date()
            date = date.replace(year=current_year)
            holiday = us_holidays.get(date)
            if holiday:
                tool_response = f"{holiday} falls on {date.strftime('%m/%d')} this year."
            else:
                tool_response = f"There is no holiday on {date.strftime('%m/%d')} this year."
        
        elif holiday_name:
            # Get the date for a specific holiday
            for date, name in us_holidays.items():
                if holiday_name.lower() in name.lower():
                    tool_response = f"{name} falls on {date.strftime('%A, %B %d')} this year."
                    break
            else:
                tool_response = f"Could not find a holiday named '{holiday_name}'."
        
        else:
            # Get the next upcoming holiday
            today = datetime.now().date()
            for date, name in sorted(us_holidays.items()):
                if date > today:
                    tool_response = f"The next holiday is {name} on {date.strftime('%A, %B %d')}."
                    break
            else:
                tool_response = "LOL.  Holidays."
            
    elif tool_name == "get_moon_phase":
        moon_phase_num = ephem.Moon(datetime.now()).phase
        if 0 <= moon_phase_num < 7.4:
            moon_phase = "New Moon"
        elif 7.4 <= moon_phase_num < 14.8:
            moon_phase = "First Quarter"
        elif 14.8 <= moon_phase_num < 22.1:
            moon_phase = "Full Moon"
        else:
            moon_phase = "Last Quarter"
        tool_response = f'The moon phase today is {moon_phase}.'
        
                    
    elif tool_name == "get_time":
        current_time = datetime.now().strftime("%I:%M %p")
        tool_response = f"The current time is {current_time}"

    elif tool_name == "nyc_subway_status":
        print(f"Processing NYC subway status. User input: {tool_input}")
        if tool_input in subway_query_dict:
            print(f"User input found in subway_query_dict")
            try:
                train_line = subway_query_dict[tool_input]
                print(f"Train line extracted from subway_query_dict: {train_line}")
            except KeyError:
                train_line = tool_input.upper()
                print(f"KeyError occurred. Using uppercased user input as train line: {train_line}")
            print(f"Checking if {train_line} is in SUBWAY_LINES")
        if tool_input in SUBWAY_LINES:  
            status = fetch_subway_status(tool_input)
            tool_response = train_status_phrase(tool_input, status)
        else:
            is_command_executed = False
            tool_response = f"Invalid subway line: {tool_input}"
    
    elif tool_name == "tools_bot":
        print(f"inside tools bot handle tools: tool input={tool_input}, tool_use_id={tool_use_id}")
        if tool_input:
            from llm_claude import call_tools_bot
            tool_response, tool_use_id = await call_tools_bot(tool_input, tool_use_id)
            print(f"handle_tool_request received from call_tools_bot: {tool_response}")
            is_command_executed = True
        else:
            tool_response = "No input provided for tools bot."
            is_command_executed = False


        
    else:
        is_command_executed = False
        tool_response = f"Unknown tool: {tool_name}"

    print(f"handle_tool_request returning: {is_command_executed}, {tool_response}, {tool_use_id}")
    return is_command_executed, tool_response, tool_use_id
