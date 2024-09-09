import json
import os
from default_settings import DEFAULT_SETTINGS

SETTINGS_FILE = 'dont_tell.json'

def ensure_settings_file_exists():
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)

def load_settings():
    ensure_settings_file_exists()
    with open(SETTINGS_FILE, 'r') as f:
        settings = json.load(f)
    return settings

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def get_setting(key):
    settings = load_settings()
    return settings.get(key)

def update_setting(key, value):
    settings = load_settings()
    if key not in settings:
        settings[key] = {}
    if isinstance(value, dict) and isinstance(settings[key], dict):
        settings[key] = deep_update(settings[key], value, DEFAULT_SETTINGS.get(key, {}))
    else:
        settings[key] = value
    save_settings(settings)

def deep_update(d, u, default):
    for k, v in u.items():
        if isinstance(v, dict):
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d[k] = deep_update(d[k], v, default.get(k, {}))
        else:
            if isinstance(default.get(k), dict) and default[k].get('type') == 'menu':
                # Handle menu-type settings
                d[k] = {
                    "type": "menu",
                    "options": default[k]['options'],
                    "default": v
                }
            else:
                d[k] = v
    return d


# Initialize settings file if it doesn't exist
ensure_settings_file_exists()