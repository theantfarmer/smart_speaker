import speech_recognition as sr
import whisper
import wave
import warnings

warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

def capture_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)  # Adjusting for ambient noise
        audio_data = recognizer.listen(source)
        try:
            # Save the audio data to a file
            with wave.open("temp_audio.wav", "wb") as audio_file:
                audio_file.setnchannels(1)
                audio_file.setsampwidth(audio_data.sample_width)
                audio_file.setframerate(16000)  # Set a suitable framerate
                audio_file.writeframes(audio_data.frame_data)

            # Load the Whisper model
            model = whisper.load_model("base.en")

            # Load the audio file
            audio = whisper.load_audio("temp_audio.wav")

            # Pad or trim the audio to fit 30 seconds
            audio = whisper.pad_or_trim(audio)

            # Make log-Mel spectrogram and move to the same device as the model
            mel = whisper.log_mel_spectrogram(audio).to(model.device).float()  # Convert to float32

            # Decode the audio
            options = whisper.DecodingOptions()
            result = whisper.decode(model, mel, options)

            # Return the recognized text
            return result.text, None
        except sr.UnknownValueError:
            return None, None  # Remain silent on unrecognized speech
        except Exception as e:
            print(f"An error occurred: {e}")
            return None, str(e)  # Handle other exceptions

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
