This is the main project directory.  Fire up main.py to run the program.  

The purpose of this project is to improve on Apple's HomePod and Siri.  I like the HomePod generally but it is very limited and buggy, and becomes outtaded quickly.  

Here are some of the main objectives of this system:
- work locally to ensure reliable use even without internet
- enhance with the internet, but do not require
- maintain privacy
- be so easy to use that any guest will use it naturally
- the user should not have to recall or think of commands 
- have sensable defaults
- allow the user to easily override defaults for more advanced features
- experiment with the latest technologies and models
- maintain speed and funtionality on par with HomePod
- be fun and delight guests
- make it work really well and reliably

**Technical Overview**

This smart speaker system implements a modular, event-driven architecture that demonstrates application of fundamental computer science principles. Following are descriptions of core components of the system:

**Signal Processing and Real-time Analysis**

The smart speaker continuously records and processes audio in small, fifth-of-a-second chunks, analysing each for speech characteristics. Upon speech detection, chunks are combined then processed through a local transcription system. The resulting text undergoes wake word analysis, with non-matching content being discarded for complete privacy and memory management. When a wake word is detected, the user text or audio is routed to appropriate services.
Multi-tiered Wake Word Architecture
A list of system wake words is built at startup, allowing unlimited ways to address the system.  The system implements three types of wake words for distinct processing:

•  General wake words (e.g., 'Hey, Siri') serve default functionality. Algorithms identify keywords or phrases (such as 'what time is it') after the wake word, and route them to appropriate APIs, or to a local language model when APIs reject input or no keyword is recognised.  The local on-device language model is slower than the built in algorithms, but can route queries that algorithms miss, or answer them privately.  

•  Function wake words enable direct routing to specific functions or APIs.  For example, the user can say 'Hey, GPT' for immediate ChatGPT access. This system allows users to bypass keyword detection and ensures input goes to the right place. New services can be added quickly with intuitive call names, allowing vast expandability without interrupting default behaviour.

•  Command wake words combine a trigger with an instruction for immediate execution with as little user effort as possible. For example, 'hey, turn on the light' will turn on the light.  A wake phrase, structured as 'hey [command]' or 'how do I turn on the [command]', can be filled with any command on the list, and is sent directly to the appropriate destination.  All of the words and phrases that algorithms search for after general wake words are available here. 

**Centralised Tool Management**

A unified tool system allows shared utility functions between the default algorithms and connected AI models. This architecture means each tool is written once and can be accessed via keyword algorithms or any LLM.  A tool may be a simple check of the current time, an api for a website, or an AI agent.  Unlimited nesting allows tools to call each other, so one AI agent may call another AI agent, and so on.  The system tracks tool requests using unique identifiers to ensure responses are sent back to the right place.  

**Command Execution Synchronised with Text-to-Speech**

The system implements sophisticated command handling for ChatGPT responses that allows commands to be executed at a precise point while reading the text.  For example, ChatGPT could say, “it was a dark and stormy night,” followed by commands to flash the lights like lightning, which would execute immediately after speaking the phrase.  It works as follows:
    • ChatGPT is prompted to insert lighting commands for colour and brightness into its responses 
    • Commands are demarcated between @[ and ]@ tags 
    • Text is parsed at each @[, creating tuples of (command, text). A command is paired with the text that follows it in ChatGPT’s output, or else it is paired with None.  In the above example, ‘it was a dark and stormy night’ would be paired with None because it precedes the command. 
    • Text is logged to a SQL database and unreadable characters are removed 
    • A text-to-speech platform replaces text in each tuple with audio
    • A playlist system sends the command to home management software at the same time the audio begins playing, resulting in speech and lighting at the same time.  
    
**Frontend Integration**

A web interface provides user preference management and quiet chat functionality for the whole system.  A user can type ‘turn off the lights’ for identical functionality to the voice system, and search through chat history.

**Competes With Big Names**

This smart speaker system competes with commercial products, such as Apple HomePod or Amazon Alexa.  This platform has several notable advantages:
    • Local processing ensures speed, privacy, and reliability even when the internet is out
    • Unlimited ways to address the system means less effort from the user
    • A variety of models from multiple companies can be accessed simultaneously
    • Fast integration of new tools allows new and experimental features are available immediately without waiting for major updates
    
The architecture of this system demonstrates practical application of computer science principles in creating accessible, user-focused technology.



**These are the core modules of the system:**

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



