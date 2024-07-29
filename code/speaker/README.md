This is the main project directory.  Fire up main.py to run the program.  

These are the core modules of the system:  

main.py - the main module
speech_to_text_operations_fasterwhisper.py - the main speech transcription module
text_to_speech_operations.py - handles common text to speech logic as well as syncronized commands


These modules greatly enhance functionality but are not part of the core system:

 centralized_tools.py - this sorts and directs tool requests
 claude_custom_instructions.txt - your main prompt goes here
 dont_tell.py - store secrets here - such as API keys, or secret phrases
 expressive_light.py - this handles lighting commands returned by LLMs
 gtts_tts.py - this sends TTS to google voice
 home_assistant_interactions.py - communicated with Home Assistant for smart home stuff
 llm_chatgpt.py - handles chatgpt communications
 llm_claude.py - handles Claude communications, including Tools Bot
 llm_gpt_dolphinmini.py - communications with a local LLM using ollama
 llm_operations.py - general LLM handling.  Common handling not specific to models is here
 queue_handling.py - inter-module queues are setup here to avoid circular errors
 requirements.txt - out of date hold on
 shared_variables.py - setup inter-module variables to avoid circular errors
 transit_routes.py
 tts_eleven_labs.py - interacts with advanced Eleven Labs TTS
 tts_eleven_labs_webhooks.py - interacts with Eleven Labs with additional webhooks logic
 tts_google_cloud.py - interacts with the advanced Google Cloud TTS
 tts_piper.py - interacts with the on-device TTS system Piper
 wake_words.py - set wake words, function wake words and command wake words to access the system

these are placeholders and are not updated frequently:  
 bluetooth_detector.py - under development.  not used yet
 text_based_main.py - this is an alternative to main.py to interact via a text front end.  It is gloriously out of date and not currently maintained.  
 db_operations.py - this handles the database.  It is not maintained currently.



