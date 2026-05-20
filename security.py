import os
import hashlib
import time
import urllib.request
import urllib.parse
import logging
import socket

logger = logging.getLogger("SPB_Security")

# Obfuscated Adblocker Lists
_X = bytes([0x53, 0x50, 0x42, 0x5F, 0x53, 0x45, 0x43, 0x55, 0x52, 0x45, 0x5F, 0x4B, 0x45, 0x59])

def _dec(data):
    if isinstance(data, list): return data
    try:
        dec = "".join(chr(b ^ _X[i % len(_X)]) for i, b in enumerate(data))
        return dec.split(",")
    except: return []

_PIRACY = b'\'8\'/:7"!7\'>2k6!7nn`vt-|10g78!2%q\'*o,&6q&=u6*%:\'$m6=(s-,-4903~7&%3&48k*:$\'s7*\'<\x7f7:;$:8#l,:1&y 0r)*8!4l<<(o\'\'1-*&26"l0!"o;+$>e60\x7f1,6> 7:!-0e*+4|26!$700$&e58!$;s\'-&=;!;.+;2)l<<(o&1 1.10>5l<<(o<"1097<=$1q0*.y&*-9 7\'4#&}&,8~1097<=$.:6&+{=78'
_ADULT = b'6fpn}+&!~7*\' jg~:\'+i1 > l\x7fk)28\'>?k-0&i8.);<?0*}&,8~7:*);<?0*}&,8~1="\'w<"%s+\',: 0q(*4\x7f8\'1\'$*x4**%!+*~!0>i3: +7>\'w0?/s+3*17*,e&6>|:1+=m6=(s9 =\'% :}&,8~<0>56!>l<<(o!\'\':sk:<=n\';$.&& -e&6>|!7216\'0$+.k:<=n0=):33+,e&6>|$>=6/,|&0&i:2=vq0*.y>,)./8 =+1}&,8~\'0%"801/,}&,8~6+9,)08#+}&,8~6/*+211,8}&,8~(0?-<!<\', k :?'
_GAMBLE = b' $#46k :?i-$*;6$l<<(o771l}pw0?/sk}{%=.:9k:<=n/<.&\'!1>96w0?/s$,/9;$2#,5?~!0>i/46\'-$.< ~!0>i!";+q(*4\x7f%,61 7{1*2g}ak3#,:+,{1*2g\'<\'\'#&}&,8~!-*#-89,8 k :?i9*+=&5.q0*.y"*4.7*\'10,}+&!~/>(.)<$!6\'<m6=('

ADBLOCK_LISTS = {
    "ads_trackers": [
        "doubleclick.net", "googleadservices.com", "ads.google.com", "adservice.google.com",
        "adnxs.com", "rubiconproject.com", "pubmatic.com", "openx.net", "casalemedia.com",
        "advertising.com", "yieldmo.com", "indexww.com", "mookie1.com", "quantserve.com",
        "scorecardresearch.com", "taboola.com", "outbrain.com", "criteo.com", "amazon-adsystem.com",
        "adform.net", "adroll.com", "adzerk.net", "bidswitch.net", "carbonads.net", "media.net",
        "moatads.com", "revcontent.com", "smartadserver.com", "sovrn.com", "doubleclick.com",
        "googlesyndication.com", "adnxs.com"
    ],
    "malware_annoyances": ["coinhive.com", "miner.com", "malware.com", "phish.com", "antivirus-update.com"],
    "social_media": [
        "facebook.com", "fb.com", "instagram.com", "twitter.com", "x.com", "linkedin.com",
        "tiktok.com", "snapchat.com", "reddit.com", "pinterest.com", "tumblr.com", "discord.com",
        "threads.net", "mastodon.social", "bluesky.social"
    ],
    "entertainment": [
        "netflix.com", "hulu.com", "disneyplus.com", "hbomax.com", "twitch.tv", "youtube.com",
        "music.youtube.com", "vimeo.com", "dailymotion.com", "crunchyroll.com", "paramountplus.com",
        "peacocktv.com", "youtube-nocookie.com", "googlevideo.com"
    ],
    "shopping": [
        "amazon.com", "ebay.com", "walmart.com", "target.com", "bestbuy.com", "aliexpress.com",
        "etsy.com", "shopify.com", "temu.com", "shein.com", "wish.com"
    ],
    "gaming": [
        "steamcommunity.com", "steampowered.com", "epicgames.com", "roblox.com", "minecraft.net",
        "battle.net", "leagueoflegends.com", "ryuugames.com", "ign.com", "gamespot.com", "kotaku.com",
        "curseforge.com", "nexusmods.com", "ea.com", "ubisoft.com", "nintendo.com", "playstation.com",
        "xbox.com", "blizzard.com", "riotgames.com", "gog.com"
    ],
    "ai_tech": [
        "chatgpt.com", "openai.com", "anthropic.com", "claude.ai", "perplexity.ai", "midjourney.com",
        "deepseek.com", "mistral.ai", "cohere.com", "labs.google", "gemini.google.com", "character.ai"
    ],
    "music_podcasts": [
        "spotify.com", "soundcloud.com", "music.apple.com", "podcasts.apple.com", "deezer.com",
        "tidal.com", "pandora.com", "music.amazon.com", "bandcamp.com", "podcasts.google.com",
        "mixcloud.com", "tunein.com"
    ],
    "piracy_illegal": _dec(_PIRACY), # Includes piracy, torrents, etc.
    "adult_content":  _dec(_ADULT),  # Obfuscated adult content filter list
    "gambling":      _dec(_GAMBLE), # Sensitive/Explicit/Illegal -> Encrypted
}

import http.client

class BoundHTTPConnection(http.client.HTTPConnection):
    def __init__(self, target_ip, host, *args, **kwargs):
        self.target_ip = target_ip
        super().__init__(host, *args, **kwargs)

    def connect(self):
        self.sock = self._create_connection(
            (self.target_ip, self.port), self.timeout, self.source_address
        )
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if self._tunnel_host:
            self._tunnel()

class BoundHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, target_ip, host, *args, **kwargs):
        self.target_ip = target_ip
        super().__init__(host, *args, **kwargs)

    def connect(self):
        self.sock = self._create_connection(
            (self.target_ip, self.port), self.timeout, self.source_address
        )
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if self._tunnel_host:
            self._tunnel()
        try:
            server_hostname = self._tunnel_host if self._tunnel_host else self.host
            self.sock = self.context.wrap_socket(self.sock, server_hostname=server_hostname)
        except Exception:
            self.sock.close()
            raise

class BoundHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, target_ip):
        super().__init__()
        self.target_ip = target_ip
    def http_open(self, req):
        return self.do_open(lambda host, **kw: BoundHTTPConnection(self.target_ip, host, **kw), req)

class BoundHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, target_ip, context=None):
        super().__init__(context=context)
        self.target_ip = target_ip
    def https_open(self, req):
        return self.do_open(lambda host, **kw: BoundHTTPSConnection(self.target_ip, host, **kw), req,
            context=self._context, check_hostname=self._check_hostname)

class CustomListManager:
    def __init__(self, base_data):
        self.base_data = base_data
        self.cache_dir = os.path.join(base_data, "list_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self._domain_cache = {}
        self._last_fetch_times = {} # Throttle storage

    def get_domains_from_list(self, list_path: str, cfg_path: str) -> list[str]:
        now = time.time()
        # Throttling: prevent redundant fetching (300s cooldown)
        if list_path in self._last_fetch_times:
            if now - self._last_fetch_times[list_path] < 300:
                if list_path in self._domain_cache:
                    return self._domain_cache[list_path][1]

        # Block UNC paths and other non-standard paths
        if list_path.startswith("\\\\"): return []
        
        is_url = list_path.startswith(("http://", "https://"))
        fetch_host = None
        target_ip = None
        actual_url = list_path

        if is_url:
            try:
                parsed = urllib.parse.urlparse(list_path)
                host = (parsed.hostname or "").lower()
                # Hardened SSRF: Resolve once to prevent DNS rebinding
                try:
                    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
                    infos = socket.getaddrinfo(host, port)
                    for info in infos:
                        ip = info[4][0]
                        # Block local, loopback, link-local, and private ranges
                        if ip.startswith(("127.", "169.254.", "10.", "172.16.", "192.168.", "::1", "fc00:", "fe80:")) or ip == "0.0.0.0":
                            logger.warning(f"SSRF Prevention: Blocked access to {ip} for {host}")
                            return []
                        if not target_ip:
                            target_ip = ip
                    
                    if target_ip:
                        fetch_host = host
                except Exception as e:
                    logger.debug(f"SSRF DNS check failed: {e}")
                    pass
            except Exception as e:
                logger.error(f"Error parsing list URL {list_path}: {e}")
                return []
        elif "://" in list_path: return []

        # Security: Check for symlinks and restrict local paths to config dir
        if "://" not in list_path:
            if os.path.islink(list_path): return []
            abs_path = os.path.abspath(list_path)
            if not abs_path.startswith(os.path.dirname(os.path.abspath(cfg_path))):
                return [] # Block arbitrary local file reads
            mtime = os.path.getmtime(list_path) if os.path.exists(list_path) else 0
        else:
            mtime = 0
        
        cache_file = os.path.join(self.base_data, "list_cache", hashlib.md5(list_path.encode()).hexdigest() + ".txt")
        
        if os.path.exists(cache_file):
            if os.path.islink(cache_file): # Security: Block cache symlink traps
                try: os.remove(cache_file)
                except: return []

        try:
            self._last_fetch_times[list_path] = now
            domains = []
            if "://" in list_path:
                uid = hashlib.md5(list_path.encode()).hexdigest()
                cache = os.path.join(self.cache_dir, f"{uid}.txt")
                if os.path.exists(cache) and (now - os.path.getmtime(cache)) < 86400:
                    domains = self._parse_file(cache)
                else:
                    # Fetching...
                    req = urllib.request.Request(actual_url, headers={"User-Agent": "Mozilla/5.0"})
                    if fetch_host:
                        req.add_header("Host", fetch_host)
                    
                    if fetch_host and target_ip:
                        import ssl
                        ctx = ssl.create_default_context()
                        opener = urllib.request.build_opener(
                            BoundHTTPHandler(target_ip),
                            BoundHTTPSHandler(target_ip, context=ctx)
                        )
                        r = opener.open(req, timeout=10)
                    else:
                        r = urllib.request.urlopen(req, timeout=10)
                    
                    with r:
                        content = r.read(10 * 1024 * 1024).decode('utf-8', errors='ignore')
                    with open(cache, "w", encoding="utf-8") as f:
                        f.write(content)
                    domains = self._parse_content(content)
            else:
                if os.path.exists(list_path):
                    domains = self._parse_file(list_path)
            
            self._domain_cache[list_path] = (mtime, domains, now)
            return domains
        except Exception as e:
            logger.error(f"Error loading list {list_path}: {e}")
            return []

    def _parse_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return self._parse_content(f.read())
        except: return []

    def _parse_content(self, content):
        domains = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "!", "||")): continue
            if " " in line: line = line.split(" ")[1] # hosts format
            domains.append(line.lower())
        return list(set(domains))
