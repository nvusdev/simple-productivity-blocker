import psutil
import logging
import threading
import time
import os
import queue
try:
    import pythoncom
    import win32com.client
except ImportError:
    pythoncom = None
    win32com = None
import urllib.parse
if os.name == 'nt':
    import subprocess
    import getpass
    import win32file
    import win32con

SYSTEM_SAFETY_EXCLUSIONS = {
    "explorer.exe", "taskmgr.exe", "services.exe", "lsass.exe", "csrss.exe",
    "wininit.exe", "winlogon.exe", "spoolsv.exe", "svchost.exe",
}

class ProcessMonitor:
    def __init__(self):
        self.blocked_app_names = set()
        self.blocked_app_paths = set()
        self.blocked_file_paths = set()
        self.blocked_file_names = set()
        self.blocked_folder_roots = []
        self.blocked_folder_prefixes = []
        self.is_active = False
        self._watcher_thread = None
        self._stop_event = threading.Event()
        self._last_shell_check = 0.0
        self._fast_until = 0.0
        self._fast_interval = 0.5
        self._base_interval = 1.0
        self._shell_interval = 2.0
        self._allowlisted_processes = set()
        self._allowlisted_keywords = set()
        self._global_allowlisted_processes = set()
        self._global_allowlisted_keywords = set()
        self._allowlist_enabled = True
        self._locked_files = []
        self._current_acl_paths = set()
        self._acl_sync_lock = threading.RLock()
        self._acl_queue = queue.Queue()
        self._username = getpass.getuser() if os.name == 'nt' else None
        self._path_cache = {}
        self.logger = logging.getLogger("SPB_AppBlocker")
        
        self._acl_worker = None
        self._acl_callback = None

    def configure_performance(self, mode: str):
        """Standardized performance profiles:
        Passive:  5.0s (Battery Saver)
        Balanced: 2.0s (Recommended)
        Strict:   0.5s (High Security)
        """
        mode = str(mode or "balanced").strip().lower()
        if mode == "passive":   self._base_interval = 5.0
        elif mode == "balanced": self._base_interval = 2.0
        elif mode == "strict":   self._base_interval = 0.5
        else:                   self._base_interval = 2.0
        self.logger.info(f"Performance profile set to: {mode.capitalize()} ({self._base_interval}s)")

    def set_allowlisted_processes(self, processes, enabled=True):
        self._allowlist_enabled = bool(enabled)
        self._allowlisted_processes = {
            str(p).strip().lower() for p in (processes or []) if str(p).strip()
        }

    def set_allowlisted_keywords(self, keywords):
        self._allowlisted_keywords = {
            str(k).strip().lower() for k in (keywords or []) if str(k).strip()
        }

    def set_global_allowlist(self, processes, keywords):
        self._global_allowlisted_processes = {
            str(p).strip().lower() for p in (processes or []) if str(p).strip()
        }
        self._global_allowlisted_keywords = {
            str(k).strip().lower() for k in (keywords or []) if str(k).strip()
        }

    def _normalize_path(self, path):
        if not path: return ""
        if path in self._path_cache:
            return self._path_cache[path]
        
        try:
            norm = os.path.normcase(os.path.abspath(path))
            self._path_cache[path] = norm
            if len(self._path_cache) > 2000:
                self._path_cache.clear()
            return norm
        except Exception:
            return path.lower()

    def _looks_like_path(self, value):
        if not value:
            return False
        if os.name == 'nt':
            if os.path.isabs(value): return True
            if value.startswith("\\\\"): return True
            if len(value) >= 3 and value[1] == ":" and value[2] in ("\\", "/"): return True
        else:
            if value.startswith("/"): return True
        if os.path.sep in value: return True
        if os.path.altsep and os.path.altsep in value: return True
        return False

    def _extract_path_candidates(self, arg):
        candidates = []
        if not arg:
            return candidates
        parts = arg.split("=") if "=" in arg else [arg]
        for part in parts:
            part = part.strip("\"'")
            if not part:
                continue
            if self._looks_like_path(part):
                candidates.append(part)
        return candidates

    def _is_in_blocked_folder(self, path_norm):
        for root, prefix in zip(self.blocked_folder_roots, self.blocked_folder_prefixes):
            if path_norm == root or path_norm.startswith(prefix):
                return True
        return False

    def set_blocked_apps(self, apps):
        old_paths = set(self.blocked_app_paths)
        self.blocked_app_names.clear()
        self.blocked_app_paths.clear()
        for app in (apps or []):
            if not app: continue
            base = os.path.basename(app)
            base_lower = base.lower() if base else ""
            if base_lower in SYSTEM_SAFETY_EXCLUSIONS:
                self.logger.warning(f"Safety exclusion: refusing to add blocked app target '{base_lower}'")
                continue
            if base:
                self.blocked_app_names.add(base.lower())
                stem = os.path.splitext(base)[0]
                if stem and stem != base:
                    self.blocked_app_names.add(stem)
            if self._looks_like_path(app):
                path_norm = self._normalize_path(app)
                self.blocked_app_paths.add(path_norm)
        
        if self.is_active:
            self._lock_files()   # Vector 1: Exclusive Handles
            
            # Vector 2: ACLs
            for path in old_paths - self.blocked_app_paths:
                self._set_acl_lock(path, False)
            for path in self.blocked_app_paths:
                self._set_acl_lock(path, True)

    def set_blocked_files(self, files):
        self._fast_until = time.time() + 10
        new_paths = {self._normalize_path(f) for f in (files or []) if f.strip()}
        removed = self.blocked_file_paths - new_paths
        self.blocked_file_paths = new_paths
        
        self.blocked_file_names.clear()
        for path in self.blocked_file_paths:
            base = os.path.basename(path)
            if base: self.blocked_file_names.add(base.lower())
            
        if self.is_active:
            self._lock_files()
            for path in removed: self._set_acl_lock(path, False)
            for path in self.blocked_file_paths: self._set_acl_lock(path, True) # Vector 3: ACLs

    def set_blocked_folders(self, folders):
        self._fast_until = time.time() + 10
        new_roots = {self._normalize_path(f) for f in (folders or []) if f.strip()}
        removed = set(self.blocked_folder_roots) - new_roots
        self.blocked_folder_roots = list(new_roots)
        self.blocked_folder_prefixes = [(r if r.endswith(os.path.sep) else r + os.path.sep) for r in self.blocked_folder_roots]
        
        if self.is_active:
            for path in removed: self._set_acl_lock(path, False)
            for root in self.blocked_folder_roots: self._set_acl_lock(root, True)

    def start(self):
        if self.is_active: return
        
        # Stop existing threads if they are still running
        if self._watcher_thread or self._acl_worker:
            self.stop()
            
        self.is_active = True
        self._stop_event.clear()
        
        self._lock_files()
        
        for path in self.blocked_app_paths:
            self._set_acl_lock(path, True)
        for path in self.blocked_file_paths:
            self._set_acl_lock(path, True)
        for path in self.blocked_folder_roots:
            self._set_acl_lock(path, True)

        # Restart background workers
        self._watcher_thread = threading.Thread(target=self._watch_processes, daemon=True)
        self._watcher_thread.start()
        
        self._acl_worker = threading.Thread(target=self._process_acl_queue, daemon=True)
        self._acl_worker.start()
        
        self.logger.info("ProcessMonitor started.")

    def stop(self):
        self.is_active = False
        self._stop_event.set()
        
        # Wait for threads to terminate
        if self._watcher_thread and self._watcher_thread.is_alive():
            self._watcher_thread.join(timeout=1.0)
        if self._acl_worker and self._acl_worker.is_alive():
            self._acl_worker.join(timeout=1.0)
            
        self._watcher_thread = None
        self._acl_worker = None
        self._unlock_files()
        self._clear_all_acls()
        self.logger.info("ProcessMonitor stopped.")

    def _process_acl_queue(self):
        while not self._stop_event.is_set():
            try:
                task = self._acl_queue.get(timeout=1)
                path, lock, callback = task
                success = self._apply_acl_internal(path, lock)
                if callback:
                    callback(path, lock, success)
                self._acl_queue.task_done()
            except queue.Empty: continue
            except Exception as e:
                self.logger.error(f"Background ACL worker error: {e}")
                time.sleep(1)

    def _is_critical_path(self, path):
        path = path.lower()
        if os.name == 'nt':
            system_root = os.environ.get("SystemRoot", "C:\\Windows").lower()
            program_data = os.environ.get("ProgramData", "C:\\ProgramData").lower()
            user_profile = os.environ.get("USERPROFILE", "").lower()
            critical_zones = [
                system_root, os.path.join(system_root, "system32"),
                program_data, os.path.join(user_profile, "appdata"),
                # SPB Self-Protection: prevent locking its own binaries or config
                os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Simple Productivity Blocker"),
                os.path.join(os.getenv("PROGRAMDATA", "C:\\ProgramData"), "SimpleProductivityBlocker")
            ]
        else:
            critical_zones = ["/etc", "/bin", "/sbin", "/usr/bin", "/usr/sbin", "/boot", "/dev"]
        
        for zone in critical_zones:
            if path == zone or path.startswith(zone + os.sep):
                return True
        return False

    def _apply_acl_internal(self, path, lock=True):
        if os.name != 'nt': return
        
        path = os.path.normpath(os.path.abspath(path))
        path_lower = path.lower()

        # 1. Global Allowlist Check
        is_global_exempt = False
        if os.path.basename(path_lower) in self._global_allowlisted_processes:
            is_global_exempt = True
        else:
            if self._global_allowlisted_keywords:
                import re
                for kw in self._global_allowlisted_keywords:
                    try:
                        if re.search(kw, path_lower, re.IGNORECASE):
                            is_global_exempt = True
                            break
                    except re.error:
                        if kw in path_lower:
                            is_global_exempt = True
                            break
                            
        if is_global_exempt:
            self.logger.info(f"Global Allowlist Override: Unlocking {path}")
            lock = False

        # 2. Group Exceptions Check: Allowlist overrides Folder Blocks, but NOT Explicit App/File Blocks
        elif lock and self._allowlist_enabled:
            # Check if it's an explicit block
            is_explicit_block = False
            if path_lower in self.blocked_app_paths or path_lower in self.blocked_file_paths:
                is_explicit_block = True
            elif os.path.basename(path_lower) in self.blocked_app_names or os.path.basename(path_lower) in self.blocked_file_names:
                is_explicit_block = True
                
            if not is_explicit_block:
                is_exempt = False
                # Check by filename
                if os.path.basename(path_lower) in self._allowlisted_processes:
                    is_exempt = True
                    reason = "Process Exempted"
                # Check by path keywords (with regex support)
                else:
                    import re
                    for kw in self._allowlisted_keywords:
                        try:
                            if re.search(kw, path_lower, re.IGNORECASE):
                                is_exempt = True
                                reason = "Path Keyword Exempted (Regex)"
                                break
                        except re.error:
                            if kw in path_lower:
                                is_exempt = True
                                reason = "Path Keyword Exempted"
                                break
                
                if is_exempt:
                    self.logger.info(f"Allowlist Override: Unlocking {path} ({reason})")
                    lock = False # Force unlock if allowlisted

        if lock and self._is_critical_path(path):
            self.logger.error(f"CRITICAL PATH VIOLATION: Refusing to lock system-critical path: {path}")
            return False
        target = "*S-1-1-0" # Everyone
        is_dir = os.path.isdir(path)
        try:
            if lock:
                perm_flags = "(OI)(CI)(F)" if is_dir else "(F)"
                args = [
                    "icacls", path, "/inheritance:r", 
                    "/grant:r", f"System:{perm_flags}", 
                    "/grant:r", f"Administrators:{perm_flags}",
                    "/deny", f"{target}:{perm_flags}", "/c", "/q"
                ]
            else:
                args = ["icacls", path, "/inheritance:e", "/remove:d", target, "/c", "/q"]
            
            res = subprocess.run(args, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.returncode != 0:
                self.logger.error(f"ACL Failure for {path}: {res.stderr.strip()}")
                return False
            else:
                self.logger.info(f"ACL {'Locked' if lock else 'Restored'} for {path}")
                with self._acl_sync_lock:
                    if lock: self._current_acl_paths.add(path)
                    elif path in self._current_acl_paths: self._current_acl_paths.remove(path)
                return True
        except Exception as e:
            self.logger.error(f"ACL Exception for {path}: {e}")
            return False

    def _set_acl_lock(self, path, should_lock, callback=None):
        """Asynchronous ACL locking via background queue."""
        if not path: return
        cb = callback or self._acl_callback
        self._acl_queue.put((path, should_lock, cb))

    def _clear_all_acls(self):
        with self._acl_sync_lock:
            paths = list(self._current_acl_paths)
        for path in paths:
            self._apply_acl_internal(path, False)
        self._current_acl_paths.clear()

    def _lock_files(self):
        """Standardized Windows exclusive handle locking."""
        if os.name != 'nt': return
        self._unlock_files()
        
        targets = set()
        targets.update(self.blocked_file_paths)
        targets.update(self.blocked_app_paths)
        
        for path in targets:
            if not os.path.exists(path) or os.path.isdir(path): continue
            if os.path.basename(path).lower() in SYSTEM_SAFETY_EXCLUSIONS:
                self.logger.warning(f"Safety exclusion: refusing to lock protected executable: {path}")
                continue
            
            # SPB Self-Protection: prevent locking its own binaries
            if "simpleproductivityblocker" in path.lower() or "spb_" in path.lower():
                continue
                
            try:
                # Open with no share mode (0) - this is an exclusive lock
                handle = win32file.CreateFile(
                    path,
                    win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                    0, # 0 means exclusive lock, no sharing
                    None,
                    win32con.OPEN_EXISTING,
                    win32con.FILE_ATTRIBUTE_NORMAL,
                    None
                )
                self._locked_files.append(handle)
                self.logger.info(f"EXCLUSIVE LOCK: {path}")
            except Exception as e:
                self.logger.debug(f"Handle Lock Failed for {path}: {e}")

    def _unlock_files(self):
        """Release all exclusive handles."""
        if os.name != 'nt': return
        for h in self._locked_files:
            try: win32file.CloseHandle(h)
            except: pass
        self._locked_files.clear()

    def _check_shell_windows(self, shell):
        try:
            targets = []
            for window in shell.Windows():
                try:
                    url = getattr(window, "LocationURL", "")
                    if url.startswith("file:///"):
                        path = urllib.parse.unquote(url[8:]).replace('/', '\\')
                        path_norm = self._normalize_path(path)
                        if self._is_in_blocked_folder(path_norm):
                            targets.append(window)
                except Exception: continue
            for window in targets:
                try: window.Quit()
                except Exception:
                    try: window.Navigate("C:\\")
                    except Exception: pass
        except Exception: pass

    def _should_terminate_proc(self, proc, now, last_handle_check):
        try:
            info = proc.info
            name_lower = (info.get('name') or "").lower()
            exe = (info.get('exe') or "").lower()
            cmdline = info.get('cmdline') or []
            exe_base = os.path.basename(exe).lower() if exe else ""

            # Absolute bypass for core system safety targets
            if name_lower in SYSTEM_SAFETY_EXCLUSIONS or exe_base in SYSTEM_SAFETY_EXCLUSIONS:
                return False
            
            if "target_app" in name_lower or "target_app" in exe:
                pass

            # 0. Global Allowlist (Cloud Allowlist) - OVERRIDES ALL
            if name_lower in self._global_allowlisted_processes: return False
            if self._global_allowlisted_keywords:
                search = exe + " " + " ".join(str(a).lower() for a in cmdline)
                import re
                for kw in self._global_allowlisted_keywords:
                    try:
                        if re.search(kw, search, re.IGNORECASE): return False
                    except re.error:
                        if kw in search: return False

            # 1. Explicit App/File Blocks (Override Allowlist)
            if name_lower in self.blocked_app_names:
                self.logger.info(f"TERMINATING: {name_lower} (App Name Blocked)")
                return True

            if exe:
                exe_norm = self._normalize_path(exe)
                if exe_norm in self.blocked_app_paths:
                    self.logger.info(f"TERMINATING: {name_lower} (App Path Blocked: {exe_norm})")
                    return True

            if cmdline:
                cmdline_str = " ".join(str(a).lower() for a in cmdline)
                for bp in self.blocked_file_paths:
                    if bp.lower() in cmdline_str:
                        for arg in cmdline:
                            if bp.lower() in str(arg).lower():
                                self.logger.info(f"TERMINATING: {name_lower} (Blocked File in Cmdline: {bp})")
                                return True

            # 2. Allowlist Exceptions (Group Level)
            if self._allowlist_enabled:
                if name_lower in self._allowlisted_processes: return False
                if self._allowlisted_keywords:
                    search = exe + " " + " ".join(str(a).lower() for a in cmdline)
                    import re
                    for kw in self._allowlisted_keywords:
                        try:
                            if re.search(kw, search, re.IGNORECASE): return False
                        except re.error:
                            if kw in search: return False

            # 3. Folder Blocks (Can be bypassed by Allowlist)
            if exe:
                if self._is_in_blocked_folder(exe_norm):
                    self.logger.info(f"TERMINATING: {name_lower} (App in Blocked Folder: {exe_norm})")
                    return True

            try:
                cwd = proc.cwd()
                if cwd:
                    cwd_norm = self._normalize_path(cwd)
                    if self._is_in_blocked_folder(cwd_norm):
                        self.logger.info(f"TERMINATING: {name_lower} (CWD in Blocked Folder: {cwd_norm})")
                        return True
            except: pass

            # Note: Vector 4 (aggressive termination on handle access) is disabled on Windows 
            # to prevent kernel deadlocks caused by psutil.open_files().
            return False
        except: return False

    def _watch_processes(self):
        shell = None
        if pythoncom and win32com:
            try:
                pythoncom.CoInitialize()
                shell = win32com.client.Dispatch("Shell.Application")
            except: pass
            
        last_handle_check = 0.0
        while not self._stop_event.is_set():
            now = time.time()
            if self.blocked_folder_roots and shell and (now - self._last_shell_check) >= self._shell_interval:
                self._last_shell_check = now
                self._check_shell_windows(shell)

            if self.blocked_app_names or self.blocked_app_paths or self.blocked_file_paths or self.blocked_folder_roots:
                for proc in psutil.process_iter(['name', 'exe', 'cmdline']):
                    if self._should_terminate_proc(proc, now, last_handle_check):
                        try: proc.kill()
                        except: pass
                
                if (now - last_handle_check) >= 10.0:
                    last_handle_check = now

            interval = self._fast_interval if now < self._fast_until else self._base_interval
            time.sleep(interval)

    def synchronize_lock(self, path: str, should_be_locked: bool):
        """Public interface for the daemon's safe-boot engine to reconcile historical locks.
        Invokes the full multi-vector protection suite (ACLs + Registry + Handles).
        This method is SURGICAL and ADDITIVE to support recovery loops.
        """
        if not should_be_locked:
            if os.path.isfile(path):
                new_list = [p for p in self.blocked_file_paths if p != path]
                self.set_blocked_files(new_list)
            elif os.path.isdir(path):
                new_list = [p for p in self.blocked_folder_roots if p != path]
                self.set_blocked_folders(new_list)
            return True # Successfully queued

        # Additive blocking
        if os.path.isfile(path):
            new_list = list(set(self.blocked_file_paths).union({path}))
            self.set_blocked_files(new_list)
        elif os.path.isdir(path):
            new_list = list(set(self.blocked_folder_roots).union({path}))
            self.set_blocked_folders(new_list)
    def synchronize_all(self, apps, files, folders):
        """Reconcile the entire process monitor state with a new set of targets.
        Used by the daemon's main loop to ensure all vectors stay consistent.
        """
        apps = list(apps or [])
        files = list(files or [])
        folders = list(folders or [])
        should_run = bool(apps or files or folders)

        self.set_blocked_apps(apps)
        self.set_blocked_files(files)
        self.set_blocked_folders(folders)

        if should_run and not self.is_active:
            self.logger.info(
                f"ProcessMonitor target sync requires enforcement: {len(apps)} apps, {len(files)} files, {len(folders)} folders."
            )
            self.start()
        elif not should_run and self.is_active:
            self.logger.info("ProcessMonitor target sync is empty; stopping enforcement and clearing locks.")
            self.stop()
        else:
            self.logger.info(
                f"ProcessMonitor synchronized: active={self.is_active}, {len(apps)} apps, {len(files)} files, {len(folders)} folders."
            )

    def batch_unlock(self, paths: list):
        """Optimized batch unlock for recovery scenarios."""
        if not paths: return
        self.logger.info(f"BATCH UNLOCK: Processing {len(paths)} paths...")
        for path in paths:
            self._set_acl_lock(path, False)
        # Re-sync internal lists
        self.blocked_file_paths = {p for p in self.blocked_file_paths if p not in paths}
        self.blocked_folder_roots = [p for p in self.blocked_folder_roots if p not in paths]
        self.blocked_folder_prefixes = [(r if r.endswith(os.path.sep) else r + os.path.sep) for r in self.blocked_folder_roots]
        self._lock_files() # Refresh handle locks
