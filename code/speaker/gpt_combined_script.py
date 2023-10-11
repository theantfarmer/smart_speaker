import os
import sqlite3
import speech_recognition as sr
import time
import openai
from gpt_key import OPENAI_API_KEY
from gtts import gTTS
from playsound import playsound

# Load custom instructions
with open('custom_instructions.txt', 'r') as f:
    custom_instructions = f.read().strip()

# Initialize OpenAI API client
openai.api_key = OPENAI_API_KEY

# Initialize DB if it doesn't exist
conn = sqlite3.connect("gpt_chat_history.db")
cursor = conn.cursor()
cursor.execute(
    "CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)"
)
conn.commit()
conn.close()


def save_to_db(role, content):
    conn = sqlite3.connect("gpt_chat_history.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def talk_with_gtts(text):
    tts = gTTS(text=text, lang='en-uk')  # Set language to British English
    tts.save("response.mp3")
    playsound("response.mp3")
    os.remove("response.mp3")

def talk_to_gpt(messages):
    model_engine = "gpt-3.5-turbo"
    response = openai.ChatCompletion.create(
        model=model_engine, messages=messages, temperature=0.9
    )
    return response.choices[0].message['content'].strip()


def main():
    recognizer = sr.Recognizer()
    messages = [{"role": "system", "content": custom_instructions}]

    while True:
        with sr.Microphone() as source:
            print("Please say something...")
            

            audio_data = recognizer.listen(source)

            try:
                text = recognizer.recognize_google(audio_data)
                print("You said:", text)
                

                save_to_db('User', text)
                messages.append({"role": "user", "content": text})

                gpt_output = talk_to_gpt(messages)
                print("GPT says:", gpt_output)
                talk_with_gtts(f"{gpt_output}")

                save_to_db('GPT', gpt_output)
                messages.append({"role": "assistant", "content": gpt_output})

               

                if "exit" in text.lower():
                    print("Exiting the conversation.")
                    talk_with_gtts("Exiting the conversation.")
                    break

            except sr.UnknownValueError:
                print("Could not understand the audio.")
                talk_with_gtts("Could not understand the audio.")
                save_to_db('System', 'Could not understand the audio.')

            except sr.RequestError as e:
                print(f"Could not request results; {e}")
                talk_with_gtts(f"Could not request results; {e}")
                save_to_db('System', f'Could not request results; {e}')


if __name__ == "__main__":
    main()
