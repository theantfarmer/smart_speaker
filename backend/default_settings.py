# default_settings.py

DEFAULT_SETTINGS = {
    "user_profile": {
        "name": "", 
        "secret_phrases": [],
        "user_info_prompt": ""  
    },
        "preferences": {
            "default_bot": {
                "type": "menu",
                "options": [
                    {"value": "hey karen", "label": "Karen"},
                    {"value": "hey home assistant", "label": "Home Assistant"},
                    {"value": "hey claude", "label": "Claude"},
                    {"value": "hey opus", "label": "Claude (Opus)"},
                    {"value": "hey chatgpt", "label": "ChatGPT"}
                ],
                "default": "hey claude"
            },

            "wake_words": []
        },
    "llm_prompts": [
        {
            "name": "Default",
            "content": "You are a helpful assistant."
        }
    ],
    "apis_and_keys": {
        "OPENAI_API_KEY": "",
        "claude_key": "",
        "HOME_ASSISTANT_TOKEN": "",
        "home_assistant_ip": "",
        "ha_ssh_username": "",
        "ha_ssh_pw": "",
        "ELEVEN_LABS_KEY": "",
        "MTA_API_KEY": "",
        "nyt_api_key": "",
        "GOOGLE_CLOUD_CREDENTIALS": {},
        "paired_philips_hue_bridges": {}
    }
}