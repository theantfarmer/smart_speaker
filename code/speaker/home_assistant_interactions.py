# this is the module that handles interaction with home assistant, including automaticly
# building command lists based on sentence triggers in the home assistant UI.
# it works like this:  it extracts the full automations yaml file from home assistant.
# it looks for automations in home assistant that have a "sentance" trigger and adds them to home_assistant_commands 
# it extracts all the sentences and looks for ones with square brackets, which contain room names
# the commands with square brackets are added to a seperate list called localized_home_assistant_commands
# the localized_home_assistant_commands are then reformatted so that if the user says "turn on the lights," which is on the list, and the machine name is bedroom
# it will tack bedroom onto the command so home assistant receives the command as "turn on the lights bedroom"
# I am currently planning the rewrite of this whole section

from dont_tell import HOME_ASSISTANT_TOKEN, home_assistant_ip, ha_ssh_username, ha_ssh_pw
import requests
import json
import yaml
import re
import threading
import paramiko  # for SSH
import socket # to get host name
import websocket


# Constants
HOME_ASSISTANT_URL = 'http://homeassistant.local:8123/api/'
HEADERS = {'Authorization': f'Bearer {HOME_ASSISTANT_TOKEN}', 'content-type': 'application/json'}

room_names = ["basement", "bedroom", "house", "bathroom"]

# the entire program is coppied precisely to different machines throughout the house
# the script is not localized because its easier to keep all machines
# up to date, and avoid errors, when the code is exactly the same.

# to add localized features, we get the name of the host machine,
# which should be named for the room it resides.  We then use
# the hostname to localize featurs.  When someone says "turn on the lights,"
# we tack the host name to the end before sending it to home assistant.

# in home assistant, we prepare localized commands using [roomname] to identify localized commands
# we must create a duplicate without [ ] because HA won't accept these chachters 
# When setting up trigger: sentence in each automation,
# you may include "turn on the lights [bedroom]" for the 
# bedroom automation, and "turn on the lights [kitchen]" for
# the kitchen automation. And duplicate "turn on the lights bedroom",
# etc.  The [] version is for identifying and sorting in this program.
#  And the non [] is what HA will actually receieve and process.  

def check_machine_name():
    hostname = socket.gethostname()
    print(f"The name of this machine is '{hostname}'")
    return hostname

hostname = check_machine_name()

# Check if Home Assistant is available

# Make a request to Home Assistant
def home_assistant_request(endpoint, method, payload=None):
    url = f'{HOME_ASSISTANT_URL}{endpoint}'
    try:
        if method == 'get':
            response = requests.get(url, headers=HEADERS, timeout=10)
        elif method == 'post':
            response = requests.post(url, headers=HEADERS, json=payload, timeout=10)

        response.raise_for_status()
        return response
    except (requests.RequestException, ValueError) as e:
        print(f"Exception occurred: {e}")
        return None
  
# get automations from automations.yaml on Home Assistant disk to assemble a list of commands and localize them, so a generic "turn on the light" command turns on a light in the room you say it in.

# we retrieve the full automations yaml from the home assistant server
# and store it in a variable

def read_automations_yaml():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(home_assistant_ip, username=ha_ssh_username, password=ha_ssh_pw)
        stdin, stdout, stderr = client.exec_command("sudo cat /config/automations.yaml")
        automations_yaml = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        if error:
            print(f"Error executing command: {error}")
            return None

    except (paramiko.AuthenticationException, paramiko.SSHException, Exception) as e:
        print(f"An error occurred: {e}")
        return None

    finally:
        client.close()

    return automations_yaml or None


# in the home assitant UI, automations use a "sentance" trigger for voice commands
# in the yaml, those sentences reside under:
# -trigger: =>   - platform: conversation => command: => a list of command sentences
# each sentence is seperated by a line break and a -.
# we also extract the alias, which is the name of the automation in the HA ui.

# The automation below extracts those sentences along with automation names
# for each command we creat a dictionary for automation name : command 
# if the command does not contain [ ], the dict added to the list home_assistant_commands
# if it does contain [ ], we remove [ ] and add the dict to the list 
# we exclude commands with square brackets containing room names, remove the 
# parts in square brackets, and append them to a seperate list called localized_home_assistant_commands

# Next, we use the hostname to filter out dictionairies that do not contain [hostname],
# we combine the localized commands with regular commands in home_assistant_commands.
# And then remove the dictionaries and localiztion in flattened commands, which is
# a simple list.  
 
flattened_localized_commands = []

def parse_automations():
    global hostname, flattened_localized_commands

    home_assistant_commands = []
    flattened_home_assistant_commands = []

    automations_yaml = read_automations_yaml()
    
    if not automations_yaml:
        print("Failed to read automations YAML.")
        return [], []

    try:
        automations = yaml.safe_load(automations_yaml)
        # print(f"automations: {automations}")
    except yaml.YAMLError as exc:
        print(f"Error parsing YAML: {exc}")
        return [], []

    if not automations or not isinstance(automations, list):
        print("Parsed YAML is empty or not in expected format.")
        return [], []

    for automation in automations:
        if 'trigger' in automation:
            for trigger in automation['trigger']:
                if isinstance(trigger, dict) and trigger.get('platform') == 'conversation':
                    friendly_name = automation.get('alias', 'Unnamed Automation')
                    command_list = trigger.get('command', [])
                    if isinstance(command_list, list):
                        for command in command_list:
                            if isinstance(command, str):
                                if '[' in command and ']' in command:
                                    if f'[{hostname}]' in command: 
                                        flattened_command = re.sub(r'\[.*?\]', '', command).strip()
                                        command_dict = {friendly_name: flattened_command}
                                        # append dict of friendlyname : command to ome asst commands
                                        home_assistant_commands.append(command_dict)
                                        # append command only to HA commands
                                        flattened_home_assistant_commands.append(flattened_command)
                                        # append command only to localized. the other two are repeated below, localized isn't.
                                        flattened_localized_commands.append(flattened_command)
                                else:
                                    command_dict = {friendly_name: command}
                                    home_assistant_commands.append(command_dict)
                                    flattened_home_assistant_commands.append(command)
                                 

    home_assistant_commands = sorted(home_assistant_commands, key=lambda x: list(x.keys())[0])    
    flattened_home_assistant_commands = sorted(set(flattened_home_assistant_commands))
    flattened_localized_commands = sorted(set(flattened_localized_commands))
    return home_assistant_commands, flattened_home_assistant_commands, flattened_localized_commands

home_assistant_commands, flattened_home_assistant_commands, flattened_localized_commands = parse_automations()


# RESTFUL:  
# def execute_command_in_home_assistant(command_to_execute):
#     global hostname, flattened_localized_commands
#     if command_to_execute in flattened_localized_commands:
#         command_to_execute = f"{command_to_execute} {hostname}"

#     endpoint = "conversation/process"
#     url = f'{HOME_ASSISTANT_URL}{endpoint}'
#     payload = {"text": command_to_execute, "language": "en"}
#     print(f"Sending command to Home Assistant: {command_to_execute}")
#     try:
#         response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
#         response.raise_for_status()
#         print("inside execute_command_in_home_assistant")
#         print(f"Home Assistant response status code: {response.status_code}")
#         print(f"Home Assistant response text: {response.text}")

#         # Parse the response JSON
#         response_json = json.loads(response.text)
#         # Extract the string after "speech"
#         speech_response = response_json["response"]["speech"]["plain"]["speech"]
#         # Check if speech_response is whitespace, empty, or contains [hostname]
#         if speech_response == "Done":
#             return True, ""
#         if speech_response.strip() == "" or f"[{hostname}]" in speech_response:
#             return False, ""
#         # Check if speech_response contains square brackets not related to hostname
#         if "[" in speech_response and "]" in speech_response:
#             speech_response = speech_response.split("[")[0].strip()
#         return True, speech_response
#     except (requests.RequestException, ValueError, KeyError) as e:
#         print(f"Exception occurred: {e}")
#         return False, str(e)
#     else:
#         print("Home Assistant is not available")
#         return False, "Home Assistant is not available"

# WEBSOCKETS:  

def execute_command_in_home_assistant(command_to_execute, command_type='call_service', service=None, payload=None):
    global hostname, flattened_localized_commands, HOME_ASSISTANT_TOKEN

    if isinstance(command_to_execute, dict):
        # If it's a dictionary, assume it's a JSON command
        command_type = command_to_execute.get('command_type', command_type)
        service = command_to_execute.get('service', service)
        payload = command_to_execute.get('payload', payload)
    else:
        # If it's a string, assume it's a sentence command
        if command_to_execute in flattened_localized_commands:
            command_to_execute = f"{command_to_execute} {hostname}"
        payload = {"text": command_to_execute, "language": "en"}

    websocket_url = "ws://homeassistant.local:8123/api/websocket"
    print(f"Connecting to Home Assistant websocket: {websocket_url}")
    
    try:
        ws = websocket.create_connection(websocket_url)
        
        # Receive the auth_required message
        auth_required_response = json.loads(ws.recv())
        if auth_required_response["type"] != "auth_required":
            raise ValueError("Unexpected response: " + str(auth_required_response))
        
        # Authenticate with Home Assistant
        auth_message = json.dumps({"type": "auth", "access_token": HOME_ASSISTANT_TOKEN})
        ws.send(auth_message)
        auth_response = json.loads(ws.recv())
        if auth_response["type"] == "auth_ok":
            print("Authentication successful")
        elif auth_response["type"] == "auth_invalid":
            raise ValueError("Authentication failed: " + auth_response.get("message", "Invalid access token"))
        else:
            raise ValueError("Unexpected authentication response: " + str(auth_response))
        
        # Send the command
        command_id = 1
        command_message = json.dumps({"id": command_id, "type": "conversation/process", "text": command_to_execute})
        print(f"Sending command to Home Assistant: {command_to_execute}")
        ws.send(command_message)
        
        # Receive the response
        response_json = json.loads(ws.recv())
        print(f"Home Assistant response: {response_json}")
        
        if response_json["id"] != command_id:
            raise ValueError("Unexpected response ID")
        
        if response_json["type"] == "result" and response_json["success"]:
            result = response_json["result"]
            if "response" in result:
                if "speech" in result["response"] and "plain" in result["response"]["speech"]:
                    speech_response = result["response"]["speech"]["plain"]["speech"]
                    # Check if speech_response is precisely "Done"
                    if speech_response == "Done":
                        ws.close()
                        return True, ""
                    # Check if speech_response is whitespace, empty, or contains [hostname]
                    if isinstance(speech_response, str) and (speech_response.strip() == "" or f"[{hostname}]" in speech_response):
                        ws.close()
                        return False, ""
                    ws.close()
                    return True, speech_response
                else:
                    ws.close()
                    return False, "Response missing 'speech' or 'plain' field"
            else:
                ws.close()
                return False, "Response missing 'response' field"
        else:
            ws.close()
            return False, "Command execution failed or unexpected response type"
    
    except (websocket.WebSocketException, ValueError, KeyError) as e:
        print(f"Exception occurred: {e}")
        return False, str(e)
    
    except Exception as e:
        print(f"Unexpected exception occurred: {e}")
        return False, str(e)
 
    
if __name__ == "__main__":
    parse_automations()