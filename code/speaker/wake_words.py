# wake_words.py

# There are three types of wake words. 
 
# normal wake words such as "hey karen" are used to wake the system
# and user input is analized and directed to the right place.  It is simple
# for the user but is subject to transcription errors.

# command wake words are simple commands that execute a simple action,
# such as turning on a light or checking the time.  Include [command]
# in your wake word to define which words must be used in addition
# to the command.  This allows for shorter commands, such as "hey time"
# to check check the time.

# function wake words allow the user to direct their input to a 
# specific function or tool. Include "f[funtion_or_tool_name]" in
# your wake word to define them.  "hey gpt f[chat_with_gpt]" means
# that "hey gpt" directs user input directly to chatgpt. This
# cuts down on transcription errors that direct input to the 
# wrong place, or allows easy re-direction if the default
# model is not good enough.  Some entities are accessable only this 
# way. 

# make sure to include extra wake words for common 
# transcription mistakes


wake_words = [
            "there you are", 
            "there she is", 
            "hey karen", 
            "hi karen", 
            "um karen", 
            "play karen", 
            "yo karen", 
            "hello karen", 
            "hey [command]", 
            "oh my gosh [command]", 
            "let there be [command]", 
            "how do i [command]",
            "how do you [command]",
            "where is the [command]",
            "Hey cameron",
            "take care and", 
            "they care and",
            "oh my gosh, [command].",
            "Take care and",
            "hey aaron",
            "hey gpt f[chat_with_gpt]",
            "agpt f[chat_with_gpt]",
            "a gpt f[chat_with_gpt]",
            "hey gp f[chat_with_gpt]",
            "hey jeep f[chat_with_gpt]",
            "hey gee f[chat_with_gpt]",
            "h-g-b-t f[chat_with_gpt]",
            "h-g-p-t f[chat_with_gpt]",
            "hey chatgpt f[chat_with_gpt]"
            "hey chat gpt f[chat_with_gpt]",
            "hey claude f[chat_with_claude]",
            "hey clive f[chat_with_claude]",
            "hey clyde f[chat_with_claude]",
            "hey quad f[chat_with_claude]",
            "they clawed f[chat_with_claude]",
            "hey claude opus f[chat_with_claude_opus]",
            "hey opus f[chat_with_claude_opus]",
            "hey claude sonnet f[chat_with_claude_sonnet]",
            "hey sonnet f[chat_with_claude_sonnet]",
            "hey claude haiku f[chat_with_claude_haiku]",
            "hey haiku f[chat_with_claude_haiku]",
            "a claude f[chat_with_claude]",
            "hey clod f[chat_with_claude]",
            "a clawed f[chat_with_claude]",
            "hey clawed f[chat_with_claude]",
            "a clod f[chat_with_claude]",
            "hey clyde f[chat_with_claude]",
            "hey tools bot f[tools_bot]",
            "hey tool spot f[tools_bot]",
            "hey tools f[tools_bot]",
            "hey tool f[tools_bot]",
            "hey dolphin f[chat_with_dolphin]",
            "hey home assistant f[speak_to_home_assistant]",
            "hey homes f[speak_to_home_assistant]",
            "hey holmes f[speak_to_home_assistant]",
            "hey home f[speak_to_home_assistant]",
            "hey mta f[nyc_subway_status]",
            "amta f[nyc_subway_status]",
            "hey subway f[nyc_subway_status]",
            "a subway f[nyc_subway_status]"
      
              ]
