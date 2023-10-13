# Import the necessary modules and the wake_words list
from wake_words import wake_words
from db_operations import initialize_db, save_conversation, save_to_db
from text_to_speech_operations import talk_with_tts
from speech_to_text_operations import capture_speech
from gpt_operations import handle_conversation
from smart_home_parser import smart_home_parse_and_execute

WAKE_WORD_ACTIVE = True

def main():
    initialize_db()
    messages = []

    while True:
        text, error = capture_speech()
        agent_output = None  # Initialize agent_output to None

        if text:
            # Check for wake words if the feature is active
            if WAKE_WORD_ACTIVE:
                if any(wake_word in text.lower() for wake_word in wake_words):
                    for wake_word in wake_words:
                        if text.lower().startswith(wake_word):
                            text = text[len(wake_word):].strip()  # Remove the wake word from the text
                            break
                else:
                    continue

            is_command_executed, command_response = smart_home_parse_and_execute(text)

            if is_command_executed:
                agent_output = command_response
            else:
                messages.append({"role": "user", "content": text})
                agent_output = handle_conversation(messages)
                messages.append({"role": "assistant", "content": agent_output})

            # Save the conversation to the database here
            save_conversation(text, agent_output)

            # Output agent's message
            if agent_output:
                print("Agent says:", agent_output)
                talk_with_tts(agent_output)

            if "exit" in text.lower():
                print("Exiting the conversation.")
                talk_with_tts("Exiting the conversation.")
                break

        elif error:
            talk_with_tts(error)
            save_to_db('System', error)  # Assuming save_to_db is the correct function, replace if necessary

if __name__ == "__main__":
    main()
