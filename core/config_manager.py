import json
import os
import threading
import copy

def get_config_dir():
    if os.name == 'nt':
        return os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker')
    else:
        config_home = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        return os.path.join(config_home, 'SimpleProductivityBlocker')

CONFIG_FILE = os.path.join(get_config_dir(), 'config.json')

_lock = threading.Lock()

DEFAULT_GROUP_CONFIG = {
    "websites": [],
    "apps": [],
    "files": [],
    "folders": [],
    "adblocker": {
        "enabled": False,
        "persist_all_day": False,
        "ads_trackers": False,
        "malware_annoyances": False,
        "adult_content": False,
        "social_media": False,
        "gambling": False,
        "piracy_illegal": False,
        "entertainment": False,
        "shopping": False,
        "ai_tech": False,
        "exceptions": [],
        "custom_lists": []
    },
    "schedule": {
        "enabled": False,
        "persist_all_day": False,
        "start_time": "09:00",
        "end_time": "17:00",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    },
    "security": {
        "enabled": False,
        "challenge_length": 32
    }
}

DEFAULT_CONFIG = {
    "groups": {
        "Default Profile": copy.deepcopy(DEFAULT_GROUP_CONFIG)
    }
}

def load_config():
    with _lock:
        if not os.path.exists(CONFIG_FILE):
            return copy.deepcopy(DEFAULT_CONFIG)
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                
                # Migrate old config if it exists
                if "groups" not in data:
                    migrated = copy.deepcopy(DEFAULT_CONFIG)
                    group_data = copy.deepcopy(DEFAULT_GROUP_CONFIG)
                    group_data["websites"] = data.get("websites", [])
                    group_data["apps"] = data.get("apps", [])
                    group_data["files"] = data.get("files", [])
                    group_data["folders"] = data.get("folders", [])
                    group_data["adblocker"] = data.get("adblocker", DEFAULT_GROUP_CONFIG["adblocker"])
                    group_data["schedule"] = data.get("schedule", DEFAULT_GROUP_CONFIG["schedule"])
                    group_data["security"] = data.get("security", DEFAULT_GROUP_CONFIG["security"])
                    migrated["groups"]["Default Profile"] = group_data
                    return migrated
                    
                # Ensure structure
                for group_name, group_data in data["groups"].items():
                    for k, v in DEFAULT_GROUP_CONFIG.items():
                        if k not in group_data:
                            group_data[k] = copy.deepcopy(v)
                return data
        except Exception:
            return copy.deepcopy(DEFAULT_CONFIG)

def save_config(config):
    with _lock:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
