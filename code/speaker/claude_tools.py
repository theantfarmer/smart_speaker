import time

def get_current_time():
    return {"current_time": time.strftime("%I:%M %p")}

CLAUDE_TOOLS = [
    {
        "name": "get_current_time",
        "description": "Get the current time. This tool returns the current time in 12-hour format with AM/PM indicator.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

def get_tools_for_claude():
    return CLAUDE_TOOLS

def handle_tool_request(tool_name, tool_input):
    if tool_name == "get_current_time":
        return get_current_time()
    else:
        return {"error": f"Unknown tool: {tool_name}"}