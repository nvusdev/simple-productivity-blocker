import os
import sys
import time
import ctypes

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
            except:
                self.cache_dir = tempfile.gettempdir()
                
    def get_domains_from_list(self, list_path):
        domains = []
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
                except:
                    if os.path.exists(cache_file):
                        return self._parse_file(cache_file)
            else:
                if os.path.exists(list_path):
                    return self._parse_file(list_path)
                    
        except Exception as e:
            print(f"Error reading custom list {list_path}: {e}")
            
        return domains

    def _parse_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return self._parse_content(f.read())
        except:
            return []
            
    def _parse_content(self, content):
        domains = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 2 and (parts[0] == '0.0.0.0' or parts[0] == '127.0.0.1'):
                domain = parts[1]
                if domain != 'localhost' and domain != '127.0.0.1' and domain != '0.0.0.0':
                    domains.append(domain)
            elif len(parts) == 1:
                domain = parts[0]
                if '.' in domain and not domain.startswith('#'):
                    domains.append(domain)
        return domains

def is_admin():
    if os.name == 'nt':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    else:
        return os.geteuid() == 0

def main():
    if os.name == 'nt':
        config_path = os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker', 'config.json')
    else:
        config_path = os.path.join(os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')), 'SimpleProductivityBlocker', 'config.json')
        
    process_monitor = ProcessMonitor()
    custom_list_manager = CustomListManager()
    
    last_config_mtime = 0
    config_cache = {}
    
    import concurrent.futures

    print("Daemon started. Monitoring configuration...")

    try:
        while True:
            try:
                current_mtime = os.path.getmtime(config_path) if os.path.exists(config_path) else 0
            except Exception:
                current_mtime = 0

            if current_mtime != last_config_mtime:
                last_config_mtime = current_mtime
                config_cache = load_config()
                
            config = config_cache
            
            all_apps = []
            all_files = []
            all_domains = []
            all_custom_lists = []
            
            schedule_is_active_anywhere = False
            
            for group_name, group_data in config.get("groups", {}).items():
                schedule_active = is_active(group_data)
                adblocker_active = False
                
                ad_settings = group_data.get("adblocker", {})
                if ad_settings.get("enabled"):
                    if ad_settings.get("persist_all_day") or schedule_active:
                        adblocker_active = True
                
                if schedule_active:
                    schedule_is_active_anywhere = True
                    all_apps.extend(group_data.get("apps", []))
                    all_files.extend(group_data.get("files", []))
                    all_domains.extend(group_data.get("websites", []))
                
                if adblocker_active:
                    keys = ["ads_trackers", "malware_annoyances", "adult_content", "social_media", "gambling", "piracy_illegal", "entertainment", "shopping", "ai_tech"]
                    for key in keys:
                        if ad_settings.get(key):
                            all_domains.extend(ADBLOCK_LISTS[key])
                            
                    all_custom_lists.extend(ad_settings.get("custom_lists", []))
                        
                exceptions = group_data.get("exceptions", [])
                exceptions_set = set(e.replace('www.', '').lower().strip() for e in exceptions)
                filtered_domains = []
                for d in all_domains:
                    base_d = d.replace('www.', '').lower().strip()
                    if base_d not in exceptions_set:
                        filtered_domains.append(d)
                all_domains = filtered_domains

            if all_custom_lists:
                unique_lists = list(set(all_custom_lists))
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    results = executor.map(custom_list_manager.get_domains_from_list, unique_lists)
                    for res in results:
                        all_domains.extend(res)

            process_monitor.set_blocked_apps(list(set(all_apps)))
            process_monitor.set_blocked_files(list(set(all_files)))

            if len(all_domains) > 0:
                apply_blocks(list(set(all_domains)), block_doh=schedule_is_active_anywhere)
            else:
                remove_blocks()

            if len(all_apps) > 0 or len(all_files) > 0:
                process_monitor.set_blocked_apps(list(set(all_apps)))
                process_monitor.set_blocked_files(list(set(all_files)))
                process_monitor.start()
            else:
                process_monitor.stop()
                
            time.sleep(5)
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
