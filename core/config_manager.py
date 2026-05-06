import json
import os
import threading
import copy
import base64

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
        "gaming": False,
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
    "startup_enabled": False,
    "cloud_allowlist_enabled": True,
    "cloud_allowlist": [
        "OneDrive.exe", "OneDriveStandaloneUpdater.exe", "GoogleDriveFS.exe",
        "GoogleDriveSync.exe", "GoogleDrive.exe", "BackupAndSync.exe",
        "Dropbox.exe", "DropboxUpdate.exe", "iCloudDrive.exe", "iCloudServices.exe",
        "MegaSync.exe", "SynologyDrive.exe", "pCloud Drive.exe", "Nextcloud.exe",
        "explorer.exe", "taskmgr.exe", "svchost.exe", "lsass.exe", "winlogon.exe",
        "dwm.exe", "csrss.exe", "MsMpEng.exe", "SecurityHealthService.exe",
        "MpCmdRun.exe", "python.exe", "pythonw.exe", "SimpleProductivityBlocker.exe",
        "SPB_Daemon.exe", "antigravity.exe", "gemini.exe", "node.exe", "git.exe",
        "code.exe", "powershell.exe", "cmd.exe", "bash.exe", "sh.exe"
    ],
    "cloud_path_keywords": [
        "onedrive", "google drive", "googledrive", "dropbox", "icloud", "mega",
        "synology drive", "pcloud", "nextcloud", "backup and sync",
        "appdata\\roaming", "appdata\\local", "programdata", "windows\\system32"
    ],
    "notifications": {
        "on_block": True, "on_block_attempt": True, "on_exception_bypass": False,
        "on_schedule": True, "on_schedule_window_miss": True,
        "on_daemon_start": True, "on_config_reload": False, "on_hosts_write": False,
        "on_challenge_fail": True, "on_challenge_pass": False
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

def _normalize_group(group_data):
    _deep_merge_defaults(group_data, DEFAULT_GROUP_CONFIG)
    if "exceptions" in group_data:
        legacy = group_data.get("exceptions") or []
        if legacy:
            adblocker = group_data.setdefault("adblocker", {})
            existing = adblocker.get("exceptions", [])
            merged = list(dict.fromkeys(existing + legacy))
            adblocker["exceptions"] = merged
        del group_data["exceptions"]

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
                for group_name, group_data in data["groups"].items():
                    _normalize_group(group_data)
                _normalize_settings(data)
                return data
        except Exception:
            return copy.deepcopy(DEFAULT_CONFIG)

import time

def save_config(config):
    with _lock:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        temp_file = CONFIG_FILE + ".tmp"
        
        # Retry loop to handle file-locking conflicts with the daemon
        max_retries = 10
        for i in range(max_retries):
            try:
                with open(temp_file, 'w') as f:
                    json.dump(config, f, indent=4)
                # Atomic replace (robust on Windows)
                os.replace(temp_file, CONFIG_FILE)
                return
            except (PermissionError, OSError) as e:
                # WinError 5 or [Errno 13] Permission denied
                if i == max_retries - 1:
                    print(f"Failed to save config after {max_retries} attempts: {e}")
                    raise
                time.sleep(0.3) # Wait slightly longer for lock release

def export_config(config, path):
    try:
        data_str = json.dumps(config)
        encoded = base64.b64encode(data_str.encode()).decode()
        with open(path, 'w') as f:
            f.write(encoded)
        return True
    except Exception:
        return False

def import_config(path, current_config=None, merge=True):
    try:
        with open(path, 'r') as f:
            encoded = f.read().strip()
        decoded = base64.b64decode(encoded).decode()
        new_data = json.loads(decoded)
        
        if not merge or not current_config:
            return new_data
            
        merged = copy.deepcopy(current_config)
        if "groups" in new_data:
            for g_name, g_data in new_data["groups"].items():
                merged["groups"][g_name] = g_data
        if "settings" in new_data:
            merged["settings"].update(new_data["settings"])
        return merged
    except Exception:
        return None
