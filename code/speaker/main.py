from db_operations import initialize_db, save_conversation, save_to_db  # Updated import
from tts_operations import talk_with_gtts
from speech_to_text_operations import capture_speech
from gpt_operations import handle_conversation

def main():
    initialize_db()
    messages = []
        

    while True:
        text, error = capture_speech()

        if text:
            messages.append({"role": "user", "content": text})
            
            agent_output = handle_conversation(messages)
            
            print("Agent says:", agent_output)
            talk_with_gtts(agent_output)

            save_conversation(text, agent_output)  # Updated call
            messages.append({"role": "assistant", "content": agent_output})

            if "exit" in text.lower():
                print("Exiting the conversation.")
                talk_with_gtts("Exiting the conversation.")
                break

        elif error:
            talk_with_gtts(error)
            save_to_db('System', error)  # This db operation can remain as it's a single, clear operation

if __name__ == "__main__":
    main()
