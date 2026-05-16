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
_INTERNAL_HOSTS_FILE = r"C:\Windows\System32\drivers\etc\hosts" if os.name == 'nt' else "/etc/hosts"

# Placeholder functions that will be replaced by actual implementations if imports succeed
def flush_dns(): pass
def apply_blocks(*a, **k): pass
def remove_blocks(*a, **k): pass
def apply_browser_policies(*a, **k): pass
def sync_website_protection(*a, **k): pass
def detect_system_dns(): return []
ProcessMonitor = None
DNSProxyServer = None
HOSTS_FILE = _INTERNAL_HOSTS_FILE # Default global

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
    from blockers.dns_server import DNSProxyServer, detect_system_dns as _detect_dns
    
    # Successfully imported - bind to the global names used in the orchestrator
    apply_blocks = _apply_blocks
    remove_blocks = _remove_blocks
    apply_browser_policies = _apply_policies
    sync_website_protection = _sync_protect
    HOSTS_FILE = _REAL_HOSTS_FILE
    flush_dns = _flush_dns
    detect_system_dns = _detect_dns
except ImportError as e:
    logger = logging.getLogger("SPB_Daemon")
    logger.error(f"CRITICAL: Background modules failed to load. Basic protection is inactive: {e}")
    # orchestrator will use the no-op fallbacks defined above

# Constants
if "SPB_DATA_DIR" in os.environ:
    base_data = os.environ["SPB_DATA_DIR"]
elif os.name == "nt":
    base_data = os.path.join(os.getenv("PROGRAMDATA", r"C:\ProgramData"), "SimpleProductivityBlocker")
else:
    base_data = os.path.expanduser("~/.config/SimpleProductivityBlocker")
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

        return False

    for _, gdata in config.get("groups", {}).items():
        if not gdata.get("enabled", True): continue
        active = is_active(gdata)
        ad = gdata.get("adblocker", {})
        ad_on = ad.get("enabled", False)
        ad_persist = ad.get("persist_all_day", False)
        day_on = is_day_active(gdata.get("schedule", {}))
        
        ad_active = ad_on and day_on and (ad_persist or active)

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
            for k in ["ads_trackers", "malware_annoyances", "social_media", "entertainment", "shopping", "gaming", "ai_tech", "piracy_illegal", "adult_content", "gambling"]:
                if ad.get(k): 
                    for domain in ADBLOCK_LISTS.get(k, []):
                        if not is_cloud_allowed(domain):
                            tier2.append(domain)

    return BlockingContext(
        manual_domains=set(tier1),
        filter_keywords=set(tier2),
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
    filter_keywords: Set[str],
    cloud_allowlist: Set[str],
    filter_exceptions: Set[str],
) -> Set[str]:
    """Approximate DNS proxy priority when falling back to static hosts entries."""
    resolved: Set[str] = set()

    for domain in manual_domains:
        if not _pattern_matches(cloud_allowlist, domain):
            resolved.add(domain)

    for domain in filter_keywords:
        if _pattern_matches(cloud_allowlist, domain):
            continue
        if _pattern_matches(filter_exceptions, domain):
            continue
        resolved.add(domain)

    return resolved

def _get_history():
    h = set()
    for f in ["recovery.json", "recovery_history.json"]:
        p = os.path.join(base_data, f)
        if os.path.exists(p):
            try:
                with open(p, "r") as fobj: h.update(json.load(fobj))
            except: pass
    return h

def _save_history(new_paths):
    """Accumulates paths into history instead of overwriting.
    Ensures that metadata for locked files is never lost until successfully unlocked.
    """
    try:
        existing = _get_history()
        # Only add to history, never remove here (Removal happens in _on_acl_operation_complete)
        updated = existing.union(set(new_paths))
        with open(RECOVERY_FILE, "w") as f:
            json.dump(list(updated), f)
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
                with open(RECOVERY_FILE, "w") as f:
                    json.dump(list(history), f)
                logger.info(f"Verified Uplift: Removed {path} from recovery history.")
        except Exception as e:
            logger.error(f"Failed to update history after unlock: {e}")

def _boot_sweep_task(initial_targets: set[str], pm_instance):
    """Reconciles historical locks against current config on startup.
    Ensures that orphans from previous versions are unlocked.
    """
    lock_history = _get_history()
    if not lock_history: return
    
    logger.info(f"Failsafe Boot Sweep: Re-verifying {len(lock_history)} locks...")
    # Normalize initial targets for consistent comparison (case-insensitive on Windows)
    norm_targets = {os.path.normcase(os.path.normpath(p)) for p in initial_targets}
    
    for path in lock_history:
        p = os.path.normpath(path)
        lookup_p = os.path.normcase(p)
        if lookup_p in norm_targets:
            if os.path.exists(p):
                pm_instance.synchronize_lock(p, True)
        else:
            # Reconcile: If it's in history but not in current targets, unlock it
            logger.info(f"Failsafe: Unlocking orphaned target: {p}")
            pm_instance.synchronize_lock(p, False)
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

class ConfigManager:
    """Handles configuration loading, debouncing, and target computation."""
    def __init__(self, cfg_path: str):
        self.cfg_path = cfg_path
        self.cache: Dict[str, Any] = load_config(cfg_path)
        self.stable_mtime = 0.0
        self.pending_mtime = 0.0
        self.debounce_counter = 0

    def check_for_updates(self) -> bool:
        """Returns True if the config has changed and stabilized."""
        try:
            mtime = os.path.getmtime(self.cfg_path) if os.path.exists(self.cfg_path) else 0.0
        except:
            mtime = 0.0

        if mtime != self.pending_mtime:
            self.pending_mtime = mtime
            self.debounce_counter = 0
            return False
        
        if self.debounce_counter < 2:
            self.debounce_counter += 1
            return False
        
        if self.stable_mtime != mtime:
            self.stable_mtime = mtime
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
        self.dns_server = None
        self.using_dns_proxy = False

    def sync_dns(self, manual_domains, filter_keywords, cloud_allowlist, filter_exceptions, first_run):
        want_domains = manual_domains.union(filter_keywords)
        if not want_domains:
            if self.dns_server:
                self.dns_server.stop()
                self.dns_server = None
            sync_website_protection([], active=False)
            self._update_health_signal("None")
            return False

        if not self.dns_server:
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

        if self.using_dns_proxy and self.dns_server and not self.dns_server.is_healthy():
            logger.error("DNS Proxy health check failed. Restoring adapter DNS and falling back to hosts-file protection.")
            self.dns_server.stop()
            self.dns_server = None
            self.using_dns_proxy = False
        
        # Determine Redundancy Set (Critical keywords that must be in hosts even with proxy)
        redundancy_set = set()
        critical_patterns = ["youtube", "discord", "googlevideo", "ytimg", "discord.gg"]
        
        for d in manual_domains:
            d_low = d.lower()
            if any(p in d_low for p in critical_patterns):
                redundancy_set.add(d)
        
        # Also include a subset of filter keywords for redundancy if they are high-priority
        # (limiting to prevent hosts file bloat)
        for d in filter_keywords:
            d_low = d.lower()
            # Only add specific high-impact filter domains to redundancy
            if "youtube" in d_low or "discord" in d_low:
                 redundancy_set.add(d)

        active_domains = _resolve_hosts_fallback_domains(
            manual_domains,
            filter_keywords,
            cloud_allowlist,
            filter_exceptions,
        )
        
        # Pass redundancy_set to ensure core distractions are in hosts file
        sync_website_protection(
            list(active_domains), 
            active=True, 
            using_dns_proxy=self.using_dns_proxy,
            redundancy_domains=list(redundancy_set) if redundancy_set else None
        )
        
        self._update_health_signal("Active" if self.using_dns_proxy else "Fallback")
        return True

    def _update_health_signal(self, status: str):
        """Writes a signal file for the UI to display engine health."""
        try:
            health_file = os.path.join(base_data, "dns_health.signal")
            with open(health_file, "w") as f:
                f.write(status)
        except: pass

    def watchdog_dns(self, active_domains):
        if not self.using_dns_proxy or not self.dns_server:
            return
        if self.dns_server.is_healthy():
            return
        logger.error("DNS watchdog detected an unhealthy proxy. Restoring DNS and switching to hosts fallback.")
        self.dns_server.stop()
        self.dns_server = None
        self.using_dns_proxy = False
        sync_website_protection(list(active_domains), active=True, using_dns_proxy=False)

    def sync_processes(self, processes, files, folders, first_run):
        if self.pm:
            app_paths = {a for a in processes if os.path.sep in a or (os.name == 'nt' and '/' in a)}
            _save_history(files.union(folders).union(app_paths).union({HOSTS_FILE}))
            self.pm.synchronize_all(list(processes), list(files), list(folders))

class DaemonOrchestrator:
    def __init__(self, cfg_path: str):
        self.cfg = ConfigManager(cfg_path)
        self.subsystems = SubsystemOrchestrator()
        
        self.cur_apps, self.cur_files, self.cur_folders = set(), set(), set()
        self.cur_domains, self.cur_exceptions, self.cur_cloud = set(), set(), set()
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
            initial_targets = ctx.files.union(ctx.folders).union(app_paths).union({HOSTS_FILE})
            if self.subsystems.pm:
                threading.Thread(target=_boot_sweep_task, args=(initial_targets, self.subsystems.pm), daemon=True).start()

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
            self.subsystems.sync_dns(ctx.manual_domains, total_filter, ctx.cloud_allowlist, ctx.filter_exceptions, self.first_run)
            logger.info(f"DNS Subsystem Sync: {len(ctx.manual_domains)} manual, {len(total_filter)} filter domains. (DNS Proxy={self.subsystems.using_dns_proxy})")

        if ctx.processes != self.cur_apps or ctx.files != self.cur_files or ctx.folders != self.cur_folders or self.first_run:
            self.subsystems.sync_processes(ctx.processes, ctx.files, ctx.folders, self.first_run)
            logger.info(f"PM Subsystem Sync: {len(ctx.processes)} apps, {len(ctx.files)} files, {len(ctx.folders)} folders.")

        # Log active groups for user transparency
        active_groups = [g.get("name", "Unnamed") for g in self.cfg.cache.get("groups", {}).values() if g.get("enabled", True) and is_active(g)]
        logger.info(f"Active Groups: {', '.join(active_groups) if active_groups else 'None'}")

        self.cur_apps, self.cur_files, self.cur_folders = ctx.processes, ctx.files, ctx.folders
        self.cur_domains, self.cur_exceptions, self.cur_cloud = total_filter.union(ctx.manual_domains), ctx.filter_exceptions, ctx.cloud_allowlist
        self.first_run = False

    def run(self):
        while True:
            try:
                self.sync()
                now = time.time()
                if now - self.last_heartbeat >= 60.0:
                    self.subsystems.watchdog_dns(self.cur_domains)
                    dns_status = "Active" if self.subsystems.using_dns_proxy else ("Fallback" if self.cur_domains else "None")
                    logger.info(f"Heartbeat: [Admin={is_admin()}] [Protection={'Active' if self.subsystems.pm and self.subsystems.pm.is_active else 'Off'}] [DNS={dns_status}]")
                    if os.name == 'nt' and self.subsystems.pm and self.subsystems.pm.is_active:
                        self.subsystems.pm.synchronize_registry()
                    self.last_heartbeat = now
                
                poll_sleep = {"Passive": 5, "Balanced": 2, "Strict": 0.5}.get(self.cfg.cache.get("settings", {}).get("performance_mode", "Balanced"), 2)
                time.sleep(poll_sleep)
            except Exception as e:
                logger.error(f"Orchestrator error: {e}", exc_info=True)
                time.sleep(5)

VERSION = "1.4.4"

def main():
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
            params = subprocess.list2cmdline(sys.argv)
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
