from db_operations import initialize_db, save_conversation
from gpt_operations import handle_conversation
from smart_home_parser import smart_home_parse_and_execute
import logging
import sys  # Importing sys to parse command line arguments

print("Debug: text_based_main.py started")

def process_text(user_input):
    try:
        print(f"Debug: User input received: {user_input}")

        print("Debug: Initializing database")
        initialize_db()

        messages = [{"role": "user", "content": user_input}]
        print(f"Debug: Messages list initialized: {messages}")

        is_command_executed, command_response = smart_home_parse_and_execute(user_input)
        print(f"Debug: Command execution status: {is_command_executed}, Response: {command_response}")

        if is_command_executed:
            agent_output = command_response
        else:
            agent_output = handle_conversation(messages)
            print(f"Debug: Agent output: {agent_output}")

        print("Debug: Saving conversation to database")
        save_conversation(user_input, agent_output)

        print("Debug: Conversation saved successfully")
        return agent_output

    except Exception as e:
        print(f"Debug: An exception occurred: {e}")
        return "Error"

if __name__ == "__main__":
    # Parsing the first command line argument as user_input
    user_input = sys.argv[1] if len(sys.argv) > 1 else "No input provided"
    output = process_text(user_input)
    print(f"Debug: Final output: {output}")
