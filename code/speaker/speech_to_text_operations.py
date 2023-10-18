import speech_recognition as sr
import threading

def capture_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio_data = recognizer.listen(source)

        try:
            text = recognizer.recognize_google(audio_data)
            if text is not None:
                text = text.lower()  # Convert to lowercase here
            return text, None
        except sr.UnknownValueError:
            return None, None
        except sr.RequestError as e:
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
