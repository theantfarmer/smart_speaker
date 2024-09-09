from multiprocessing import Value, Lock, Array
from ctypes import c_char
import threading

# The following are for user response after TTS speaks

user_response_window = Value('b', False)
# set in text to speech module
# turns True for a few seconds after
# tts finishes speaking

most_recent_wake_word = Array(c_char, 150)
# Set in Main.  This stores the most recent wake
# word used.  It is reset in TTS if the user doesn't
# respond during the window.

user_response_en_route = Value('b', False)
# This is set in speech to text.  It indicates the
# user has begun speaking, giving time to finish
# and for transcription.  It turns false if
# transcription results in an empty strng.  


tts_is_speaking = Value('b', False)
tts_is_speaking_notification = threading.Event()
tts_lock = Lock()
# set in tts
# becomes true when speech play back starts
# and remains true until all files have finishes playing.
# This is the status used in external moduals