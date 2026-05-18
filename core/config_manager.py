import json
import os
import threading
import ctypes
import sys
import subprocess
import copy
import base64
import shutil
from datetime import datetime

def get_config_dir():
    if os.name == 'nt':
        return os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker')
    else:
        config_home = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        return os.path.join(config_home, 'SimpleProductivityBlocker')

CONFIG_FILE = os.path.join(get_config_dir(), 'config.json')
CONFIG_SCHEMA_VERSION = 2

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
    "max_domains_cap": 1000,
    "cloud_allowlist_enabled": True,
    "cloud_allowlist": [
        "OneDrive.exe", "OneDriveStandaloneUpdater.exe", "GoogleDriveFS.exe",
        "GoogleDriveSync.exe", "GoogleDrive.exe", "BackupAndSync.exe",
        "Dropbox.exe", "DropboxUpdate.exe", "iCloudDrive.exe", "iCloudServices.exe",
        "MegaSync.exe", "SynologyDrive.exe", "pCloud Drive.exe", "Nextcloud.exe",
        "explorer.exe", "taskmgr.exe", "svchost.exe", "lsass.exe", "winlogon.exe",
        "dwm.exe", "csrss.exe", "MsMpEng.exe", "SecurityHealthService.exe",
        "MpCmdRun.exe", "python.exe", "pythonw.exe", "SimpleProductivityBlocker.exe",
        "SPB_Daemon.exe", "node.exe", "git.exe",
        "code.exe", "powershell.exe", "cmd.exe", "bash.exe", "sh.exe",
        "google.com", "bing.com", "duckduckgo.com", "yahoo.com",
        "microsoft.com", "live.com", "outlook.com", "office.com",
        "icloud.com", "apple.com", "github.com", "gitlab.com",
        "openai.com", "anthropic.com", "aws.amazon.com", "dropbox.com",
        "box.com", "zoom.us", "slack.com", "trello.com", "notion.so",
        "googletagmanager.com", "gstatic.com", "googleapis.com",
        "compute.googleapis.com", "oauth2.googleapis.com", "mcp.context7.com"
    ],
    "cloud_path_keywords": [
        "onedrive", "google drive", "googledrive", "dropbox", "icloud", "mega",
        "synology drive", "pcloud", "nextcloud", "backup and sync",
        "appdata\\roaming", "appdata\\local", "programdata", "windows\\system32",
        "program files", "program files (x86)", "steamapps", "site-packages",
        "node_modules", "package.json", ".git", ".vscode", ".config"
    ],
    "notifications": {
        "on_block": True, "on_block_attempt": True, "on_exception_bypass": False,
        "on_schedule": True, "on_schedule_window_miss": True,
        "on_daemon_start": True, "on_config_reload": False, "on_hosts_write": False,
        "on_challenge_fail": True, "on_challenge_pass": False
    },
}

DEFAULT_CONFIG = {
    "schema_version": CONFIG_SCHEMA_VERSION,
    "normalized_at": None,
    "migration_warnings": [],
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
    schedule = group_data.get("schedule", {})
    if isinstance(schedule, dict):
        if "start_time" not in schedule and "start" in schedule:
            schedule["start_time"] = schedule.get("start")
        if "end_time" not in schedule and "end" in schedule:
            schedule["end_time"] = schedule.get("end")
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

def normalize_config(data):
    warnings = []
    if not isinstance(data, dict):
        warnings.append("Config root was not an object; defaults loaded.")
        data = {}

    if "groups" not in data or not isinstance(data.get("groups"), dict):
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
        data = migrated
        warnings.append("Legacy flat config migrated into Default Profile.")

    # Deep-merge top-level defaults, excluding "groups" to prevent "Default Profile" re-creation when other profiles exist
    for k, v in DEFAULT_CONFIG.items():
        if k == "groups":
            if "groups" not in data or not isinstance(data["groups"], dict) or not data["groups"]:
                data["groups"] = copy.deepcopy(DEFAULT_CONFIG["groups"])
        else:
            if isinstance(v, dict):
                if k not in data or not isinstance(data.get(k), dict):
                    data[k] = copy.deepcopy(v)
                else:
                    _deep_merge_defaults(data[k], v)
            else:
                if k not in data:
                    data[k] = copy.deepcopy(v)

    for group_name, group_data in list(data.get("groups", {}).items()):
        if not isinstance(group_data, dict):
            data["groups"][group_name] = copy.deepcopy(DEFAULT_GROUP_CONFIG)
            warnings.append(f"Invalid group '{group_name}' replaced with defaults.")
        else:
            _normalize_group(group_data)

    _normalize_settings(data)
    data["schema_version"] = CONFIG_SCHEMA_VERSION
    data["normalized_at"] = datetime.now().isoformat(timespec="seconds")
    existing = data.get("migration_warnings", [])
    if not isinstance(existing, list):
        existing = []
    data["migration_warnings"] = list(dict.fromkeys(existing + warnings))
    return data

def _quarantine_bad_config(path):
    try:
        if os.path.exists(path):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            quarantine = f"{path}.bad-{ts}"
            shutil.copy2(path, quarantine)
            return quarantine
    except Exception:
        return None
    return None

def repair_config(path=None):
    """Attempt to force-delete a corrupted/locked config via elevation.
    This is a failsafe for the end-user when NTFS ACLs or file locks block standard recovery.
    """
    cfg_file = path or CONFIG_FILE
    if not os.path.exists(cfg_file):
        return True
        
    try:
        # 1. Try standard delete first
        os.remove(cfg_file)
        return True
    except (PermissionError, OSError):
        # 2. If blocked, attempt elevated forced removal
        if os.name == 'nt':
            try:
                # Use powershell to force-remove the item with elevation
                params = f'-NoProfile -Command "Remove-Item \'{cfg_file}\' -Force"'
                res = ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", params, None, 0)
                # res > 32 indicates success in launching
                return res > 32
            except Exception:
                return False
        return False

def load_config(path=None):
    cfg_file = path or CONFIG_FILE
    with _lock:
        if not os.path.exists(cfg_file):
            return normalize_config(copy.deepcopy(DEFAULT_CONFIG))
        try:
            with open(cfg_file, 'r') as f:
                data = json.load(f)
                return normalize_config(data)
        except Exception as e:
            # CORRUPTION DETECTED: Trigger self-healing
            fallback = normalize_config(copy.deepcopy(DEFAULT_CONFIG))
            quarantine = _quarantine_bad_config(cfg_file)
            
            # If we couldn't even quarantine it (likely permission error), trigger repair
            if not quarantine:
                repair_config(cfg_file)
                fallback["migration_warnings"].append("Critical config corruption detected. Elevated self-healing triggered.")
            else:
                fallback["migration_warnings"].append(f"Invalid config quarantined at {quarantine}.")
            
            return fallback

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
        
        new_data = normalize_config(new_data)
        if not merge or not current_config:
            return new_data
            
        merged = normalize_config(copy.deepcopy(current_config))
        if "groups" in new_data:
            for g_name, g_data in new_data["groups"].items():
                merged["groups"][g_name] = g_data
        if "settings" in new_data:
            merged["settings"].update(new_data["settings"])
        return normalize_config(merged)
    except Exception:
        return None
