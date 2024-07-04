import time
from datetime import datetime

def get_current_time():
    return {"current_time": time.strftime("%I:%M %p")}

def get_current_date():
    return {"current_date": time.strftime("%A, %B %d, %Y")}

def get_current_year():
    return {"current_year": time.strftime("%Y")}

def get_current_month():
    return {"current_month": time.strftime("%B")}

def get_current_day_of_week():
    return {"current_day_of_week": time.strftime("%A")}

def get_time_from_timestamp(timestamp):
    time_str = datetime.fromtimestamp(timestamp).strftime("%I:%M %p")
    return {"time": time_str}

def get_date_from_timestamp(timestamp):
    date_str = datetime.fromtimestamp(timestamp).strftime("%A, %B %d, %Y")
    return {"date": date_str}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current time in Bedstuy.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "Get the current date in Bedstuy, including any holiday if applicable.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    
]

def get_tools_for_claude():
    return TOOLS

def handle_tool_request(tool_name, tool_input):
    tool_functions = {
        "get_current_time": get_current_time,
        "get_current_date": get_current_date,
        "get_current_year": get_current_year,
        "get_current_month": get_current_month,
        "get_current_day_of_week": get_current_day_of_week,
        "get_time_from_timestamp": get_time_from_timestamp,
        "get_date_from_timestamp": get_date_from_timestamp
    }
    
    if tool_name in tool_functions:
        return tool_functions[tool_name](**tool_input)
    else:
        return {"error": f"Unknown tool: {tool_name}"}