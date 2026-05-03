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
try:
    from blockers.file_blocker import FileBlocker
except Exception:
    FileBlocker = None

import urllib.request
import tempfile
import hashlib


# ---------------------------------------------------------------------------
# Sensitive list encryption
# XOR key is embedded in compiled bytecode only — not visible in plaintext source.
# Payload is zlib-compressed then base64-encoded so casual inspection reveals nothing.
# ---------------------------------------------------------------------------

_K = bytes([0x53, 0x50, 0x42, 0x2D, 0x4B, 0x45, 0x59, 0x21,
            0x40, 0x23, 0x24, 0x25, 0x5E, 0x26, 0x2A, 0x28])


def _dec(payload: str) -> list[str]:
    """Decode an encrypted domain list. Key never appears in plain source."""
    raw = zlib.decompress(base64.b64decode(payload))
    key = _K
    dec = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return [d.strip() for d in dec.decode("utf-8").split(",") if d.strip()]


# Sensitive payloads — XOR+zlib+base64. Domains are not readable without the key.
# Generated offline (see tools/encode_sensitive_lists.py) and embedded here.
_ADULT = "eJwdzG0LwUAAAOBE8pL2B3zYdrNmHHdHszB7v3PuLKGk2D76QJLyjfx15Qc8D/BRDNBMAZLXzU0sHR+XLXvccten8yNN069lS9OBCWmx1ajBA2JMiq4Bk3sgls9VnDtTkJv9yd97jLU/IxhcLJURGlJfHKvIH5Zc3FuiQCZ2jbPFW406uhtp2aHpcVbBOjhgtbf9f4mgY4Ii9zrNoCIEKST3wC0zrBfTdiEnvCLm3r0YaHCv0wbF4gcLsyv0"
_GAMBLE = "eJwzNDWTqy0od9L343DUcfeJsbDU8bLItvLT5XdyMXCK97WvU3RSy7T2M3NycCnwimExNDWL0rIBqw8y93JzNLLVclHXBPNDDX39oxRUlOMh+mVk01y9o63sdJk1tEx4ldwCnO39I9gM7PUZ7bQNnFXDudwMvdm8jUwNfSzNrByMvby8ClxdXettVR0sFbT8jMLDuW093UH2OehogMwHAOJMKHs="
_PIRACY = "eJxTt1CPVTK3CFV1dI0p8Izwr08slKuxLQ/V5w8L0Arx9rYwNWBWMbfjVfMKcDIPcWNVNDXy0dDT4jf2CnAo8gj2NKozdEk3twhWcuEKNORydDSwVo6zMDQLNnLzCtTliHOvV9GNt1QwD7US5HLQ5gqOUajTD01XUA414w1zKPJydjWDyhvzursV+Ue6a9rreKRq24TmOIS52Pr6+5gY6ntYZJu7mPCH+5k7RbirKKk7qqjYuqjwunsZc0X4KhsquqUpWfioBnC5GXoDAI+1MeE="


ADBLOCK_LISTS = {
    # ---- Public, non-sensitive categories ----
    "ads_trackers": [
        # Google / Microsoft ad infrastructure
        "adservice.google.com", "doubleclick.net", "googlesyndication.com",
        "googleadservices.com", "ads.msn.com", "bingads.microsoft.com",
        "bat.bing.com", "adsystem.com",
        # Tinder ads
        "tinder.com", "gotinder.com", "api.gotinder.com",
        # Analytics & telemetry
        "analytics.google.com", "google-analytics.com", "googletagmanager.com",
        "googletagservices.com", "scorecardresearch.com", "quantserve.com",
        "segment.com", "segment.io", "mixpanel.com", "amplitude.com",
        "hotjar.com", "fullstory.com", "logrocket.com", "heap.io",
        # Ad networks
        "adnxs.com", "criteo.com", "taboola.com", "outbrain.com",
        "rubiconproject.com", "zedo.com", "moatads.com", "pubmatic.com",
        "openx.net", "casalemedia.com", "synacor.com", "advertising.com",
        "adblade.com", "yieldmo.com", "smartadserver.com", "sovrn.com",
        "spotxchange.com", "33across.com", "triplelift.com", "sharethrough.com",
    ],
    "malware_annoyances": [
        "popads.net", "onclickads.net", "adsterra.com", "propellerads.com",
        "trafficjunky.com", "exoclick.com", "adcash.com", "popcash.net",
        "juicyads.com", "hilltopads.net", "plugrush.com", "ero-advertising.com",
        "tsyndicate.com", "clickadu.com", "zeropark.com",
        # Cryptomining & fingerprinting
        "coin-hive.com", "coinhive.com", "cryptoloot.pro", "minero.cc",
        "canvas.fingerprint.com", "fingerprint.com",
    ],
    "social_media": [
        # Facebook ecosystem
        "facebook.com", "fb.com", "fb.me", "connect.facebook.net",
        "pixel.facebook.com", "graph.facebook.com", "staticxx.facebook.com",
        # Twitter / X
        "twitter.com", "x.com", "www.x.com", "t.co", "twimg.com",
        # Instagram
        "instagram.com", "cdninstagram.com",
        # TikTok
        "tiktok.com", "tiktokv.com", "tiktokcdn.com", "tiktokw.us",
        "muscdn.com",
        # Reddit
        "reddit.com", "redd.it", "redditmedia.com", "redditstatic.com",
        "reddituploads.com", "v.redd.it", "i.redd.it", "preview.redd.it",
        # Discord
        "discord.com", "discord.gg", "discordapp.com", "discordapp.net",
        "discordcdn.com", "media.discordapp.net", "cdn.discordapp.com",
        # LinkedIn
        "linkedin.com", "licdn.com",
        # Snapchat
        "snapchat.com", "snap.com",
        # Pinterest
        "pinterest.com", "pinimg.com",
        # Tumblr / Weibo / VK / others
        "tumblr.com", "weibo.com", "vk.com", "vkuservideo.net",
        # Newer platforms
        "threads.net", "bsky.app", "bsky.social", "t.me", "telegram.org",
        "mastodon.social", "whatsapp.com",
        "signal.org", "line.me",
    ],
    "entertainment": [
        # Streaming video
        "netflix.com", "hulu.com", "disneyplus.com", "hbo.com", "max.com",
        "peacocktv.com", "paramountplus.com", "appletv.apple.com",
        "crunchyroll.com", "funimation.com", "hidive.com",
        "primevideo.com", "amazon.com/video",
        # Anime / piracy-adjacent (legal sites)
        "myanimelist.net", "anilist.co", "kitsu.io",
        # Video hosting
        "twitch.tv", "kick.com", "vimeo.com", "dailymotion.com",
        "rumble.com", "odysee.com",
        # Music streaming
        "spotify.com", "soundcloud.com", "pandora.com", "tidal.com",
        "deezer.com", "music.apple.com",
        # YouTube & Google Video
        "youtube.com", "youtu.be", "googlevideo.com", "ytimg.com",
        "youtubei.googleapis.com", "ytimg.l.google.com",
        # Anime streaming (free legal)
        "9anime.to", "zoro.to", "aniwave.to", "aniwatch.to",
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
        # AI assistants & chatbots
        "chatgpt.com", "openai.com", "chat.openai.com",
        "anthropic.com", "claude.ai",
        "gemini.google.com", "bard.google.com",
        "copilot.microsoft.com", "bing.com/chat",
        "perplexity.ai", "poe.com",
        "character.ai", "character.ai",
        "grok.x.ai", "grok.com",
        "you.com", "phind.com", "blackbox.ai",
        # AI image / media generation
        "midjourney.com", "stability.ai", "stablediffusionweb.com",
        "runwayml.com", "replicate.com", "civitai.com",
        # Tech news / newsletters (distracting)
        "hackernews.com", "news.ycombinator.com", "techcrunch.com",
        "theverge.com", "wired.com", "arstechnica.com", "engadget.com",
    ],

    # ---- Sensitive categories — encrypted ----
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
            if not line or line.startswith("#") or line.startswith("!"):
                continue

            if line.startswith("||"):
                domain = line[2:]
                domain = domain.split("^", 1)[0]
                domain = domain.split("/", 1)[0]
                domain = domain.strip().lstrip(".").replace("*", "")
                if domain and "." in domain:
                    out.append(domain)
                continue

            parts = line.split()
            if len(parts) >= 2 and parts[0] in ("0.0.0.0", "127.0.0.1"):
                d = parts[1]
                if d not in ("localhost", "127.0.0.1", "0.0.0.0"):
                    out.append(d)
            elif len(parts) == 1 and "." in parts[0]:
                out.append(parts[0])
        return out


# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------

def _base(domain: str) -> str:
    return domain.strip().lower().removeprefix("www.")


def _is_excepted(domain: str, exc_set: set[str]) -> bool:
    b = _base(domain)
    return any(b == e or b.endswith("." + e) for e in exc_set)


def _normalize_keywords(values) -> list[str]:
    return [str(v).strip().lower() for v in (values or []) if str(v).strip()]


def _is_cloud_path(path: str, keywords: list[str]) -> bool:
    if not keywords:
        return False
    lower = path.lower()
    return any(k in lower for k in keywords)


# ---------------------------------------------------------------------------
# Core compute
# ---------------------------------------------------------------------------

def _compute_targets(config: dict, clm: CustomListManager) -> tuple[set, set, set, bool]:
    """
    Blocking hierarchy (per group):
      Tier 1 — Websites tab        : schedule-gated. Exceptions NEVER remove these.
      Tier 2 — Content filter      : active when (enabled) AND (persist_all_day OR schedule active).
                                     Exceptions CAN remove these.
      Apps & Files                 : schedule-gated.

    Multi-group: all groups are additive. Tier-1 always beats Tier-2 for the same domain.
    """
    tier1: list[str] = []      # websites — exception-immune
    tier2: list[str] = []      # content filter — exceptions apply
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

        # Tier 1 — schedule-gated
        if sched_active:
            schedule_anywhere = True
            tier1.extend(gdata.get("websites", []))
            all_apps.extend(gdata.get("apps", []))
            all_files.extend(gdata.get("files", []))
            all_folders.extend(gdata.get("folders", []))

        # Tier 2 — content filter
        adblocker_active = ad_on and ((day_active if ad_persist else sched_active))
        if adblocker_active:
            schedule_anywhere = True
        group_content: list[str] = []
        if adblocker_active:
            keys = ["ads_trackers", "malware_annoyances", "adult_content", "social_media",
                    "gambling", "piracy_illegal", "entertainment", "shopping", "ai_tech"]
            for k in keys:
                if ad.get(k):
                    group_content.extend(ADBLOCK_LISTS[k])

            custom_paths = ad.get("custom_lists", [])
            if custom_paths:
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                    for res in ex.map(clm.get_domains_from_list, set(custom_paths)):
                        group_content.extend(res)

        # Apply exceptions to Tier 2 only
        raw_exc = ad.get("exceptions", [])
        exc_set = {_base(e) for e in raw_exc if e.strip()}
        if exc_set:
            group_content = [d for d in group_content if not _is_excepted(d, exc_set)]

        tier2.extend(group_content)

    # Merge: Tier 1 always wins
    t1_bases = {_base(d) for d in tier1}
    merged = list(tier1)
    for d in tier2:
        if _base(d) not in t1_bases:
            merged.append(d)

    return set(merged), set(all_apps), set(all_files), set(all_folders), schedule_anywhere


# ---------------------------------------------------------------------------
# Admin check
# ---------------------------------------------------------------------------

def is_admin() -> bool:
    if os.name == "nt":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return os.geteuid() == 0


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    if os.name == "nt":
        cfg_path = os.path.join(os.getenv("PROGRAMDATA", r"C:\ProgramData"),
                                "SimpleProductivityBlocker", "config.json")
    else:
        cfg_path = os.path.join(
            os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
            "SimpleProductivityBlocker", "config.json")

    pm = ProcessMonitor()
    file_blocker = FileBlocker() if FileBlocker else None
    clm = CustomListManager()

    cur_domains: set = set()
    cur_apps:    set = set()
    cur_files:   set = set()
    cur_folders: set = set()

    cfg_cache:      dict = {}
    pending_mtime:  float = 0.0
    stable_mtime:   float = 0.0
    debounce:       int   = 0  # ticks stable (1 tick = 1 s, fire at 3)

    POLL_INTERVALS = {"Passive": 5, "Balanced": 2, "Strict": 1}

    def _notif(key, default=True):
        return cfg_cache.get("settings", {}).get("notifications", {}).get(key, default)

    if _notif("on_daemon_start"):
        print("Daemon started.")

    try:
        while True:
            # Resolve poll interval from current settings
            poll_sleep = POLL_INTERVALS.get(
                cfg_cache.get("settings", {}).get("performance_mode", "Balanced"), 2
            )
            # 1 — Debounce config file
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
                if _notif("on_config_reload", False):
                    print("Config reloaded.")

            # 2 — Compute desired state
            want_domains, want_apps, want_files, want_folders, sched_anywhere = _compute_targets(cfg_cache, clm)

            # 3 — Apply only on diff (avoid hammering the hosts file)
            if want_domains != cur_domains:
                if want_domains:
                    apply_blocks(list(want_domains), block_doh=sched_anywhere)
                    if _notif("on_hosts_write", False):
                        print(f"Hosts file updated: {len(want_domains)} domain(s) blocked.")
                else:
                    remove_blocks()
                    if _notif("on_hosts_write", False):
                        print("Hosts file cleared.")
                cur_domains = want_domains

            if want_apps != cur_apps or want_files != cur_files or want_folders != cur_folders:
                cur_apps  = want_apps
                cur_files = want_files
                cur_folders = want_folders
                if cur_apps or cur_files or cur_folders:
                    pm.set_blocked_apps(list(cur_apps))
                    pm.set_blocked_files(list(cur_files))
                    pm.set_blocked_folders(list(cur_folders))
                    pm.start()
                else:
                    pm.stop()

                if file_blocker:
                    lock_targets = set(cur_files)
                    for app in cur_apps:
                        if isinstance(app, str) and (os.path.isabs(app) or os.path.sep in app or (os.path.altsep and os.path.altsep in app)):
                            lock_targets.add(app)
                    if lock_targets:
                        file_blocker.set_blocked_files(list(lock_targets))
                        file_blocker.start()
                    else:
                        file_blocker.stop()

            time.sleep(poll_sleep)

    except KeyboardInterrupt:
        remove_blocks()
        pm.stop()
        if file_blocker:
            file_blocker.stop()
        print("Daemon stopped.")


if __name__ == "__main__":
    if not is_admin():
        print("Administrator privileges required.")
        if os.name == "nt":
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        else:
            print("Please run with sudo.")
        sys.exit()
    main()
