import speech_recognition as sr
import sounddevice as sd
import numpy as np

volume_levels = []

def sound_level_callback(indata, frames, time, status):
    global volume_levels
    volume_norm = np.linalg.norm(indata) * 10
    volume_levels.append(volume_norm)


def capture_speech(threshold=0.5, timeout=5):
    global volume_levels
    recognizer = sr.Recognizer()
    
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        while True:
            # Start monitoring ambient sound level
            with sd.InputStream(callback=sound_level_callback):
                while True:
                    if len(volume_levels) > 0 and max(volume_levels) >= threshold:
                        volume_levels.clear()  # Clear the list after threshold is reached
                        break

            # Once threshold is exceeded, capture speech
            try:
                print("Listening for speech...")
                audio_data = recognizer.listen(source, timeout=timeout)
                text = recognizer.recognize_google(audio_data)
                if text:
                    return text.lower(), None
            except sr.UnknownValueError:
                return None, None
            except sr.RequestError as e:
                return None, f"Could not request results; {e}"
            except sr.WaitTimeoutError:
                return None, "Listening timed out."

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
