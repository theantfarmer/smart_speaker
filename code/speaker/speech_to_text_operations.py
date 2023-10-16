import speech_recognition as sr

def capture_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)  # Adjusting for ambient noise
        audio_data = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio_data)
            return text, None
        except sr.UnknownValueError:
            return None, None  # Remain silent on unrecognized speech
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return None, f"Could not request results; {e}"

def main():
    print("Please say something...")  
    while True:
        text, error = capture_speech()
        if text:
            print(f"You said: {text}")
        elif error:
            print(f"Error: {error}")

if __name__ == "__main__":
    main()
