import time

def get_current_time():
    return {"current_time": time.strftime("%I:%M %p")}

CLAUDE_TOOLS = [
    {
        "name": "get_current_time",
        "description": "Get the current time from user system.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

def get_tools_for_claude():
    return CLAUDE_TOOLS

async def handle_tool_request(tool_name, tool_args):
    if tool_name == "get_current_time":
        return get_current_time()["current_time"]
    else:
        return {"error": f"Unknown tool: {tool_name}"}