from faster_whisper import WhisperModel
import time
import numpy as np
from pydub import AudioSegment

def preprocess(file, sample_rate=16000):
    sound = AudioSegment.from_file(file, format='wav', frame_rate=sample_rate)
    sound = sound.set_frame_rate(sample_rate)
    samples = sound.get_array_of_samples()
    samples = np.array(samples).flatten().astype(np.float32) / 32768.0
    return samples

start_time = time.time()

model = WhisperModel("tiny", device="cpu", compute_type="int8")

audio_samples = preprocess("tmpvsplpdsd_mono.wav")

segments, info = model.transcribe(audio_samples, beam_size=5, language="en")

# Measure the end time
end_time = time.time()

# Calculate the transcription time
transcription_time = end_time - start_time

print(f"Transcription completed in {transcription_time:.2f} seconds.")
print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

for segment in segments:
    print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))