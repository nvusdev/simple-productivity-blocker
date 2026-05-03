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

DEFAULT_SETTINGS = {
    "performance_mode": "Balanced",
    "cloud_allowlist_enabled": True,
    "cloud_allowlist": [
        "OneDrive.exe",
        "GoogleDriveFS.exe",
        "GoogleDriveSync.exe",
        "GoogleDrive.exe",
    ],
    "cloud_path_keywords": [
        "onedrive",
        "google drive",
        "googledrive",
    ],
    "notifications": {
        "on_block": True,
        "on_schedule": True,
        "on_daemon_start": True,
    },
}

DEFAULT_CONFIG = {
    "groups": {
        "Default Profile": copy.deepcopy(DEFAULT_GROUP_CONFIG)
    },
    "settings": copy.deepcopy(DEFAULT_SETTINGS)
}

def _deep_merge_defaults(target, defaults):
    for key, value in defaults.items():
        if isinstance(value, dict):
            if key not in target or not isinstance(target.get(key), dict):
                target[key] = copy.deepcopy(value)
            else:
                _deep_merge_defaults(target[key], value)
        else:
            if key not in target:
                target[key] = copy.deepcopy(value)

def _migrate_exceptions(group_data):
    if "exceptions" in group_data:
        legacy = group_data.get("exceptions") or []
        if legacy:
            adblocker = group_data.setdefault("adblocker", {})
            existing = adblocker.get("exceptions", [])
            merged = list(dict.fromkeys(existing + legacy))
            adblocker["exceptions"] = merged
        del group_data["exceptions"]

def _normalize_group(group_data):
    _deep_merge_defaults(group_data, DEFAULT_GROUP_CONFIG)
    _migrate_exceptions(group_data)

def _normalize_settings(config_data):
    settings = config_data.get("settings")
    if not isinstance(settings, dict):
        config_data["settings"] = copy.deepcopy(DEFAULT_SETTINGS)
        return
    _deep_merge_defaults(settings, DEFAULT_SETTINGS)

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
                    group_data = {
                        "websites": data.get("websites", []),
                        "apps": data.get("apps", []),
                        "files": data.get("files", []),
                        "folders": data.get("folders", []),
                        "adblocker": data.get("adblocker", {}),
                        "schedule": data.get("schedule", {}),
                        "security": data.get("security", {}),
                        "exceptions": data.get("exceptions", []),
                    }
                    _normalize_group(group_data)
                    migrated["groups"]["Default Profile"] = group_data
                    if "settings" in data:
                        migrated["settings"] = data.get("settings", {})
                        _normalize_settings(migrated)
                    return migrated
                    
                # Ensure structure
                for group_name, group_data in data["groups"].items():
                    _normalize_group(group_data)
                _normalize_settings(data)
                return data
        except Exception:
            return copy.deepcopy(DEFAULT_CONFIG)

def save_config(config):
    with _lock:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
