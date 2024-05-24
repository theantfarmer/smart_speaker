from dont_tell import HOME_ASSISTANT_TOKEN, home_assistant_ip, ha_ssh_username, ha_ssh_pw
import requests
import json
import yaml
import paramiko  # for SSH
import socket # to get host name

words_to_remove = ["basement", "bedroom", "house", "bathroom"]

# Constants
HOME_ASSISTANT_URL = 'http://homeassistant.local:8123/api/'
HEADERS = {'Authorization': f'Bearer {HOME_ASSISTANT_TOKEN}', 'content-type': 'application/json'}

# Check if Home Assistant is available
def is_home_assistant_available():
    try:
        response = requests.get(f'{HOME_ASSISTANT_URL}states', headers=HEADERS)
        return True if response.status_code == 200 else False
    except requests.RequestException:
        return False

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

# Get all entities and their detailed states
def get_all_entities_with_states():
    if not is_home_assistant_available():
        print("Home Assistant is not available.")
        return []

    response = home_assistant_request('states', 'get')
    if response is not None:
        entities = response.json()
        detailed_entities = []

        for entity in entities:
            entity_id = entity['entity_id']
            state = entity['state']
            attributes = entity['attributes']

            # Check for entity type and extract additional information if needed
            if 'light' in entity_id:
                # Extract light-specific attributes
                scene = attributes.get('scene', 'unknown')
                temperature = attributes.get('color_temp', 'unknown')
                brightness = attributes.get('brightness', 'unknown')
                detailed_entity = {
                    'entity_id': entity_id,
                    'state': state,
                    'scene': scene,
                    'temperature': temperature,
                    'brightness': brightness
                }
            elif 'switch' in entity_id or 'boolean' in entity_id:
                # For simple entities, just use the state
                detailed_entity = {
                    'entity_id': entity_id,
                    'state': state
                }
            else:
                # Default case for other entities
                detailed_entity = {
                    'entity_id': entity_id,
                    'state': state,
                    'attributes': attributes  # Include all attributes
                }

            detailed_entities.append(detailed_entity)

        return detailed_entities
    else:
        return []

# Write the entity list to a JSON file
def write_entities_to_file(entities, filename='home_assistant_entity_list.json'):
    with open(filename, 'w') as file:
        json.dump(entities, file, indent=4)
    print(f"Entities have been written to {filename}")
    
    
    #get automations from automations.yaml on Home Assistant disk to assemble a list of commands and localize them, so a generic "turn on the light" command turns on a light in the room you say it in.

def read_automations_yaml():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(home_assistant_ip, username=ha_ssh_username, password=ha_ssh_pw)
    except paramiko.AuthenticationException:
        print("Authentication failed, please verify your credentials")
        return None
    except paramiko.SSHException as e:
        print(f"SSH connection error: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    try:
        # Direct command to read the automations.yaml file
        command = "sudo cat /config/automations.yaml"
        stdin, stdout, stderr = client.exec_command(command)
        automations_yaml_bytes = stdout.read()
        error = stderr.read().decode('utf-8')

        if error:
            print(f"Error executing command: {error}")
            return None
    except Exception as e:
        print(f"An error occurred while executing the command: {e}")
        return None
    finally:
        client.close()

    automations_yaml = automations_yaml_bytes.decode('utf-8')
    return automations_yaml if automations_yaml.strip() else None

original_commands_mapping = {}  # New dictionary to store original commands

def parse_automations(automations_yaml):
    global words_to_remove
    conversation_commands = []
    naked_commands = set() # Store naked commands

    try:
        automations = yaml.safe_load(automations_yaml)
    except yaml.YAMLError as exc:
        print(f"Error parsing YAML: {exc}")
        return [], {}, {}, {}

    if not automations:
        print("Parsed YAML is empty or not in expected format.")
        return [], {}, {}, {}

    for automation in automations:
        if 'trigger' in automation:
            for trigger in automation['trigger']:
                if isinstance(trigger, dict) and trigger.get('platform') == 'conversation':
                    friendly_name = automation.get('alias', 'Unnamed Automation')
                    commands = trigger.get('command', [])
                    if not isinstance(commands, list):
                        commands = [commands]
                    for command in commands:
                        command_parts = command.split()
                        # Check if the last word of the command is in words_to_remove
                        if command_parts and command_parts[-1].lower() in words_to_remove:
                            if len(command_parts) > 1:
                                # Remove the last word for naked_commands
                                modified_command = ' '.join(command_parts[:-1])
                                naked_commands.add(modified_command)
                        # Add all commands to conversation_commands as is
                        conversation_commands.append({friendly_name: command})

    return conversation_commands, naked_commands


def create_naked_friendly_name(friendly_name, words_to_remove):
    words = friendly_name.split()
    # Remove any unwanted words from the friendly name
    return ' '.join(word for word in words if word.lower() not in words_to_remove)


def check_machine_name(words_to_check):
    hostname = socket.gethostname()
    if hostname.lower() in words_to_check:
        print(f"The name of this machine is '{hostname}', which is in the list.")
        return hostname
    return None
    
def get_first_key(dictionary):
    return next(iter(dictionary))


def write_to_json_file(data, file_name):
    try:
        # Convert each dictionary to a JSON string and store them in a list
        json_strings = [json.dumps(d, separators=(',', ':')) for d in data]

        # Join the strings with a comma and a line break
        formatted_json = '[' + ',\n'.join(json_strings) + ']'

        # Write the formatted string to the file
        with open(file_name, 'w') as file:
            file.write(formatted_json)

        print(f"Data successfully written to {file_name}")
    except IOError as e:
        print(f"An error occurred while writing to the file: {e}")

machine_name_match = check_machine_name(words_to_remove)

automations_yaml = read_automations_yaml()
if automations_yaml:
    conversation_commands,  naked_commands = parse_automations(automations_yaml)

    # Create localized versions of naked commands
    localized_commands = []
    for command in naked_commands:
        command_dict = {"{} localized".format(command): command}
        if machine_name_match:
            # Add the 'replacement' key-value pair
            command_dict["replacement"] = f"{command} {machine_name_match}"
        localized_commands.append(command_dict)

    # Combine localized commands with the existing conversation commands
    full_command_list = conversation_commands + localized_commands

    # Sort full_command_list using the get_first_key function
    full_command_list.sort(key=lambda x: get_first_key(x).lower())
    
    # Continue with writing to the JSON file
    write_to_json_file(full_command_list, 'command_list.json')

     
def load_commands():
    with open('command_list.json', 'r') as file:
        raw_commands_dict = json.load(file)
        flattened_commands = []  # List to store the values

        for command_dict in raw_commands_dict:
            # Convert command_dict to a string to check for a comma
            dict_string = json.dumps(command_dict)
            if ',' in dict_string:
                # Find the index of the first comma
                comma_index = dict_string.find(',')
                # Trim the string to everything before the first comma
                trimmed_dict_string = dict_string[:comma_index] + "}"
                # Convert the trimmed string back to a dictionary
                trimmed_dict = json.loads(trimmed_dict_string)
                # Extract the value and add to the list
                flattened_commands.append(next(iter(trimmed_dict.values())))
            else:
                # Extract the value and add to the list
                flattened_commands.append(next(iter(command_dict.values())))
        return raw_commands_dict, flattened_commands

raw_commands_dict, flattened_commands = load_commands()

def execute_command_in_home_assistant(command):
    if is_home_assistant_available():
        # Sending a POST request with the sentence to the conversation API
        endpoint = "conversation/process"
        payload = {"text": command, "language": "en"}  # Assuming English language
        response = home_assistant_request(endpoint, 'post', payload)
        print("inside execute_command_in_home_assistant")
        if response and response.status_code == 200:
            return True, f" "
        else:
            print(f"Failed to trigger automation: {response.text if response else 'No response'}")
            return True, "Error in triggering automation in Home Assistant."
    else:
        print("Home Assistant is not available")
        return True, "Home Assistant is not available."


