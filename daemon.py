import sys
# Suppress problematic dependencies
sys.modules['redis'] = None
sys.modules['opentelemetry'] = None

import os
import json
import time
import ctypes
import logging
import threading
import psutil
import concurrent.futures
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime

# Local imports
try:
    from blockers.app_blocker import ProcessMonitor
    from blockers.website_blocker import apply_blocks, remove_blocks
    from blockers.dns_server import DNSProxyServer, detect_system_dns
except ImportError as e:
    import traceback
    print(f"IMPORT ERROR IN DAEMON: {e}")
    traceback.print_exc()
    ProcessMonitor = None
    apply_blocks = remove_blocks = lambda *a, **k: None
    DNSProxyServer = None

# Constants
if "SPB_DATA_DIR" in os.environ:
    base_data = os.environ["SPB_DATA_DIR"]
elif os.name == "nt":
    base_data = os.path.join(os.getenv("PROGRAMDATA", r"C:\ProgramData"), "SimpleProductivityBlocker")
else:
    base_data = os.path.expanduser("~/.config/SimpleProductivityBlocker")
os.makedirs(base_data, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(base_data, "daemon.log"), encoding='utf-8')
    ]
)
logger = logging.getLogger("SPB_Daemon")
print("Logging initialized")

RECOVERY_FILE = os.path.join(base_data, "recovery_history.json")

# Obfuscated Adblocker Lists
_X = bytes([0x53, 0x50, 0x42, 0x5F, 0x53, 0x45, 0x43, 0x55, 0x52, 0x45, 0x5F, 0x4B, 0x45, 0x59])
def _dec(data):
    if isinstance(data, list): return data
    try:
        dec = "".join(chr(b ^ _X[i % len(_X)]) for i, b in enumerate(data))
        return dec.split(",")
    except: return []

_ADULT = b"#?01;0!{1*2g=/:4'0 k :?i-.!-&2'q0*.y+**;*+=~!0>"
_GAMBLE = b"156lepm6=(ss}a#?):!k :?i/$.<!#6>!6m6=(s) -51+-}&,8"
_PIRACY = b"\'8\'/:7\"!7\'>2k6!7nn`vt-|10g78!2%q\'*o,&6q&="

ADBLOCK_LISTS = {
    "ads_trackers": _dec(b"\x1c\x01\x14\x0e\x02\x0e\x0e\x07\x04\x0b\x05\x0c\x0e\x0b\x1d\x03\x0e\x02\x15\x01\x0e\x0b\x03\x05\x14\x01\x0b\x03\x05"),
    "malware_annoyances": _dec(b"\x1c\x01\x14\x0e\x02\x0e\x0e\x07\x04\x0b\x05\x0c\x0e\x0b\x1d\x03\x0e\x02\x15\x01\x0e\x0b\x03\x05\x14\x01\x0b\x03\x06"),
    "social_media": _dec(b"\x1c\x01\x14\x0e\x02\x0e\x0e\x07\x04\x0b\x05\x0c\x0e\x0b\x1d\x03\x0e\x02\x15\x01\x0e\x0b\x03\x05\x14\x01\x0b\x03\x07"),
    "entertainment": _dec(b"\x1c\x01\x14\x0e\x02\x0e\x0e\x07\x04\x0b\x05\x0c\x0e\x0b\x1d\x03\x0e\x02\x15\x01\x0e\x0b\x03\x05\x14\x01\x0b\x03\x08"),
    "shopping": _dec(b"\x1c\x01\x14\x0e\x02\x0e\x0e\x07\x04\x0b\x05\x0c\x0e\x0b\x1d\x03\x0e\x02\x15\x01\x0e\x0b\x03\x05\x14\x01\x0b\x03\x09"),
    "gaming": _dec(b"\x1c\x01\x14\x0e\x02\x0e\x0e\x07\x04\x0b\x05\x0c\x0e\x0b\x1d\x03\x0e\x02\x15\x01\x0e\x0b\x03\x05\x14\x01\x0b\x03\x0a"),
    "ai_tech": _dec(b"\x1c\x01\x14\x0e\x02\x0e\x0e\x07\x04\x0b\x05\x0c\x0e\x0b\x1d\x03\x0e\x02\x15\x01\x0e\x0b\x03\x05\x14\x01\x0b\x03\x0b"),
    "piracy_illegal": _dec(_PIRACY),
    "adult_content":  _dec(_ADULT),
    "gambling":      _dec(_GAMBLE),
}

class CustomListManager:
    def __init__(self):
        self.cache_dir = os.path.join(base_data, "list_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self._domain_cache = {}

    def get_domains_from_list(self, list_path: str, cfg_path: str) -> list[str]:
        # Block UNC paths and other non-standard paths
        if list_path.startswith("\\\\"): return []
        
        is_url = list_path.startswith(("http://", "https://"))
        if is_url:
            try:
                parsed = urllib.parse.urlparse(list_path)
                host = (parsed.hostname or "").lower()
                # Hardened SSRF: Resolve to IP
                import socket
                ip = socket.gethostbyname(host)
                if any(ip.startswith(p) for p in ["127.", "169.254.", "10.", "172.16.", "192.168.", "::1", "0:0:0:0:0:0:0:1"]):
                    return []
            except: pass
        elif "://" in list_path: return []

        now = time.time()
        # Security: Check for symlinks and restrict local paths to config dir
        if os.path.islink(list_path): return []
        if "://" not in list_path:
            abs_path = os.path.abspath(list_path)
            if not abs_path.startswith(os.path.dirname(os.path.abspath(cfg_path))):
                return [] # Block arbitrary local file reads
        
        mtime = os.path.getmtime(list_path) if os.path.exists(list_path) and "://" not in list_path else 0
        cache_file = os.path.join(base_data, "list_cache", hashlib.md5(list_path.encode()).hexdigest() + ".txt")
        
        if os.path.exists(cache_file):
            if os.path.islink(cache_file): # Security: Block cache symlink traps
                try: os.remove(cache_file)
                except: return []
            
            if now - os.path.getmtime(cache_file) < 3600: # 1h cache
                if list_path in self._domain_cache:
                    cached_mtime, cached_domains, last_check = self._domain_cache[list_path]
                    if (mtime == cached_mtime or "://" in list_path) and (now - last_check) < 300:
                        return cached_domains

        try:
            domains = []
            if "://" in list_path:
                uid = hashlib.md5(list_path.encode()).hexdigest()
                cache = os.path.join(self.cache_dir, f"{uid}.txt")
                if os.path.exists(cache) and (now - os.path.getmtime(cache)) < 86400:
                    domains = self._parse_file(cache)
                else:
                    req = urllib.request.Request(list_path, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=10) as r:
                        # Security: Limit read to 10MB to prevent OOM
                        content = r.read(10 * 1024 * 1024).decode('utf-8', errors='ignore')
                    with open(cache, "w", encoding="utf-8") as f:
                        f.write(content)
                    domains = self._parse_content(content)
            elif os.path.exists(list_path):
                domains = self._parse_file(list_path)
            
            self._domain_cache[list_path] = (mtime, domains, now)
            return domains
        except: return []

    def _parse_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f: return self._parse_content(f.read())
        except: return []

    def _parse_content(self, content):
        out = []
        for line in content.splitlines():
            line = line.split('#')[0].split('!')[0].strip().lower()
            if not line: continue
            
            # Handle Adblock/Hosts formats
            line = line.removeprefix("||").removesuffix("^").removeprefix("127.0.0.1 ").removeprefix("0.0.0.0 ")
            line = line.strip().removeprefix("www.")
            
            if line and "." in line:
                out.append(line)
        return list(set(out))

def is_day_active(schedule):
    if not schedule.get("enabled", False): return True
    if schedule.get("always", False): return True
    day_name = datetime.now().strftime("%A")
    days = schedule.get("days", [])
    if isinstance(days, list) and day_name in days:
        return True
    return schedule.get(day_name, False)

def is_active(group):
    if not group.get("enabled", True): return False
    schedule = group.get("schedule", {})
    if not schedule.get("enabled", False): return True
    if not is_day_active(schedule): return False
    
    if schedule.get("persist_all_day", False): return True
    
    now = datetime.now().time()
    start_str = schedule.get("start_time", schedule.get("start", "00:00"))
    end_str = schedule.get("end_time", schedule.get("end", "23:59"))
    try:
        start = datetime.strptime(start_str, "%H:%M").time()
        end = datetime.strptime(end_str, "%H:%M").time()
        if start <= end: return start <= now <= end
        else: return now >= start or now <= end # Overnight
    except: return True

def _base(domain):
    return domain.strip().lower().removeprefix("www.")

def _is_excepted(domain, exceptions):
    if not domain or not exceptions: return False
    b = _base(domain)
    return any(b == e or b.endswith("." + e) for e in exceptions)

def _compute_targets(config, clm, cfg_path):
    cfg_dir = os.path.dirname(cfg_path)
    tier1, tier2 = [], []
    all_apps, all_files, all_folders = set(), set(), set()
    all_exceptions = set()
    schedule_anywhere = False
    custom_lists = set()

    for _, gdata in config.get("groups", {}).items():
        if not gdata.get("enabled", True): continue
        active = is_active(gdata)
        ad = gdata.get("adblocker", {})
        ad_on = ad.get("enabled", False)
        ad_persist = ad.get("persist_all_day", False)
        day_on = is_day_active(gdata.get("schedule", {}))
        
        # Adblocker is active if enabled AND (it's the active day AND (persist-all-day OR current time is active))
        ad_active = ad_on and day_on and (ad_persist or active)

        if active or ad_active:
            all_exceptions.update({_base(e) for e in gdata.get("exceptions", []) if e.strip()})
            all_exceptions.update({_base(e) for e in ad.get("exceptions", []) if e.strip()})

        if active:
            schedule_anywhere = True
            tier1.extend(gdata.get("websites", []))
            for a in gdata.get("apps", []): 
                if a.strip(): all_apps.add(a.strip())
            for f in gdata.get("files", []):
                if not f.strip(): continue
                p = f if os.path.isabs(f) else os.path.join(cfg_dir, f)
                all_files.add(os.path.normpath(p))
            for f in gdata.get("folders", []):
                if not f.strip(): continue
                p = f if os.path.isabs(f) else os.path.join(cfg_dir, f)
                all_folders.add(os.path.normpath(p))

        if ad_active:
            schedule_anywhere = True
            for k in ["ads_trackers", "malware_annoyances", "social_media", "entertainment", "shopping", "gaming", "ai_tech", "piracy_illegal", "adult_content", "gambling"]:
                if ad.get(k): tier2.extend(ADBLOCK_LISTS.get(k, []))
            for cp in ad.get("custom_lists", []): 
                if cp.strip(): custom_lists.add(cp.strip())

    # Custom lists are handled in background by CustomListManager
    return set(tier1), set(tier2), all_apps, all_files, all_folders, all_exceptions, schedule_anywhere, custom_lists

def _async_fetch_lists(clm, lists, callback, cfg_path):
    """Fetches custom lists in background and ensures callback is always called."""
    all_domains = set()
    try:
        for lp in lists:
            all_domains.update(clm.get_domains_from_list(lp, cfg_path))
    except Exception as e:
        logger.error(f"Async fetch error: {e}")
    finally:
        callback(all_domains)

def _get_history():
    h = set()
    for f in ["recovery.json", "recovery_history.json"]:
        p = os.path.join(base_data, f)
        if os.path.exists(p):
            try:
                with open(p, "r") as fobj: h.update(json.load(fobj))
            except: pass
    return h

def _save_history(current_set):
    try:
        with open(RECOVERY_FILE, "w") as f: json.dump(list(current_set), f)
    except: pass

def _boot_sweep_task(initial_targets, pm_instance):
    """Reconciles historical locks against current config on startup."""
    lock_history = _get_history()
    if not lock_history: return
    
    logger.info(f"Failsafe Boot Sweep: Re-verifying {len(lock_history)} locks...")
    for path in lock_history:
        p = os.path.normpath(path)
        if p in initial_targets and os.path.exists(p):
            pm_instance.synchronize_lock(p, True)
    logger.info("Boot Sweep complete.")

def is_admin():
    if os.name == "nt":
        try: return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except: return False
    return os.geteuid() == 0

def kill_other_instances():
    me = os.getpid()
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if p.info['pid'] == me: continue
            if p.info['name'] == "SPB_Daemon.exe" or ("python" in p.info['name'].lower() and "daemon.py" in " ".join(p.info['cmdline'] or [])):
                p.kill()
        except: pass

def main():
    print("Daemon main() started")
    # kill_other_instances()
    cfg_path = os.path.join(base_data, "config.json")
    if not ProcessMonitor:
        logger.error("Critical: ProcessMonitor could not be loaded. Exiting.")
        return

    pm = ProcessMonitor()
    clm = CustomListManager()
    dns_server = None
    
    cur_domains = set()
    cur_apps = set()
    cur_files = set()
    cur_folders = set()
    cur_exceptions = set()
    want_custom = set() # Persistent async state
    targets_dirty = False # Efficiency flag
    using_dns_proxy = False
    
    last_cfg_mtime = 0
    last_minute = -1
    cached_targets = None
    stable_mtime = pending_mtime = 0.0
    debounce = 0
    last_admin_check = 0.0
    
    first_run = True

    logger.info("Productivity Daemon v1.4.1 started.")

    while True:
        try:
            now = time.time()
            current_minute = time.localtime(now).tm_min
            
            try: mtime = os.path.getmtime(cfg_path) if os.path.exists(cfg_path) else 0.0
            except: mtime = 0.0

            config_changed = False
            if mtime != pending_mtime:
                pending_mtime = mtime
                debounce = 0
            elif debounce < 2:
                debounce += 1
            
            if (debounce == 2 and stable_mtime != mtime) or first_run:
                stable_mtime = mtime
                try:
                    with open(cfg_path, "r") as f: cfg_cache = json.load(f)
                    config_changed = True
                    logger.info("Config loaded.")
                except: 
                    if first_run:
                        logger.warning("Initial config not found or invalid. Using empty config.")
                        cfg_cache = {"groups": {}, "settings": {}}
                        config_changed = True
                    else:
                        logger.error("Failed to reload config. Using last known good config.")

            if config_changed or current_minute != last_minute or first_run:
                last_minute = current_minute
                cached_targets = _compute_targets(cfg_cache, clm, cfg_path)
                want_manual, want_filters, want_apps, want_files, want_folders, want_exceptions, sched_anywhere, custom_lists = cached_targets
                want_domains = want_manual.union(want_filters).union(want_custom)
                targets_dirty = True
                
                # Async fetch for custom lists with concurrency guard
                if custom_lists and not getattr(clm, "_is_fetching", False):
                    clm._is_fetching = True
                    def _on_custom_load(res):
                        nonlocal want_custom, targets_dirty
                        want_custom = res
                        targets_dirty = True
                        clm._is_fetching = False
                    threading.Thread(target=_async_fetch_lists, args=(clm, custom_lists, _on_custom_load, cfg_path), daemon=True).start()
            
            # Protective access
            if not cached_targets:
                time.sleep(1)
                continue

            if first_run:
                # Safe Boot Sequence
                settings = cfg_cache.get("settings", {})
                pm.set_allowlisted_processes(settings.get("cloud_allowlist", []))
                pm.set_allowlisted_keywords(settings.get("cloud_path_keywords", []))
                
                app_paths = {a for a in want_apps if os.path.sep in a or (os.name == 'nt' and '/' in a)}
                initial_targets = want_files.union(want_folders).union(app_paths)
                threading.Thread(target=_boot_sweep_task, args=(initial_targets, pm), daemon=True).start()
                # first_run = False # Moved to end

            # Update Logic...
            if first_run or config_changed or want_exceptions != cur_exceptions:
                # Update Allowlists
                settings = cfg_cache.get("settings", {})
                comb_allow = set(settings.get("cloud_allowlist", [])).union(want_exceptions)
                pm.set_allowlisted_processes(list(comb_allow))
                pm.set_allowlisted_keywords(settings.get("cloud_path_keywords", []))
                pm.configure_performance(settings.get("performance_mode", "Balanced"))

            # DNS/Hosts logic...
            if first_run or config_changed or targets_dirty or want_domains != cur_domains or want_exceptions != cur_exceptions:
                targets_dirty = False
                if want_domains:
                    if not dns_server:
                        dns_server = DNSProxyServer(list(want_manual), list(want_filters), allowlist=list(want_exceptions), upstream_dns=detect_system_dns())
                        if dns_server.start():
                            using_dns_proxy = True
                            remove_blocks()
                        else:
                            dns_server = None; using_dns_proxy = False
                    
                    if using_dns_proxy: 
                        dns_server.update_rules(list(want_manual), list(want_filters.union(want_custom)), list(want_exceptions))
                    else: 
                        apply_blocks([d for d in want_domains if not _is_excepted(d, want_exceptions)], block_doh=sched_anywhere)
                else:
                    if dns_server: dns_server.stop(); dns_server = None
                    remove_blocks()
                cur_domains = set(want_domains)
                cur_exceptions = set(want_exceptions)

            # App/File logic...
            if first_run or config_changed or want_apps != cur_apps or want_files != cur_files or want_folders != cur_folders:
                pm.set_blocked_apps(list(want_apps))
                pm.set_blocked_files(list(want_files))
                pm.set_blocked_folders(list(want_folders))
                
                app_paths = {a for a in want_apps if os.path.sep in a or (os.name == 'nt' and '/' in a)}
                _save_history(want_files.union(want_folders).union(app_paths))
                
                if want_apps or want_files or want_folders: pm.start()
                else: pm.stop()
                
                cur_apps, cur_files, cur_folders = want_apps, want_files, want_folders

            if (now - last_admin_check) >= 60.0:
                logger.info(f"Heartbeat: [Admin={is_admin()}] [Active={pm.is_active}]")
                last_admin_check = now

            first_run = False
            poll_sleep = {"Passive": 5, "Balanced": 2, "Strict": 0.5}.get(cfg_cache.get("settings", {}).get("performance_mode", "Balanced"), 2)
            time.sleep(poll_sleep)
        except Exception:
            logger.exception("LOOP CRASH detected in main daemon cycle:")
            time.sleep(5)

if __name__ == "__main__":
    if os.name == "nt" and not is_admin() and "SPB_DATA_DIR" not in os.environ:
        # Re-launch with admin rights using safe quoting
        import subprocess
        params = subprocess.list2cmdline(sys.argv)
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        except: pass
        sys.exit(0)
    main()
