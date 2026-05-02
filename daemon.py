import os
import sys
import time
import ctypes
import concurrent.futures

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config_manager import load_config
from core.scheduler import is_active
from blockers.website_blocker import apply_blocks, remove_blocks
from blockers.app_blocker import ProcessMonitor

import urllib.request
import urllib.error
import tempfile
import hashlib
import base64


def b64_decode_list(encoded_str):
    return [d.strip() for d in base64.b64decode(encoded_str).decode('utf-8').split(',')]


ADBLOCK_LISTS = {
    "ads_trackers": [
        "adservice.google.com", "doubleclick.net", "googlesyndication.com", "ads.msn.com",
        "bingads.microsoft.com", "analytics.google.com", "googleadservices.com", "adsystem.com",
        "adnxs.com", "criteo.com", "taboola.com", "outbrain.com", "rubiconproject.com",
        "scorecardresearch.com", "quantserve.com", "zedo.com", "moatads.com"
    ],
    "malware_annoyances": [
        "popads.net", "onclickads.net", "adsterra.com", "propellerads.com", "trafficjunky.com",
        "exoclick.com", "adcash.com", "popcash.net"
    ],
    "social_media": [
        "connect.facebook.net", "pixel.facebook.com", "twitter.com", "x.com", "discord.com",
        "instagram.com", "tiktok.com", "reddit.com", "facebook.com", "snapchat.com",
        "pinterest.com", "linkedin.com", "tumblr.com", "weibo.com", "vk.com", "t.co"
    ],
    "entertainment": [
        "netflix.com", "hulu.com", "disneyplus.com", "crunchyroll.com", "funimation.com",
        "9anime.to", "zoro.to", "nyaa.si", "hbo.com", "max.com", "primevideo.com", "twitch.tv",
        "vimeo.com", "dailymotion.com", "aniwave.to", "aniwatch.to", "myanimelist.net"
    ],
    "shopping": [
        "amazon.com", "temu.com", "ebay.com", "aliexpress.com", "shein.com", "walmart.com",
        "target.com", "bestbuy.com", "etsy.com", "wayfair.com", "wish.com", "alibaba.com"
    ],
    "ai_tech": [
        "chatgpt.com", "openai.com", "anthropic.com", "claude.ai", "perplexity.ai", "poe.com",
        "character.ai", "bard.google.com", "copilot.microsoft.com", "midjourney.com"
    ],

    # Sensitive lists are base64 encoded to prevent casual plaintext reading
    "adult_content": b64_decode_list("cG9ybmh1Yi5jb20sIHh2aWRlb3MuY29tLCB4bnh4LmNvbSwgeGhhbXN0ZXIuY29tLCBjaGF0dXJiYXRlLmNvbQ=="),
    "gambling": b64_decode_list("YmV0MzY1LmNvbSwgZHJhZnRraW5ncy5jb20sIGZhbmR1ZWwuY29tLCBib3ZhZGEubHYsIGJldHdheS5jb20="),
    "piracy_illegal": b64_decode_list("dGhlcGlyYXRlYmF5Lm9yZywgMTMzN3gudG8sIHJ1dHJhY2tlci5vcmcsIGZpdGdpcmwtcmVwYWNrcy5zaXRl")
}


class CustomListManager:
    def __init__(self):
        if os.name == 'nt':
            base_dir = os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker')
        else:
            base_dir = os.path.join(os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')), 'SimpleProductivityBlocker')

        self.cache_dir = os.path.join(base_dir, 'list_cache')
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
            except Exception:
                self.cache_dir = tempfile.gettempdir()

    def get_domains_from_list(self, list_path):
        try:
            if list_path.startswith("http://") or list_path.startswith("https://"):
                url_hash = hashlib.md5(list_path.encode()).hexdigest()
                cache_file = os.path.join(self.cache_dir, f"{url_hash}.txt")

                if os.path.exists(cache_file):
                    if (time.time() - os.path.getmtime(cache_file)) < 86400:
                        return self._parse_file(cache_file)

                try:
                    req = urllib.request.Request(list_path, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=10) as response:
                        content = response.read().decode('utf-8')
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        return self._parse_content(content)
                except Exception:
                    if os.path.exists(cache_file):
                        return self._parse_file(cache_file)
            else:
                if os.path.exists(list_path):
                    return self._parse_file(list_path)
        except Exception as e:
            print(f"Error reading custom list {list_path}: {e}")
        return []

    def _parse_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return self._parse_content(f.read())
        except Exception:
            return []

    def _parse_content(self, content):
        domains = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[0] in ('0.0.0.0', '127.0.0.1'):
                domain = parts[1]
                if domain not in ('localhost', '127.0.0.1', '0.0.0.0'):
                    domains.append(domain)
            elif len(parts) == 1 and '.' in parts[0] and not parts[0].startswith('#'):
                domains.append(parts[0])
        return domains


def _domain_base(domain):
    """Strip www. prefix and normalise to lowercase for comparison."""
    return domain.strip().lower().lstrip("www.")


def _is_excepted(domain, exceptions_bases):
    """
    Return True if domain (or any of its parent domains) matches an exception.
    e.g. exceptions_bases = {'facebook.com'}
    'connect.facebook.net' → False  (different TLD suffix, not a match)
    'connect.facebook.com' → True   (facebook.com is suffix of connect.facebook.com)
    'facebook.com'         → True
    'www.facebook.com'     → True
    """
    base = _domain_base(domain)
    for exc in exceptions_bases:
        if base == exc or base.endswith("." + exc):
            return True
    return False


def is_admin():
    if os.name == 'nt':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False
    else:
        return os.geteuid() == 0


def _compute_targets(config, custom_list_manager):
    """
    Compute the full set of blocked domains, apps, and files from config.

    Block hierarchy:
      Tier 1 — explicit "websites":  blocked when schedule is active. Exceptions NEVER remove these.
      Tier 2 — content filter:       blocked when adblocker is active (persist_all_day OR schedule active).
                                      Exceptions CAN remove these.
      Exceptions live at group_data["exceptions"] (top-level, written by the UI).
    """
    all_websites = []   # Tier 1 — schedule gated, exception-immune
    all_content  = []   # Tier 2 — adblocker gated, exceptions apply
    all_apps     = []
    all_files    = []
    schedule_is_active_anywhere = False

    for group_name, group_data in config.get("groups", {}).items():
        schedule_active   = is_active(group_data)
        ad_settings       = group_data.get("adblocker", {})
        ad_enabled        = ad_settings.get("enabled", False)
        ad_persist        = ad_settings.get("persist_all_day", False)

        # Tier 1: websites — only when schedule allows
        if schedule_active:
            schedule_is_active_anywhere = True
            all_websites.extend(group_data.get("websites", []))
            all_apps.extend(group_data.get("apps", []))
            all_files.extend(group_data.get("files", []))

        # Tier 2: content filter — active if (ad enabled) AND (persist OR schedule active)
        adblocker_active = ad_enabled and (ad_persist or schedule_active)
        if adblocker_active:
            keys = ["ads_trackers", "malware_annoyances", "adult_content", "social_media",
                    "gambling", "piracy_illegal", "entertainment", "shopping", "ai_tech"]
            for key in keys:
                if ad_settings.get(key):
                    all_content.extend(ADBLOCK_LISTS[key])

            # Custom lists (URL or local file) — stored in adblocker block
            custom_list_paths = ad_settings.get("custom_lists", [])
            if custom_list_paths:
                unique_paths = list(set(custom_list_paths))
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    results = executor.map(custom_list_manager.get_domains_from_list, unique_paths)
                    for res in results:
                        all_content.extend(res)

        # Build exception set (suffix-aware) — stored at top-level group_data["exceptions"]
        raw_exceptions   = group_data.get("exceptions", [])
        exceptions_bases = set(_domain_base(e) for e in raw_exceptions if e.strip())

        # Filter Tier 2 only — Tier 1 is never touched by exceptions
        if exceptions_bases:
            all_content = [d for d in all_content if not _is_excepted(d, exceptions_bases)]

    # Merge: Tier 1 always wins; Tier 2 fills in the rest
    # De-duplicate while preserving all Tier-1 entries
    tier1_bases = set(_domain_base(d) for d in all_websites)
    merged_domains = list(all_websites)
    for d in all_content:
        if _domain_base(d) not in tier1_bases:
            merged_domains.append(d)

    return (
        set(merged_domains),
        set(all_apps),
        set(all_files),
        schedule_is_active_anywhere
    )


def main():
    if os.name == 'nt':
        config_path = os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker', 'config.json')
    else:
        config_path = os.path.join(
            os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
            'SimpleProductivityBlocker', 'config.json'
        )

    process_monitor    = ProcessMonitor()
    custom_list_manager = CustomListManager()

    # State tracking — avoids redundant hosts writes
    current_domains = set()
    current_apps    = set()
    current_files   = set()

    # Debounce tracking
    config_cache    = {}
    pending_mtime   = 0
    stable_mtime    = 0
    debounce_ticks  = 0   # each tick = 1 second; fire after 3 stable ticks

    print("Daemon started. Monitoring configuration...")

    try:
        while True:
            # --- 1. Debounce config reload ---
            try:
                file_mtime = os.path.getmtime(config_path) if os.path.exists(config_path) else 0
            except Exception:
                file_mtime = 0

            newly_loaded = False
            if file_mtime != pending_mtime:
                # File just changed — reset debounce window
                pending_mtime  = file_mtime
                debounce_ticks = 0
            else:
                if debounce_ticks < 3:
                    debounce_ticks += 1
                # Fire config reload exactly once after 3 stable seconds
                if debounce_ticks == 3 and stable_mtime != file_mtime:
                    stable_mtime = file_mtime
                    config_cache = load_config()
                    newly_loaded = True

            # --- 2. Compute desired state (runs every tick, cheap) ---
            target_domains, target_apps, target_files, schedule_anywhere = _compute_targets(
                config_cache, custom_list_manager
            )

            # --- 3. Apply only on actual changes ---
            if target_domains != current_domains:
                if target_domains:
                    apply_blocks(list(target_domains), block_doh=schedule_anywhere)
                else:
                    remove_blocks()
                current_domains = target_domains

            if target_apps != current_apps or target_files != current_files:
                current_apps  = target_apps
                current_files = target_files
                if current_apps or current_files:
                    process_monitor.set_blocked_apps(list(current_apps))
                    process_monitor.set_blocked_files(list(current_files))
                    process_monitor.start()
                else:
                    process_monitor.stop()

            time.sleep(1)

    except KeyboardInterrupt:
        remove_blocks()
        process_monitor.stop()
        print("Daemon stopped.")


if __name__ == "__main__":
    if not is_admin():
        print("Administrator privileges required.")
        if os.name == 'nt':
            print("Requesting UAC prompt...")
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        else:
            print("Please run with sudo: sudo " + " ".join(sys.argv))
        sys.exit()
    main()
