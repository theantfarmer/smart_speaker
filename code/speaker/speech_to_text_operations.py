import speech_recognition as sr

def capture_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Please say something...")
        audio_data = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio_data)
            return text, None
        except sr.UnknownValueError:
            return None, "Could not understand the audio."
        except sr.RequestError as e:
            return None, f"Could not request results; {e}"
