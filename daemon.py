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
import socket
import psutil
import concurrent.futures
import urllib.request
import urllib.parse
import traceback
import dataclasses
import site
from datetime import datetime
from typing import List, Optional, Set, Any, Dict, Tuple, Union

# Local imports
from security import ADBLOCK_LISTS, CustomListManager
from core.config_manager import load_config
from core.scheduler import is_active, is_day_active

# SYSTEM SAFETY EXCLUSIONS - Absolute bypass for core OS processes
SYSTEM_SAFETY_EXCLUSIONS = {
    "explorer.exe", "taskmgr.exe", "services.exe", "lsass.exe", "csrss.exe",
    "wininit.exe", "winlogon.exe", "spoolsv.exe", "svchost.exe", "notepad.exe",
    "python.exe", "SimpleProductivityBlocker.exe", "SPB_Daemon.exe", "spb_installer.exe"
}

def _harden_runtime_paths():
    if not getattr(sys, "frozen", False):
        return
    try:
        user_site = site.getusersitepackages()
        if user_site in sys.path:
            sys.path.remove(user_site)
    except Exception:
        pass
    for entry in ("", ".", os.getcwd()):
        while entry in sys.path:
            sys.path.remove(entry)

_harden_runtime_paths()

# Define internal fallbacks with explicit defaults to prevent startup NameErrors
from core.platform_handler import get_platform_handler
handler = get_platform_handler()

_INTERNAL_HOSTS_FILE = handler.get_hosts_path()

# Global references for subsystems
ProcessMonitor = None
DNSProxyServer = None
HOSTS_FILE = _INTERNAL_HOSTS_FILE
apply_blocks = None
remove_blocks = None
apply_browser_policies = None
sync_website_protection = None
flush_dns = None
detect_system_dns = None

try:
    from blockers.app_blocker import ProcessMonitor
    from blockers.website_blocker import (
        apply_blocks as _apply_blocks, 
        remove_blocks as _remove_blocks, 
        apply_browser_policies as _apply_policies, 
        sync_website_protection as _sync_protect, 
        HOSTS_FILE as _REAL_HOSTS_FILE, 
        flush_dns as _flush_dns
    )
    from blockers.dns_server import DNSProxyServer, detect_system_dns as _detect_dns, detect_conflicting_services as _detect_conflicts
    
    # Successfully imported - bind to the global names used in the orchestrator
    apply_blocks = _apply_blocks
    remove_blocks = _remove_blocks
    apply_browser_policies = _apply_policies
    sync_website_protection = _sync_protect
    HOSTS_FILE = _REAL_HOSTS_FILE
    flush_dns = _flush_dns
    detect_system_dns = _detect_dns
    detect_conflicting_services = _detect_conflicts
except ImportError as e:
    # --- FAIL-CLOSED HARDENING ---
    logger = logging.getLogger("SPB_Daemon")
    logger.critical(f"FATAL: Protection modules failed to load: {e}")
    
    # Signal failure to health monitor
    try:
        base_data = handler.get_data_dir()
        os.makedirs(base_data, exist_ok=True)
        with open(os.path.join(base_data, "dns_health.signal"), "w") as f:
            f.write("CRITICAL ERROR")
    except: pass
    
    # Native Notification
    if os.name == 'nt' and os.environ.get("SPB_GHOST_MODE") != "1":
        try:
            msg = f"Simple Productivity Blocker cannot start because a critical protection module is missing or corrupted.\n\nError: {e}\n\nPlease reinstall the application."
            ctypes.windll.user32.MessageBoxW(0, msg, "SPB - Critical Startup Error", 0x10) # 0x10 = MB_ICONERROR
        except: pass
    
    sys.exit(1)

# Constants
if "SPB_DATA_DIR" in os.environ:
    base_data = os.environ["SPB_DATA_DIR"]
else:
    base_data = handler.get_data_dir()
os.makedirs(base_data, exist_ok=True)

log_file = os.path.join(base_data, "daemon.log")
try:
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
except PermissionError:
    try:
        # Fallback to temp directory if ProgramData is read-only for this user
        import tempfile
        log_file = os.path.join(tempfile.gettempdir(), "spb_daemon_fallback.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
    except Exception:
        # If even temp fails, use null handler to prevent crash
        file_handler = logging.NullHandler()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        file_handler
    ]
)
logger = logging.getLogger("SPB_Daemon")
logger.info(f"Logging initialized (Target: {log_file})")

RECOVERY_FILE = os.path.join(base_data, "recovery_history.json")

# Security & Lists initialized in security.py
clm = CustomListManager(base_data)

NORMALIZED_FILTER_MAP = {
    "ads_trackers": [
        "doubleclick.net", "googleadservices.com", "googlesyndication.com", 
        "adnxs.com", "taboola.com", "outbrain.com", "criteo.com", "ads.google.com"
    ],
    "malware_annoyances": [
        "coinhive.com", "miner.com", "cryptobloot.com", "popads.net", "propellerads.com"
    ],
    "social_media": [
        "facebook.com", "fb.com", "instagram.com", "x.com", "twitter.com", "tiktok.com", 
        "reddit.com", "discord.com", "linkedin.com", "pinterest.com", "threads.net"
    ],
    "entertainment": [
        "youtube.com", "music.youtube.com", "netflix.com", "twitch.tv", "googlevideo.com", 
        "vimeo.com", "dailymotion.com", "disneyplus.com", "crunchyroll.com"
    ],
    "shopping": [
        "amazon.com", "ebay.com", "walmart.com", "target.com", "bestbuy.com", "aliexpress.com"
    ],
    "gaming": [
        "steampowered.com", "roblox.com", "epicgames.com", "minecraft.net", "nintendo.com", "playstation.com"
    ],
    "ai_tech": [
        "chatgpt.com", "openai.com", "claude.ai", "anthropic.com", "perplexity.ai", 
        "gemini.google.com", "midjourney.com", "deepseek.com"
    ],
    "piracy_illegal": [
        "thepiratebay.org", "1337x.to", "yts.mx", "rarbg.to", "rutracker.org"
    ],
    "adult_content": [
        "pornhub.com", "xvideos.com", "redtube.com", "xnxx.com", "youporn.com"
    ],
    "gambling": [
        "stake.com", "bet365.com", "roobet.com", "draftkings.com", "bovada.lv"
    ],
    "music_podcasts": [
        "spotify.com", "soundcloud.com", "music.apple.com", "podcasts.apple.com", 
        "deezer.com", "tidal.com", "music.amazon.com"
    ]
}

def _base(domain):
    return domain.strip().lower().removeprefix("www.")

def _is_excepted(domain: str, exceptions: set[str]) -> bool:
    """Optimized exception check using set lookup and subdomain splitting."""
    if not domain or not exceptions: return False
    b = _base(domain)
    if b in exceptions: return True
    parts = b.split('.')
    for i in range(len(parts) - 1):
        if ".".join(parts[i:]) in exceptions:
            return True
    return False

@dataclasses.dataclass
class BlockingContext:
    """Structured container for computed blocking targets."""
    manual_domains: Set[str]
    filter_keywords: Set[str]
    normalized_filter_domains: Set[str]
    cloud_allowlist: Set[str]
    cloud_path_keywords: List[str]
    filter_exceptions: Set[str]
    app_exceptions: Set[str]
    path_exceptions: Set[str]
    adblock_enabled: bool
    processes: Set[str]
    files: Set[str]
    folders: Set[str]
    history: Set[str]

def _compute_targets(config: Dict[str, Any], clm: Any, cfg_path: str) -> BlockingContext:
    cfg_dir = os.path.dirname(cfg_path)
    # Extract and sanitize date_context from clm parameter if passed as datetime by test suites
    date_context = None
    if isinstance(clm, datetime):
        date_context = clm

    tier1: List[str] = []
    tier2: List[str] = []
    all_apps: Set[str] = set()
    all_files: Set[str] = set()
    all_folders: Set[str] = set()
    settings = config.get("settings", {})
    cloud_enabled = settings.get("cloud_allowlist_enabled", True)
    cloud_list = set(settings.get("cloud_allowlist", [])) if cloud_enabled else set()
    cloud_kws = [k.lower() for k in settings.get("cloud_path_keywords", [])] if cloud_enabled else []
    
    filter_exceptions: Set[str] = set()
    all_app_exceptions: Set[str] = set()
    all_path_exceptions: Set[str] = set()

    def is_cloud_allowed(val: str) -> bool:
        if not val or not cloud_enabled: return False
        v_low = val.lower()
        
        # 1. Exact or Wildcard Match (using DomainMatcher which handles *.domain.com and glob-style)
        if _pattern_matches(cloud_list, v_low):
            return True
            
        # 2. Path Keyword Matching (e.g., "appdata\roaming")
        # For paths, we also check if any allowed keyword is a parent directory
        for kw in cloud_kws:
            if kw in v_low:
                return True
        
        # 3. Robust App/File Matching: If a base filename is in cloud_list, allow it
        basename = os.path.basename(val).lower()
        if basename in {p.lower() for p in cloud_list}:
            return True
            
        # 4. System Safety Exclusions: Hardcoded bypass for critical processes
        if basename in SYSTEM_SAFETY_EXCLUSIONS:
            return True

        return False

    for _, gdata in config.get("groups", {}).items():
        if not gdata.get("enabled", True): continue
        active = is_active(gdata, date_context=date_context)
        ad = gdata.get("adblocker", {})
        ad_on = ad.get("enabled", False)
        ad_persist = ad.get("persist_all_day", False)
        
        if ad_on and ad_persist:
            ad_active = True
        else:
            ad_active = ad_on and active

        if active or ad_active:
            for e in gdata.get("exceptions", []) + ad.get("exceptions", []):
                e_str = str(e).strip().lower()
                if not e_str: continue
                if e_str.startswith("app:"):
                    all_app_exceptions.add(e_str[4:])
                elif e_str.startswith("path:"):
                    all_path_exceptions.add(e_str[5:])
                else:
                    filter_exceptions.add(_base(e_str))

        if active:
            for w in gdata.get("websites", []):
                if not is_cloud_allowed(w):
                    tier1.append(w)
            
            for a in gdata.get("apps", []):
                a_clean = a.strip()
                if a_clean and not is_cloud_allowed(a_clean):
                    all_apps.add(a_clean)
                    
            for f in gdata.get("files", []):
                if not f.strip(): continue
                p = f if os.path.isabs(f) else os.path.join(cfg_dir, f)
                p_norm = os.path.normpath(p)
                if not is_cloud_allowed(p_norm):
                    all_files.add(p_norm)
                    
            for f in gdata.get("folders", []):
                if not f.strip(): continue
                p = f if os.path.isabs(f) else os.path.join(cfg_dir, f)
                p_norm = os.path.normpath(p)
                if not is_cloud_allowed(p_norm):
                    all_folders.add(p_norm)

        if ad_active:
            for k in ["ads_trackers", "malware_annoyances", "social_media", "entertainment", "shopping", "gaming", "ai_tech", "piracy_illegal", "adult_content", "gambling", "music_podcasts"]:
                if ad.get(k): 
                    for domain in ADBLOCK_LISTS.get(k, []):
                        if not is_cloud_allowed(domain):
                            tier2.append(domain)

    # Compute normalized domains for fallback redundancy
    norm_domains = set()
    for _, gdata in config.get("groups", {}).items():
        if not gdata.get("enabled", True): continue
        ad = gdata.get("adblocker", {})
        ad_on = ad.get("enabled", False)
        if not ad_on: continue
        
        active = is_active(gdata, date_context=date_context)
        ad_persist = ad.get("persist_all_day", False)
        
        if ad_on and ad_persist:
            ad_active = True
        else:
            ad_active = ad_on and active
            
        if not ad_active: continue
        
        for k, domains in NORMALIZED_FILTER_MAP.items():
            if ad.get(k):
                norm_domains.update(domains)

    # Filter exceptions out of content filter redundancy domains (Exceptions > Content Filter)
    norm_domains = {d for d in norm_domains if not _is_excepted(d, filter_exceptions)}

    return BlockingContext(
        manual_domains=set(tier1),
        filter_keywords=set(tier2),
        normalized_filter_domains=norm_domains,
        cloud_allowlist=cloud_list,
        cloud_path_keywords=cloud_kws,
        filter_exceptions=filter_exceptions,
        app_exceptions=all_app_exceptions,
        path_exceptions=all_path_exceptions,
        adblock_enabled=any(g.get("adblocker", {}).get("enabled") for g in config.get("groups", {}).values()),
        processes=all_apps,
        files=all_files,
        folders=all_folders,
        history=_get_history()
    )

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

def _pattern_matches(patterns: Set[str], domain: str) -> bool:
    try:
        from blockers.dns_server import DomainMatcher
        return DomainMatcher(patterns).matches(domain)
    except Exception:
        domain = _base(str(domain))
        return domain in {_base(str(p)) for p in patterns if str(p).strip()}

def _resolve_hosts_fallback_domains(
    manual_domains: Set[str],
    normalized_filter_domains: Set[str],
    cloud_allowlist: Set[str],
    want_custom: Set[str] = None,
) -> Set[str]:
    """ONLY returns manual_domains, critical normalized redundancy set, and custom domains."""
    resolved: Set[str] = set()

    for domain in manual_domains:
        if not _pattern_matches(cloud_allowlist, domain):
            resolved.add(domain)

    for domain in normalized_filter_domains:
        if not _pattern_matches(cloud_allowlist, domain):
            resolved.add(domain)

    if want_custom:
        for domain in want_custom:
            if not _pattern_matches(cloud_allowlist, domain):
                resolved.add(domain)

    return resolved

def _get_history():
    h = set()
    legacy_path = os.path.join(base_data, "recovery.json")
    history_path = os.path.join(base_data, "recovery_history.json")
    
    # 1. Load active history if exists
    if os.path.exists(history_path):
        try:
            with open(history_path, "r") as fobj:
                h.update(json.load(fobj))
        except: pass
        
    # 2. Check and migrate legacy recovery.json
    if os.path.exists(legacy_path):
        try:
            legacy_set = set()
            with open(legacy_path, "r") as fobj:
                legacy_set.update(json.load(fobj))
            
            if legacy_set:
                h.update(legacy_set)
                import tempfile
                fd, tmp_path = tempfile.mkstemp(dir=base_data, prefix="recovery_tmp_", suffix=".json")
                with os.fdopen(fd, "w") as f:
                    json.dump(list(h), f)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, history_path)
            
            # Delete legacy file permanently to prevent zombie locks reloading
            os.remove(legacy_path)
            logger.info("Successfully migrated legacy recovery.json and deleted it from disk.")
        except Exception as e:
            logger.error(f"Failed to migrate legacy recovery.json: {e}")
            
    return h

def _save_history(new_paths):
    """Accumulates paths into history instead of overwriting.
    Ensures that metadata for locked files is never lost until successfully unlocked.
    """
    try:
        existing = _get_history()
        updated = existing.union(set(new_paths))
        
        # Write to a temporary file first
        import tempfile
        fd, tmp_path = tempfile.mkstemp(dir=base_data, prefix="recovery_tmp_", suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(list(updated), f)
            f.flush()
            os.fsync(f.fileno()) # Guarantee it is written to disk
            
        # Atomic replacement (safe from mid-write crashes)
        os.replace(tmp_path, RECOVERY_FILE)
    except Exception as e:
        logger.error(f"Failed to save history: {e}")

def _on_acl_operation_complete(path, locked, success):
    """Callback from ProcessMonitor when an ACL operation finishes.
    If an unlock was successful, we can finally remove it from the persistent history.
    """
    if not success:
        return
        
    if not locked: # This was an UNLOCK operation
        try:
            history = _get_history()
            path_norm = os.path.normpath(path)
            # Find and remove (case-insensitive on Windows)
            to_remove = None
            for p in history:
                if os.path.normpath(p).lower() == path_norm.lower():
                    to_remove = p
                    break
            
            if to_remove:
                history.remove(to_remove)
                import tempfile
                fd, tmp_path = tempfile.mkstemp(dir=base_data, prefix="recovery_tmp_", suffix=".json")
                with os.fdopen(fd, "w") as f:
                    json.dump(list(history), f)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, RECOVERY_FILE)
                logger.info(f"Verified Uplift: Removed {path} from recovery history.")
        except Exception as e:
            logger.error(f"Failed to update history after unlock: {e}")

def _boot_sweep_task(initial_targets: set[str], pm_instance, pm_lock):
    """Reconciles historical locks against current config on startup.
    Ensures that orphans from previous versions are unlocked.
    """
    lock_history = _get_history()
    if not lock_history: return
    
    logger.info(f"Failsafe Boot Sweep: Re-verifying {len(lock_history)} locks...")
    # Normalize initial targets for consistent comparison (case-insensitive on Windows)
    norm_targets = {os.path.normcase(os.path.normpath(p)) for p in initial_targets}
    
    to_lock = []
    to_unlock = []
    
    for path in lock_history:
        p = os.path.normpath(path)
        lookup_p = os.path.normcase(p)
        if lookup_p in norm_targets:
            if os.path.exists(p):
                to_lock.append(p)
        else:
            to_unlock.append(p)
            
    with pm_lock:
        # Process unlocks first (Batched)
        if to_unlock:
            logger.info(f"Failsafe: Unlocking {len(to_unlock)} orphaned targets...")
            if hasattr(pm_instance, 'batch_unlock'):
                pm_instance.batch_unlock(to_unlock)
            else:
                for p in to_unlock:
                    pm_instance.synchronize_lock(p, False)
            
        # Re-verify existing locks (Batch)
        if to_lock:
            logger.info(f"Failsafe: Re-verifying {len(to_lock)} active locks.")
            files = [p for p in to_lock if os.path.isfile(p)]
            folders = [p for p in to_lock if os.path.isdir(p)]
            if files: pm_instance.set_blocked_files(list(set(pm_instance.blocked_file_paths).union(set(files))))
            if folders: pm_instance.set_blocked_folders(list(set(pm_instance.blocked_folder_roots).union(set(folders))))

    logger.info("Boot Sweep complete.")

def is_admin():
    if os.name == "nt":
        from core.win32_utils import is_admin as win_is_admin
        return win_is_admin()
    return os.geteuid() == 0

def kill_other_instances():
    me = os.getpid()
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if p.info['pid'] == me: continue
            if p.info['name'] == "SPB_Daemon.exe" or ("python" in p.info['name'].lower() and "daemon.py" in " ".join(p.info['cmdline'] or [])):
                p.kill()
        except: pass

class ConfigManager:
    """Handles configuration loading, debouncing, and target computation."""
    def __init__(self, cfg_path: str):
        self.cfg_path = cfg_path
        self.cache: Dict[str, Any] = load_config(cfg_path)
        self.last_hash = self._get_config_hash()

    def _get_config_hash(self) -> str:
        import hashlib
        try:
            if os.path.exists(self.cfg_path):
                with open(self.cfg_path, 'rb') as f:
                    return hashlib.sha256(f.read()).hexdigest()
        except: pass
        return ""

    def check_for_updates(self) -> bool:
        """Returns True if the config has changed and stabilized."""
        curr_hash = self._get_config_hash()
        if not curr_hash:
            return False
        if self.last_hash != curr_hash:
            self.last_hash = curr_hash
            try:
                self.cache = load_config(self.cfg_path)
                return True
            except Exception:
                logger.error("Failed to load config.json", exc_info=True)
        return False

    def compute_context(self) -> BlockingContext:
        return _compute_targets(self.cache, clm, self.cfg_path)

class SubsystemOrchestrator:
    """Manages low-level protection subsystems (DNS, ProcessMonitor)."""
    def __init__(self):
        self.pm = ProcessMonitor() if ProcessMonitor else None
        self.pm_lock = threading.RLock()
        self.dns_server = None
        self.using_dns_proxy = False
        self._dns_healthy_flag = True
        self._dns_check_lock = threading.Lock()
        self._dns_check_in_progress = False
    
    def _dns_redirect_healthy(self) -> bool:
        """Return True when adapter DNS is still bound to localhost for proxy mode."""
        try:
            return handler.dns_points_to_local()
        except Exception as e:
            logger.debug(f"DNS redirect health check failed: {e}")
            return False

    def _check_dns_recovery(self, manual_domains, filter_keywords, normalized_filter_domains, cloud_allowlist, filter_exceptions):
        """Asynchronous recovery check for Port 53."""
        if self.using_dns_proxy:
            return

        # Preemptive check: do not recover DNS Proxy if there is a running conflicting service
        conflict = detect_conflicting_services()
        if conflict:
            logger.debug(f"DNS Proxy Recovery bypassed: Conflicting service '{conflict}' is running.")
            return

        # Simple non-destructive bind check
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.bind(('0.0.0.0', 53))
            
            logger.info("DNS Proxy Recovery: Port 53 is now available. Restarting DNS Subsystem...")
            # Re-initialize DNS Server
            self.sync_dns(manual_domains, filter_keywords, cloud_allowlist, filter_exceptions, False, normalized_filter_domains=normalized_filter_domains)
            if self.using_dns_proxy:
                logger.info("DNS Proxy Recovery SUCCESS: Subsystem active and hosts bloat cleared.")
                self._dns_healthy_flag = True
                self._update_health_signal("Active")
        except socket.error:
            # Port still occupied
            pass
        except Exception as e:
            logger.debug(f"Recovery check error: {e}")

    def sync_dns(self, manual_domains, filter_keywords, cloud_allowlist, filter_exceptions, first_run, normalized_filter_domains=None):
        want_domains = manual_domains.union(filter_keywords)
        if not want_domains:
            if self.dns_server:
                self.dns_server.stop()
                self.dns_server = None
            sync_website_protection([], active=False)
            self._update_health_signal("None")
            return False

        # Preemptive check: check for conflicting services
        conflict = detect_conflicting_services()
        if conflict:
            logger.info(f"Conflict detected with superior network/DNS service '{conflict}'. Falling back to hosts-file blocking.")
            if self.dns_server:
                self.dns_server.stop()
                self.dns_server = None
            self.using_dns_proxy = False
        
        elif not self.dns_server:
            self.dns_server = DNSProxyServer(
                list(manual_domains),
                list(filter_keywords),
                cloud_list=list(cloud_allowlist),
                filter_exceptions=list(filter_exceptions),
                upstream_dns=detect_system_dns()
            )
            if self.dns_server.start():
                self.using_dns_proxy = True
                remove_blocks(keep_policies=True)
            else:
                logger.error("DNS Proxy failed. Fallback to hosts-file.")
                self.dns_server = None
                self.using_dns_proxy = False
        else:
            # Only update rules if server already existed (re-creation does it in __init__)
            if self.using_dns_proxy:
                self.dns_server.update_rules(list(manual_domains), list(filter_keywords), list(cloud_allowlist), list(filter_exceptions))

        if self.using_dns_proxy and self.dns_server and (not self.dns_server.is_healthy() or not self._dns_redirect_healthy()):
            logger.error("DNS Proxy health check failed or adapter DNS drift detected. Restoring adapter DNS and falling back to hosts-file protection.")
            self.dns_server.stop()
            self.dns_server = None
            self.using_dns_proxy = False
        else:
            if self.using_dns_proxy:
                self._dns_healthy_flag = True
        
        # Determine Redundancy Set (Critical domains kept in hosts even with proxy active)
        # We only keep the global manual blocks as redundancy in the hosts file during proxy mode.
        # This keeps the hosts file clean of all other categories while proxy is healthy.
        # Both redundancy_set and active_domains are cloud-filtered to ensure policy consistency.
        redundancy_set = set()
        for domain in manual_domains:
            if not _pattern_matches(cloud_allowlist, domain):
                redundancy_set.add(domain)

        active_domains = _resolve_hosts_fallback_domains(
            manual_domains,
            normalized_filter_domains if normalized_filter_domains is not None else set(),
            cloud_allowlist,
            want_custom=filter_keywords
        )
        
        # Consistently check and enforce max_domains_cap limit for health/logging
        try:
            config = load_config()
            max_lines = config.get("settings", {}).get("max_domains_cap", 1000)
        except Exception:
            max_lines = 1000
        max_domains = max(0, (max_lines - 2) // 2)

        is_degraded = False
        if not self.using_dns_proxy:
            if len(active_domains) > max_domains:
                dropped = len(active_domains) - max_domains
                logger.critical(f"CRITICAL WARNING: Fallback hosts protection truncated. {dropped} domains dropped to fit max_domains_cap ({max_domains}).")
                is_degraded = True
        else:
            if len(redundancy_set) > max_domains:
                dropped = len(redundancy_set) - max_domains
                logger.critical(f"CRITICAL WARNING: Hosts redundancy protection truncated. {dropped} domains dropped to fit max_domains_cap ({max_domains}).")
                is_degraded = True

        # Pass redundancy_set to ensure core distractions are in hosts file
        sync_website_protection(
            list(active_domains), 
            active=True, 
            using_dns_proxy=self.using_dns_proxy,
            redundancy_list=list(redundancy_set)
        )
        
        health_state = "Degraded" if is_degraded else ("Active" if self.using_dns_proxy else "Fallback")
        self._update_health_signal(health_state)
        return True

    def _update_health_signal(self, status: str):
        """Writes a signal file for the UI to display engine health."""
        try:
            health_file = os.path.join(base_data, "dns_health.signal")
            with open(health_file, "w") as f:
                f.write(status)
        except: pass

    def _run_dns_health_check_async(self):
        with self._dns_check_lock:
            if self._dns_check_in_progress:
                return
            self._dns_check_in_progress = True

        def worker():
            try:
                server = self.dns_server
                if not server:
                    self._dns_healthy_flag = False
                    return

                conflict = detect_conflicting_services()
                if conflict:
                    self._dns_healthy_flag = False
                    return

                if not server.is_healthy():
                    self._dns_healthy_flag = False
                    return

                if not self._dns_redirect_healthy():
                    self._dns_healthy_flag = False
                    return

                self._dns_healthy_flag = True
            except Exception as e:
                logger.debug(f"Async DNS health check error: {e}")
                self._dns_healthy_flag = False
            finally:
                with self._dns_check_lock:
                    self._dns_check_in_progress = False

        threading.Thread(target=worker, daemon=True).start()

    def watchdog_dns(self, manual_domains, filter_keywords, normalized_filter_domains, cloud_allowlist, filter_exceptions):
        if not self.using_dns_proxy or not self.dns_server:
            # Task 4: Attempt recovery if in fallback mode
            self._check_dns_recovery(manual_domains, filter_keywords, normalized_filter_domains, cloud_allowlist, filter_exceptions)
            return

        # Trigger the next async check cycle
        self._run_dns_health_check_async()

        # Evaluate the result from the last cycle
        if not self._dns_healthy_flag:
            conflict = detect_conflicting_services()
            if conflict:
                logger.warning(f"DNS watchdog detected conflict with '{conflict}'. Switch to hosts fallback.")
            else:
                logger.error("DNS watchdog detected an unhealthy proxy or adapter DNS drift. Restoring DNS and switching to hosts fallback.")
            
            # Reset flag immediately to avoid multiple triggering
            self._dns_healthy_flag = True
            
            self.dns_server.stop()
            self.dns_server = None
            self.using_dns_proxy = False
            
            # Call sync_dns directly to consistently trigger fallback state, caps, and health signal updates
            self.sync_dns(manual_domains, filter_keywords, cloud_allowlist, filter_exceptions, False, normalized_filter_domains=normalized_filter_domains)

    def sync_processes(self, processes, files, folders, first_run):
        if self.pm:
            app_paths = {a for a in processes if os.path.sep in a or (os.name == 'nt' and '/' in a)}
            _save_history(files.union(folders).union(app_paths))
            with self.pm_lock:
                self.pm.synchronize_all(list(processes), list(files), list(folders))

class DaemonOrchestrator:
    def __init__(self, cfg_path: str):
        self.cfg = ConfigManager(cfg_path)
        self.subsystems = SubsystemOrchestrator()
        
        self.cur_apps, self.cur_files, self.cur_folders = set(), set(), set()
        self.cur_domains, self.cur_manual_domains, self.cur_exceptions, self.cur_cloud = set(), set(), set(), set()
        self.want_custom = set()
        self._last_custom_urls = set()
        self._is_fetching = False
        self.last_minute = -1
        self.first_run = True
        self.last_heartbeat = 0.0

    def _handle_custom_lists(self):
        custom_lists = []
        for g in self.cfg.cache.get("groups", {}).values():
            if g.get("enabled") and is_active(g):
                custom_lists.extend(g.get("adblocker", {}).get("custom_lists", []))
        
        urls = {u.strip() for u in custom_lists if u.strip()}
        if urls and urls != self._last_custom_urls and not self._is_fetching:
            self._is_fetching = True
            self._last_custom_urls = urls
            def _callback(res):
                self.want_custom = res
                self._is_fetching = False
            
            logger.info(f"Updating {len(urls)} custom lists...")
            threading.Thread(target=_async_fetch_lists, args=(clm, list(urls), _callback, self.cfg.cfg_path), daemon=True).start()

    def sync(self) -> None:
        config_changed = self.cfg.check_for_updates()
        now_dt = datetime.now()
        
        # Periodic trigger for schedule updates
        time_triggered = False
        if now_dt.minute != self.last_minute:
            self.last_minute = now_dt.minute
            time_triggered = True

        if not config_changed and not time_triggered and not self.first_run:
            return

        self._handle_custom_lists()
        ctx = self.cfg.compute_context()
        
        if self.first_run:
            app_paths = {os.path.normpath(a) for a in ctx.processes if os.path.sep in a or (os.name == 'nt' and '/' in a)}
            initial_targets = ctx.files.union(ctx.folders).union(app_paths)
            if self.subsystems.pm:
                threading.Thread(target=_boot_sweep_task, args=(initial_targets, self.subsystems.pm, self.subsystems.pm_lock), daemon=True).start()

        # Update PM Settings
        settings = self.cfg.cache.get("settings", {})
        if self.subsystems.pm:
            global_allow = set(settings.get("cloud_allowlist", [])) if settings.get("cloud_allowlist_enabled", True) else set()
            global_kws = settings.get("cloud_path_keywords", []) if settings.get("cloud_allowlist_enabled", True) else []
            self.subsystems.pm.set_global_allowlist(list(global_allow), global_kws)
            self.subsystems.pm.set_allowlisted_processes(list(ctx.app_exceptions), enabled=bool(ctx.app_exceptions))
            self.subsystems.pm.set_allowlisted_keywords(list(ctx.path_exceptions))
            self.subsystems.pm.configure_performance(settings.get("performance_mode", "Balanced"))
            # Register the history callback
            self.subsystems.pm._acl_callback = _on_acl_operation_complete

        # Update Subsystems
        total_filter = ctx.filter_keywords.union(self.want_custom)
        
        if total_filter.union(ctx.manual_domains) != self.cur_domains or \
           ctx.filter_exceptions != self.cur_exceptions or \
           ctx.cloud_allowlist != self.cur_cloud or self.first_run:
            self.subsystems.sync_dns(ctx.manual_domains, total_filter, ctx.cloud_allowlist, ctx.filter_exceptions, self.first_run, normalized_filter_domains=ctx.normalized_filter_domains)
            logger.info(f"DNS Subsystem Sync: {len(ctx.manual_domains)} manual, {len(total_filter)} filter domains. (DNS Proxy={self.subsystems.using_dns_proxy})")

        if ctx.processes != self.cur_apps or ctx.files != self.cur_files or ctx.folders != self.cur_folders or self.first_run:
            self.subsystems.sync_processes(ctx.processes, ctx.files, ctx.folders, self.first_run)
            logger.info(f"PM Subsystem Sync: {len(ctx.processes)} apps, {len(ctx.files)} files, {len(ctx.folders)} folders.")

        # Log active groups for user transparency
        active_groups = [gname for gname, g in self.cfg.cache.get("groups", {}).items() if g.get("enabled", True) and is_active(g)]
        logger.info(f"Active Groups: {', '.join(active_groups) if active_groups else 'None'}")

        self.cur_apps, self.cur_files, self.cur_folders = ctx.processes, ctx.files, ctx.folders
        self.cur_domains, self.cur_exceptions, self.cur_cloud = total_filter.union(ctx.manual_domains), ctx.filter_exceptions, ctx.cloud_allowlist
        self.cur_manual_domains = ctx.manual_domains
        self.cur_filter_keywords = total_filter
        self.cur_normalized_filter_domains = ctx.normalized_filter_domains
        self.first_run = False

    def run(self):
        while True:
            try:
                self.sync()
                now = time.time()
                if now - self.last_heartbeat >= 60.0:
                    self.subsystems.watchdog_dns(self.cur_manual_domains, getattr(self, 'cur_filter_keywords', set()), getattr(self, 'cur_normalized_filter_domains', set()), self.cur_cloud, self.cur_exceptions)
                    dns_status = "Active" if self.subsystems.using_dns_proxy else ("Fallback" if self.cur_domains else "None")
                    logger.info(f"Heartbeat: [Admin={is_admin()}] [Protection={'Active' if self.subsystems.pm and self.subsystems.pm.is_active else 'Off'}] [DNS={dns_status}]")
                    self.last_heartbeat = now
                
                poll_sleep = {"Passive": 5, "Balanced": 2, "Strict": 0.5}.get(self.cfg.cache.get("settings", {}).get("performance_mode", "Balanced"), 2)
                time.sleep(poll_sleep)
            except Exception as e:
                logger.error(f"Orchestrator error: {e}", exc_info=True)
                time.sleep(5)

VERSION = "1.4.8"

def main():
    from core.win32_utils import is_safe_mode
    if is_safe_mode():
        logger.warning("Windows Safe Mode detected! Automatically lifting all SPB blocks.")
        try:
            from recovery_uplift import run_auto_recovery
            run_auto_recovery()
        except Exception as e:
            logger.error(f"Safe Mode automated recovery failed: {e}")
        sys.exit(0)

    logger.info(f"Productivity Daemon v{VERSION} started.")
    cfg_path = os.path.join(base_data, "config.json")
    try:
        from core.persistence import harden_config_dir
        harden_config_dir(base_data)
    except Exception:
        logger.debug("Config ACL hardening skipped.")
    orchestrator = DaemonOrchestrator(cfg_path)
    orchestrator.run()

if __name__ == "__main__":
    if os.name == "nt" and not is_admin() and "SPB_DATA_DIR" not in os.environ:
        # Check if Ghost Mode is explicitly requested (skips UAC prompt)
        if os.environ.get("SPB_GHOST_MODE") == "1":
            logger.info("Ghost Mode: Running without administrative elevation.")
        else:
            # Re-launch with admin rights using safe quoting
            import subprocess
            params = subprocess.list2cmdline(sys.argv[1:])
            try:
                # ShellExecuteW returns > 32 on success
                res = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
                if res > 32:
                    sys.exit(0)
                else:
                    logger.warning(f"Elevation rejected (Code: {res}). Attempting to run in User Mode.")
            except Exception as e:
                logger.warning(f"Elevation failed: {e}. Attempting to run in User Mode.")
    
    main()
