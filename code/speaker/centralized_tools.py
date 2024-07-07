from datetime import datetime
import holidays
import ephem
from transit_routes import fetch_subway_status, train_status_phrase, SUBWAY_LINES

# these are centeralized tools that are shared by LLMs and the system.
# new tools added here will automaticlly be available to all entities
# that use this module.  Sentence triggers will automaticlly be added
# to command wake words unless excuded from the system.  

# each tool is executed when handle_tool_request recieves a tool_name.  
# some tools, such as time or date, require only a tool a tool_name to return.
# Others, like web search, need user_input as well.  

# add extra trigger sentences to account for common transcription mistakes

# We make a lot of lists, such as all available tools, and dictionaries
# to map trigger sentences to tool names.  

# Some entities that use these tools requires a customized list.  Claude
# for example, requires a list of schemas.  This module is designed so
# costomized schema lists can easily be constructed.  

# tools that require user_input are suitable for function wake words,
# allowing the user to address the tool directly.  
# To add a tool to function_wake_words, open the main and wake words modules
# and copy the convention of direct chatgpt calls.  

# Items may be excluded from AI to save tokens or from the sysem if they 
# require AI, or for any other reason. Items excluded from the system 
# will not recieve command wake words or be callable from the default system,
# but will be available to chatgpt and claude by default.
# Exclude items from the system that require AI.




tools = {
    "get_current_time": {
        "name": "get_current_time",
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
        "has_sublist": False,
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

        # Create minimal schema for Claude
        if not tool["exclude_from_claude"]:
            claude_tool_schema = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": {
                    "type": "object",
                    "properties": tool["properties"],
                    "required": tool["required"]
                }
            }
            tools_for_claude.append(claude_tool_schema)

    return mta_trigger_sentences, subway_query_dict, tool_commands_list, tool_names_list, tool_commands_map_dict, list_of_available_tools, tools_for_claude

mta_trigger_sentences, subway_query_dict, tool_commands_list, tool_commands_map_dict, tool_names_list, list_of_available_tools, tools_for_claude = list_maker()

print(f"Checking if {SUBWAY_LINES}")

async def handle_tool_request(input_data):
    if isinstance(input_data, dict):
        user_input, tool_name = next(iter(input_data.items()))
    else:
        tool_name = input_data
        user_input = None

    if tool_name == "get_current_time":
        current_time = datetime.now().strftime("%I:%M %p")
        return True, f"The current time is {current_time}"
    
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
        response = f'The moon phase today is {moon_phase}.'
        return True, response

    elif tool_name == "nyc_subway_status":
        print(f"Processing NYC subway status. User input: {user_input}")
        if user_input in subway_query_dict:
            print(f"User input found in subway_query_dict")
            try:
                train_line = subway_query_dict[user_input]
                print(f"Train line extracted from subway_query_dict: {train_line}")
            except KeyError:
                train_line = user_input.upper()
                print(f"KeyError occurred. Using uppercased user input as train line: {train_line}")
            print(f"Checking if {train_line} is in SUBWAY_LINES")
        if user_input in SUBWAY_LINES:  
            status = fetch_subway_status(user_input)
            response = train_status_phrase(user_input, status)
            return True, response
        else:
            return False, f"Invalid subway line: {user_input}"

    else:
        return False, f"Unknown tool: {tool_name}"