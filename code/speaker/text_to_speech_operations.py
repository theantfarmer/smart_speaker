from gtts import gTTS
from playsound import playsound
import os

def talk_with_tts(text):
    tts = gTTS(text=text, lang='en-uk')
    tts.save("response.mp3")
    playsound("response.mp3")
    os.remove("response.mp3")
