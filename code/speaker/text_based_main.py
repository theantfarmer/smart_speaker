from db_operations import initialize_db, save_conversation
from gpt_operations import handle_conversation
import sys
import traceback 

def main():
    initialize_db()
    messages = []

    user_text = sys.argv[1] if len(sys.argv) > 1 else ""
    print(f"Received user_text: {user_text}")  # Log the received user_text

    if user_text:
        messages.append({"role": "user", "content": user_text})
        agent_output = handle_conversation(messages)
        print(f"Agent says: {agent_output}")
        print("Debug: About to save to DB")
        save_conversation(user_text, agent_output)
        print("Debug: Successfully saved to DB")

        messages.append({"role": "assistant", "content": agent_output})
       
        


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Traceback:", traceback.format_exc())  