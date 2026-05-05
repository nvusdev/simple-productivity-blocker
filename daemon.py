import os
import sys
import time
import ctypes
import zlib
import base64
import concurrent.futures

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config_manager import load_config
from core.scheduler import is_active, is_day_active
from blockers.website_blocker import apply_blocks, remove_blocks
from blockers.app_blocker import ProcessMonitor
from blockers.dns_server import DNSProxyServer, detect_system_dns

try:
    from blockers.file_blocker import FileBlocker
except Exception:
    FileBlocker = None

import urllib.request
import tempfile
import hashlib

_K = bytes([0x53, 0x50, 0x42, 0x2D, 0x4B, 0x45, 0x59, 0x21,
            0x40, 0x23, 0x24, 0x25, 0x5E, 0x26, 0x2A, 0x28])

_ADULT = "eJwdzG0LwUAAAOBE8pL2B3zYdrNmHHdHszB7v3PuLKGk2D76QJLyjfx15Qc8D/BRDNBMAZLXzU0sHR+XLXvccten8yNN069lS9OBCWmx1ajBA2JMiq4Bk3sgls9VnDtTkJv9yd97jLU/IxhcLJURGlJfHKvIH5Zc3FuiQCZ2jbPFW406uhtp2aHpcVbBOjhgtbf9f4mgY4Ii9zrNoCIEKST3wC0zrBfTdiEnvCLm3r0YaHCv0wbF4gcLsyv0"
_GAMBLE = "eJwzNDWTqy0od9L343DUcfeJsbDU8bLItvLT5XdyMXCK97WvU3RSy7T2M3NycCnwimExNDWL0rIBqw8y93JzNLLVclHXBPNDDX39oxRUlOMh+mVk01y9o63sdJk1tEx4ldwCnO39I9gM7PUZ7bQNnFXDudwMvdm8jUwNfSzNrByMvby8ClxdXettVR0sFbT8jMLDuW093UH2OehogMwHAOJMKHs="
_PIRACY = "eJxTt1CPVTK3CFV1dI0p8Izwr08slKuxLQ/V5w8L0Arx9rYwNWBWMbfjVfMKcDIPcWNVNDXy0dDT4jf2CnAo8gj2NKozdEk3twhWcuEKNORydDSwVo6zMDQLNnLzCtTliHOvV9GNt1QwD7US5HLQ5gqOUajTD01XUA414w1zKPJydjWDyhvzursV+Ue6a9rreKRq24TmOIS52Pr6+5gY6ntYZJu7mPCH+5k7RbirKKk7qqjYuqjwunsZc0X4KhsquqUpWfioBnC5GXoDAI+1MeE="

def _dec(payload: str) -> list[str]:
    raw = zlib.decompress(base64.b64decode(payload))
    key = _K
    dec = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return [d.strip() for d in dec.decode("utf-8").split(",") if d.strip()]

ADBLOCK_LISTS = {
    "ads_trackers": [
        "adservice.google.com", "doubleclick.net", "googlesyndication.com",
        "googleadservices.com", "ads.msn.com", "bingads.microsoft.com",
        "bat.bing.com", "adsystem.com", "tinder.com", "gotinder.com", 
        "api.gotinder.com", "analytics.google.com", "google-analytics.com", 
        "googletagmanager.com", "googletagservices.com", "scorecardresearch.com", 
        "quantserve.com", "segment.com", "segment.io", "mixpanel.com", 
        "amplitude.com", "hotjar.com", "fullstory.com", "logrocket.com", 
        "heap.io", "adnxs.com", "criteo.com", "taboola.com", "outbrain.com",
        "rubiconproject.com", "zedo.com", "moatads.com", "pubmatic.com",
        "openx.net", "casalemedia.com", "synacor.com", "advertising.com",
        "adblade.com", "yieldmo.com", "smartadserver.com", "sovrn.com",
        "spotxchange.com", "33across.com", "triplelift.com", "sharethrough.com",
    ],
    "malware_annoyances": [
        "popads.net", "onclickads.net", "adsterra.com", "propellerads.com",
        "trafficjunky.com", "exoclick.com", "adcash.com", "popcash.net",
        "juicyads.com", "hilltopads.net", "plugrush.com", "ero-advertising.com",
        "tsyndicate.com", "clickadu.com", "zeropark.com", "coin-hive.com", 
        "coinhive.com", "cryptoloot.pro", "minero.cc", "canvas.fingerprint.com", 
        "fingerprint.com",
    ],
    "social_media": [
        "facebook.com", "fb.com", "fb.me", "connect.facebook.net",
        "pixel.facebook.com", "graph.facebook.com", "staticxx.facebook.com",
        "twitter.com", "x.com", "www.x.com", "t.co", "twimg.com",
        "instagram.com", "cdninstagram.com", "tiktok.com", "tiktokv.com", 
        "tiktokcdn.com", "tiktokw.us", "muscdn.com", "reddit.com", "redd.it", 
        "redditmedia.com", "redditstatic.com", "reddituploads.com", "v.redd.it", 
        "i.redd.it", "preview.redd.it", "discord.com", "discord.gg", 
        "discordapp.com", "discordapp.net", "discordcdn.com", "media.discordapp.net", 
        "cdn.discordapp.com", "linkedin.com", "licdn.com", "snapchat.com", 
        "snap.com", "pinterest.com", "pinimg.com", "tumblr.com", "weibo.com", 
        "vk.com", "vkuservideo.net", "threads.net", "bsky.app", "bsky.social", 
        "t.me", "telegram.org", "mastodon.social", "whatsapp.com", "signal.org", 
        "line.me",
    ],
    "entertainment": [
        "netflix.com", "hulu.com", "disneyplus.com", "hbo.com", "max.com",
        "peacocktv.com", "paramountplus.com", "appletv.apple.com",
        "crunchyroll.com", "funimation.com", "hidive.com", "primevideo.com", 
        "amazon.com/video", "myanimelist.net", "anilist.co", "kitsu.io",
        "twitch.tv", "kick.com", "vimeo.com", "dailymotion.com",
        "rumble.com", "odysee.com", "spotify.com", "soundcloud.com", 
        "pandora.com", "tidal.com", "deezer.com", "music.apple.com",
        "youtube.com", "youtu.be", "googlevideo.com", "ytimg.com",
        "youtubei.googleapis.com", "ytimg.l.google.com", "9anime.to", 
        "zoro.to", "aniwave.to", "aniwatch.to",
    ],
    "shopping": [
        "amazon.com", "temu.com", "ebay.com", "aliexpress.com",
        "shein.com", "walmart.com", "target.com", "bestbuy.com",
        "etsy.com", "wayfair.com", "wish.com", "alibaba.com",
        "zappos.com", "overstock.com", "newegg.com", "homedepot.com",
        "lowes.com", "costco.com", "samsclub.com", "macys.com",
        "nordstrom.com", "shopify.com", "zara.com", "hm.com",
    ],
    "ai_tech": [
        "chatgpt.com", "openai.com", "chat.openai.com", "anthropic.com", 
        "claude.ai", "gemini.google.com", "bard.google.com", "copilot.microsoft.com", 
        "bing.com/chat", "perplexity.ai", "poe.com", "character.ai", 
        "grok.x.ai", "grok.com", "you.com", "phind.com", "blackbox.ai",
        "midjourney.com", "stability.ai", "stablediffusionweb.com",
        "runwayml.com", "replicate.com", "civitai.com", "hackernews.com", 
        "news.ycombinator.com", "techcrunch.com", "theverge.com", "wired.com", 
        "arstechnica.com", "engadget.com",
    ],
    "adult_content": _dec(_ADULT),
    "gambling":      _dec(_GAMBLE),
    "piracy_illegal": _dec(_PIRACY),
}

class CustomListManager:
    def __init__(self):
        if os.name == "nt":
            base = os.path.join(os.getenv("PROGRAMDATA", r"C:\ProgramData"), "SimpleProductivityBlocker")
        else:
            base = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "SimpleProductivityBlocker")
        self.cache_dir = os.path.join(base, "list_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_domains_from_list(self, list_path: str) -> list[str]:
        try:
            if list_path.startswith(("http://", "https://")):
                uid = hashlib.md5(list_path.encode()).hexdigest()
                cache = os.path.join(self.cache_dir, f"{uid}.txt")
                if os.path.exists(cache) and (time.time() - os.path.getmtime(cache)) < 86400:
                    return self._parse_file(cache)
                try:
                    req = urllib.request.Request(list_path, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=10) as r:
                        content = r.read().decode("utf-8")
                    with open(cache, "w", encoding="utf-8") as f:
                        f.write(content)
                    return self._parse_content(content)
                except Exception:
                    return self._parse_file(cache) if os.path.exists(cache) else []
            elif os.path.exists(list_path):
                return self._parse_file(list_path)
        except Exception as e:
            print(f"Custom list error ({list_path}): {e}")
        return []

    def _parse_file(self, path: str) -> list[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return self._parse_content(f.read())
        except Exception:
            return []

    def _parse_content(self, content: str) -> list[str]:
        out = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("!"): continue
            if line.startswith("||"):
                domain = line[2:].split("^", 1)[0].split("/", 1)[0].strip().lstrip(".").replace("*", "")
                if domain and "." in domain: out.append(domain)
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[0] in ("0.0.0.0", "127.0.0.1"):
                d = parts[1]
                if d not in ("localhost", "127.0.0.1", "0.0.0.0"): out.append(d)
            elif len(parts) == 1 and "." in parts[0]:
                out.append(parts[0])
        return out

def _base(domain: str) -> str:
    return domain.strip().lower().removeprefix("www.")

def _is_excepted(domain: str, exc_set: set[str]) -> bool:
    b = _base(domain)
    return any(b == e or b.endswith("." + e) for e in exc_set)

def _compute_targets(config: dict, clm: CustomListManager) -> tuple[set, set, set, set, bool]:
    tier1: list[str] = []
    tier2: list[str] = []
    all_apps:  list[str] = []
    all_files: list[str] = []
    all_folders: list[str] = []
    schedule_anywhere = False

    for _, gdata in config.get("groups", {}).items():
        schedule = gdata.get("schedule", {})
        day_active = is_day_active(schedule)
        sched_active = is_active(gdata)
        ad = gdata.get("adblocker", {})
        ad_on = ad.get("enabled", False)
        ad_persist = ad.get("persist_all_day", False)

        if sched_active:
            schedule_anywhere = True
            tier1.extend(gdata.get("websites", []))
            all_apps.extend(gdata.get("apps", []))
            all_files.extend(gdata.get("files", []))
            all_folders.extend(gdata.get("folders", []))

        adblocker_active = ad_on and ((day_active if ad_persist else sched_active))
        if adblocker_active:
            schedule_anywhere = True
            keys = ["ads_trackers", "malware_annoyances", "adult_content", "social_media",
                    "gambling", "piracy_illegal", "entertainment", "shopping", "ai_tech"]
            group_content: list[str] = []
            for k in keys:
                if ad.get(k): group_content.extend(ADBLOCK_LISTS[k])

            custom_paths = ad.get("custom_lists", [])
            if custom_paths:
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                    for res in ex.map(clm.get_domains_from_list, set(custom_paths)):
                        group_content.extend(res)

            raw_exc = ad.get("exceptions", [])
            exc_set = {_base(e) for e in raw_exc if e.strip()}
            if exc_set:
                group_content = [d for d in group_content if not _is_excepted(d, exc_set)]
            tier2.extend(group_content)

    t1_bases = {_base(d) for d in tier1}
    merged = list(tier1)
    for d in tier2:
        if _base(d) not in t1_bases: merged.append(d)

    return set(merged), set(all_apps), set(all_files), set(all_folders), schedule_anywhere

def is_admin() -> bool:
    if os.name == "nt":
        try: return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception: return False
    return os.geteuid() == 0

def main() -> None:
    if os.name == "nt":
        cfg_path = os.path.join(os.getenv("PROGRAMDATA", r"C:\ProgramData"), "SimpleProductivityBlocker", "config.json")
    else:
        cfg_path = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "SimpleProductivityBlocker", "config.json")

    pm = ProcessMonitor()
    clm = CustomListManager()
    dns_server = None
    using_dns_proxy = False

    cur_domains: set = set()
    cur_apps:    set = set()
    cur_files:   set = set()
    cur_folders: set = set()

    cfg_cache:      dict = {}
    pending_mtime:  float = 0.0
    stable_mtime:   float = 0.0
    debounce:       int   = 0

    POLL_INTERVALS = {"Passive": 5, "Balanced": 2, "Strict": 1}

    def _notif(key, default=True):
        return cfg_cache.get("settings", {}).get("notifications", {}).get(key, default)

    try:
        while True:
            poll_sleep = POLL_INTERVALS.get(cfg_cache.get("settings", {}).get("performance_mode", "Balanced"), 2)
            try:
                mtime = os.path.getmtime(cfg_path) if os.path.exists(cfg_path) else 0.0
            except Exception:
                mtime = 0.0

            if mtime != pending_mtime:
                pending_mtime = mtime
                debounce = 0
            elif debounce < 3:
                debounce += 1

            if debounce == 3 and stable_mtime != mtime:
                stable_mtime = mtime
                cfg_cache = load_config()
                if _notif("on_config_reload", False): print("Config reloaded.")

            want_domains, want_apps, want_files, want_folders, sched_anywhere = _compute_targets(cfg_cache, clm)

            # --- DNS/Web Blocking ---
            if want_domains != cur_domains:
                if want_domains:
                    # Try DNS Proxy first
                    if not dns_server:
                        upstream = detect_system_dns()
                        dns_server = DNSProxyServer(list(want_domains), upstream_dns=upstream)
                        if dns_server.start():
                            using_dns_proxy = True
                            print("DNS Proxy Server active.")
                        else:
                            using_dns_proxy = False
                            print("Port 53 taken. Falling back to hosts-file.")
                    
                    if using_dns_proxy:
                        # Update existing DNS server matcher
                        dns_server.matcher = dns_server.matcher.__class__(list(want_domains))
                    else:
                        apply_blocks(list(want_domains), block_doh=sched_anywhere)
                    
                    if _notif("on_hosts_write", False):
                        print(f"Blocking {len(want_domains)} domain(s).")
                else:
                    if dns_server:
                        dns_server.stop()
                        dns_server = None
                    remove_blocks()
                    if _notif("on_hosts_write", False): print("All domains unblocked.")
                cur_domains = want_domains

            # --- App/File/Folder Blocking ---
            if want_apps != cur_apps or want_files != cur_files or want_folders != cur_folders or debounce == 3:
                cur_apps = want_apps
                cur_files = want_files
                cur_folders = want_folders
                
                settings = cfg_cache.get("settings", {})
                pm.set_allowlisted_processes(settings.get("cloud_allowlist", []), enabled=settings.get("cloud_allowlist_enabled", True))
                pm.set_allowlisted_keywords(settings.get("cloud_path_keywords", []))
                
                if cur_apps or cur_files or cur_folders:
                    pm.set_blocked_apps(list(cur_apps))
                    pm.set_blocked_files(list(cur_files))
                    pm.set_blocked_folders(list(cur_folders))
                    pm.start()
                else:
                    pm.stop()

            time.sleep(poll_sleep)

    except KeyboardInterrupt:
        if dns_server: dns_server.stop()
        remove_blocks()
        pm.stop()
        print("Daemon stopped.")

if __name__ == "__main__":
    if not is_admin():
        if os.name == "nt":
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
    main()
