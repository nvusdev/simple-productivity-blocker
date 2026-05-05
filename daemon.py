import os
import sys
import time
import ctypes
import zlib
import base64
import concurrent.futures

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Prevent crashing dependencies (redis/opentelemetry) from loading via portalocker/others
sys.modules['redis'] = None
sys.modules['opentelemetry'] = None
sys.modules['opentelemetry.context'] = None

if os.name == 'nt':
    try:
        import pywintypes
        import pythoncom
    except ImportError:
        pass

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

_ADULT = "eJwt0FtLwmAAxnFCGVbE6iKK6sLXzQNu7lDu4Glz27vt3cnpXAczJxQhoogJZjfpV4/Eyx//m4cH5Bn087UZyMPMM+WGt5PtvU9k5WARaL1VPIbix/cwB5qdRdtDB7+SkmDubdzdvG9ppE6b16vLE68RYYbYqhjkrBzPkYZ4ZGJcbmExJTFkz2JIR/00p1bajLTpgV73bWWatiJwKZlbW/nQcvl4jHEqe8SSksH6T92lbloKT6UUcR2BIIRC37GVLIMeZvVOBR9BTg8xICwskpL1ku6ethw7TdTqsDWTYBV3gwZKnPp+H4+qvuMvXS9dJKR2jhJxwneOmf7LCNToVK68dkAQoEYmSXZy0VBJzgGPmrdMou7BOK1nYMXTgxZJwM+C6M/P/TYXedqvUhxMBLHPeD17aZrmrlSFbFaM9v8ksEttgV6YUjFtXV389z8Qql00"
_GAMBLE = "eJwdzu1rgkAAx3HGQmIQ7R9YmF2zmZrnfNim5eHj6Z1eUSuD9nLRmEgEozfb/z64lz/48uMDbWfwd76Gs6r7cBzkufiqhp+PDm3WpPI2+4MpwduJYvXAKomUMkqtUVOByU82LNHSKzrEn7cMPL8kwx5eX2J2ANDjvVvg3M0y9ObrfEvpMgpYLRjB7EYG88ikDGndPFv8upEk++8tIvgSJ9R3G7z4MpiVbldwuxeccct06DC1KNA5KztHa4p05xrb/Q01MCGBzT2pzL3c86G4Wm1QhlT+D2r5ScPq7i6FRLj/PpmhKE77I5r/A7ERPFY="
_PIRACY = "eJwd0Mlu2kAAANBGWCkEIe5VD97A8XgBG2xjghnv23hnsQkVnCI1CkVVJEovqL9eiQ94l0ewWsPTU3fSC+LJU1MOB4NkiIO+6BedWX7I56T4RcdZkwrrrpAf0n9TISJ/cu7YDjKhvbMY5fz975/z7lyjDsjyZk5SO5GZNedka38eD/ubMX/Qac5hekX8uYl8CAetIX6puNispbJJIaQikbjao6yd6NbXXDaYw9tQTU5FYUJ09CEkfJG45oO6Xb9sEZrdRuGzMMtZs+4aUYCNqdOR5K4rpR/U0LOOMk14d1+WJR9EjkqebJ28pGxmldK6SQ1aakFw2YzKrTmuim83RXuQgFrw/pMvoUdP1vgQEkqfSqKOkkeOTEk7WuNcsa67IHo84DSwl+qiL2/bK6GKXuUJ23oG0x6xNROp8gJIndzBO7sa1SiWNxhaGOdXoC32vyy/K61TDJf4EH6AzalADgga9KJPwzce9OhkheA6MudDpkVryx7j/Sj54O5jwTAywU7Rb8/DlhB3GR4k99/YiacK3yLVS0XFnZRzsb36H6ukby0="

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
        "zoro.to", "aniwave.to", "aniwatch.to", "animepahe.ru",
        "gogoanime.pe", "gogoanime.hu", "kayoanime.com", "kaminari.to",
        "mangadex.org", "mangakakalot.com", "mangatoto.com", "manganelo.com",
        "readmanganato.com", "mangaone.com", "viz.com", "shonenjump.com",
        "manganato.com", "mangapark.net", "mangasee123.com", "mangaowl.net",
        "mangafreak.net", "mangareader.to", "anime-planet.com", "crunchyroll.it",
    ],
    "shopping": [
        "amazon.com", "temu.com", "ebay.com", "aliexpress.com",
        "shein.com", "walmart.com", "target.com", "bestbuy.com",
        "etsy.com", "wayfair.com", "wish.com", "alibaba.com",
        "zappos.com", "overstock.com", "newegg.com", "homedepot.com",
        "lowes.com", "costco.com", "samsclub.com", "macys.com",
        "nordstrom.com", "shopify.com", "zara.com", "hm.com",
        "craigslist.org", "mercari.com", "poshmark.com", "offerup.com",
        "fb.com/marketplace", "facebook.com/marketplace", "rakuten.com",
    ],
    "gaming": [
        "steampowered.com", "steamcommunity.com", "steamgames.com", 
        "epicgames.com", "gog.com", "uplay.com", "ubisoft.com", 
        "origin.com", "ea.com", "battle.net", "blizzard.com", 
        "roblox.com", "minecraft.net", "riotgames.com", "playvalorant.com", 
        "leagueoflegends.com", "humblebundle.com", "fanatical.com", 
        "greenmangaming.com", "instant-gaming.com", "cdkeys.com", 
        "g2a.com", "kinguin.net", "eneba.com", "itch.io", "gamejolt.com",
        "rockstargames.com", "socialclub.rockstargames.com", "nexusmods.com",
        "curseforge.com", "moddb.com", "speedrun.com", "discord.com",
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
    "piracy_illegal": _dec(_PIRACY),
    "adult_content":  _dec(_ADULT),
    "gambling":      _dec(_GAMBLE),
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
    all_exceptions: set[str] = set()
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
                    "gambling", "piracy_illegal", "entertainment", "shopping", "ai_tech", "gaming"]
            group_content: list[str] = []
            for k in keys:
                if ad.get(k):
                    val = ADBLOCK_LISTS[k]
                    if isinstance(val, list):
                        group_content.extend([d for d in val if isinstance(d, str)])
                    elif isinstance(val, str):
                        group_content.append(val)

            custom_paths = ad.get("custom_lists", [])
            if custom_paths:
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                    for res in ex.map(clm.get_domains_from_list, set(custom_paths)):
                        group_content.extend(res)

            raw_exc = ad.get("exceptions", [])
            exc_set = {_base(e) for e in raw_exc if e.strip()}
            all_exceptions.update(exc_set)
            if exc_set:
                group_content = [d for d in group_content if not _is_excepted(d, exc_set)]
            tier2.extend(group_content)

    t1_bases = {_base(d) for d in tier1}
    merged = list(tier1)
    for d in tier2:
        if _base(d) not in t1_bases: merged.append(d)

    return set(merged), set(all_apps), set(all_files), set(all_folders), all_exceptions, schedule_anywhere

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

            want_domains, want_apps, want_files, want_folders, want_exceptions, sched_anywhere = _compute_targets(cfg_cache, clm)

            # --- DNS/Web Blocking ---
            if want_domains != cur_domains or want_exceptions != getattr(dns_server, "cur_exc", None):
                if want_domains:
                    # Try DNS Proxy first
                    if not dns_server:
                        upstream = detect_system_dns()
                        dns_server = DNSProxyServer(list(want_domains), allowlist=list(want_exceptions), upstream_dns=upstream)
                        dns_server.cur_exc = want_exceptions
                        if dns_server.start():
                            using_dns_proxy = True
                            print("DNS Proxy Server active.")
                        else:
                            using_dns_proxy = False
                            print("Port 53 taken. Falling back to hosts-file.")
                    
                    if using_dns_proxy:
                        # Update existing DNS server matcher
                        dns_server.block_matcher = DomainMatcher(list(want_domains))
                        dns_server.allow_matcher = DomainMatcher(list(want_exceptions))
                        dns_server.cur_exc = want_exceptions
                    else:
                        apply_blocks(list(want_domains), block_doh=sched_anywhere)
                    
                    if _notif("on_hosts_write", False):
                        print(f"Blocking {len(want_domains)} domain(s) with {len(want_exceptions)} exceptions.")
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
