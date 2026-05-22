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
    import win32api

# Absolute safety guardrails for essential Windows processes.
# These names must never be blocked, terminated, or locked by SPB enforcement code.
# Modifying this set can cause system instability or loss of administrative recovery paths.
SYSTEM_SAFETY_EXCLUSIONS = {
    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", 
    "services.exe", "lsass.exe", "svchost.exe", "dwm.exe", "fontdrvhost.exe",
    "sihost.exe", "runtimebroker.exe", "conhost.exe", "smartscreen.exe",
    "explorer.exe", "taskmgr.exe", "spoolsv.exe", "notepad.exe", "python.exe", 
    "SimpleProductivityBlocker.exe", "SPB_Daemon.exe", "spb_installer.exe"
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
        self._locked_files_map = {}
        self._file_lock = threading.Lock()
        self._non_acl_sync_interval = 10
        self._non_acl_max_files = 1000
        self._last_sync_time = 0.0
        self._current_acl_paths = set()
        self._acl_sync_lock = threading.RLock()
        self._acl_queue = queue.Queue()
        self._username = getpass.getuser() if os.name == 'nt' else None
        from collections import OrderedDict
        self._path_cache = OrderedDict()
        self.logger = logging.getLogger("SPB_AppBlocker")
        
        # Enforcement settings (configurable by daemon)
        self.dialog_enforcement_enabled = True
        self.aggressive_process_enforcement = True
        self.aggressive_scan_interval = 10
        self.ui_automation_enabled = False
        self.shell_check_interval = 2.0

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

    def set_non_acl_sync_interval(self, val):
        try:
            self._non_acl_sync_interval = int(val)
        except Exception:
            self._non_acl_sync_interval = 10
        self.logger.info(f"Non-ACL Sync Interval set to: {self._non_acl_sync_interval}s")

    def set_non_acl_max_files(self, val):
        try:
            self._non_acl_max_files = int(val)
        except Exception:
            self._non_acl_max_files = 1000
        self.logger.info(f"Non-ACL Max Files set to: {self._non_acl_max_files}")

    def _get_volume_root(self, path):
        path = os.path.normpath(os.path.abspath(path))
        if path.startswith("\\\\"):
            parts = [p for p in path.split("\\") if p]
            if len(parts) >= 2:
                return f"\\\\{parts[0]}\\{parts[1]}\\"
            return "\\\\"
        drive = os.path.splitdrive(path)[0]
        if drive:
            return drive + "\\"
        return "C:\\"

    def _supports_acls(self, path):
        if os.name != 'nt':
            return False
        try:
            root = self._get_volume_root(path)
            _, _, _, flags, filesystem_name = win32api.GetVolumeInformation(root)
            filesystem_name = str(filesystem_name or "").strip().lower()
            self.logger.debug(f"Volume flags for {root}: {flags}; filesystem={filesystem_name or 'unknown'}")

            # Virtual/cloud mounts can advertise ACL support inconsistently. Only treat a volume as
            # ACL-capable when it is a known persistent-ACL filesystem and the persistent ACL flag is set.
            if filesystem_name in {"fat32", "exfat", "cdfs", "udf", "webdav", "remote storage"}:
                return False

            if filesystem_name and filesystem_name not in {"ntfs", "refs", "csvfs"}:
                return False

            # FILE_PERSISTENT_ACLS flag is 0x00000008 (verified: win32con.FILE_PERSISTENT_ACLS == 0x8)
            return bool(flags & 0x00000008)
        except Exception as e:
            self.logger.debug(f"Failed to check ACL support for {path}: {e}")
            return False

    def _get_all_files_in_folder(self, folder_path, max_files=1000):
        files = []
        if not os.path.exists(folder_path):
            return files
        try:
            for root_dir, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    files.append(os.path.join(root_dir, filename))
                    if max_files > 0 and len(files) >= max_files:
                        return files
        except Exception as e:
            self.logger.debug(f"Error walking directory {folder_path}: {e}")
        return files

    def _sync_locks_if_needed(self, now):
        if not self.is_active:
            return
        if now - self._last_sync_time >= self._non_acl_sync_interval:
            self._last_sync_time = now
            self._lock_files()

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
            self._path_cache.move_to_end(path)
            return self._path_cache[path]
        
        try:
            norm = os.path.normcase(os.path.abspath(path))
            self._path_cache[path] = norm
            if len(self._path_cache) > 2000:
                self._path_cache.popitem(last=False)
            return norm
        except Exception as e:
            self.logger.debug(f"Normalization failed for {path}: {e}")
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

    def _path_exists_safe(self, path: str) -> bool:
        path_norm = self._normalize_path(path)
        if path_norm in {self._normalize_path(p) for p in self.blocked_folder_roots} or path_norm in {self._normalize_path(p) for p in self.blocked_file_paths}:
            return True
        try:
            os.stat(path)
            return True
        except PermissionError:
            return True
        except OSError:
            return False

    def _path_isdir_safe(self, path: str) -> bool:
        path_norm = self._normalize_path(path)
        if path_norm in {self._normalize_path(p) for p in self.blocked_folder_roots}:
            return True
        if path_norm in {self._normalize_path(p) for p in self.blocked_file_paths}:
            return False
        try:
            import win32file
            attrs = win32file.GetFileAttributes(path)
            return bool(attrs & win32file.FILE_ATTRIBUTE_DIRECTORY)
        except Exception:
            try:
                return os.path.isdir(path)
            except OSError:
                return False

    def _path_isfile_safe(self, path: str) -> bool:
        path_norm = self._normalize_path(path)
        if path_norm in {self._normalize_path(p) for p in self.blocked_file_paths}:
            return True
        if path_norm in {self._normalize_path(p) for p in self.blocked_folder_roots}:
            return False
        if not self._path_exists_safe(path):
            return False
        return not self._path_isdir_safe(path)

    def _apply_acl_internal(self, path, lock=True):
        if os.name != 'nt': return
        
        path = os.path.normpath(os.path.abspath(path))
        path_lower = path.lower()

        # Skip if filesystem does not support persistent ACLs
        if not self._supports_acls(path):
            self.logger.debug(f"Skipping ACL apply for {path} (volume does not support persistent ACLs)")
            return True

        # 1. Global Allowlist Check - strictly as literal substrings
        is_global_exempt = False
        if os.path.basename(path_lower) in self._global_allowlisted_processes:
            is_global_exempt = True
        else:
            if self._global_allowlisted_keywords:
                for kw in self._global_allowlisted_keywords:
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
                # Check by path keywords (strictly as literal substrings)
                else:
                    for kw in self._allowlisted_keywords:
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
        is_dir = self._path_isdir_safe(path)
        try:
            if lock:
                perm_flags = "(OI)(CI)(F)" if is_dir else "(F)"
                args = [
                    "icacls", path, "/inheritance:r", 
                    "/grant:r", f"*S-1-5-18:{perm_flags}",
                    "/grant:r", f"*S-1-5-32-544:{perm_flags}",
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
        with self._file_lock:
            targets = set()
            
            # Decouple: blocked_app_paths are locked via handles regardless of filesystem type
            for path in self.blocked_app_paths:
                path_norm = self._normalize_path(path)
                if not self._path_exists_safe(path_norm) or self._path_isdir_safe(path_norm):
                    continue
                if os.path.basename(path_norm).lower() in SYSTEM_SAFETY_EXCLUSIONS:
                    continue
                if "simpleproductivityblocker" in path_norm.lower() or "spb_" in path_norm.lower():
                    continue
                targets.add(path_norm)
                
            # Non-ACL file paths/folders fallback
            for path in self.blocked_file_paths:
                path_norm = self._normalize_path(path)
                if not self._supports_acls(path_norm):
                    if self._path_exists_safe(path_norm) and not self._path_isdir_safe(path_norm):
                        targets.add(path_norm)
                        
            for root in self.blocked_folder_roots:
                root_norm = self._normalize_path(root)
                if not self._supports_acls(root_norm):
                    # Recursively discover files inside root
                    files = self._get_all_files_in_folder(root_norm, max_files=self._non_acl_max_files)
                    for f in files:
                        f_norm = self._normalize_path(f)
                        if os.path.basename(f_norm).lower() in SYSTEM_SAFETY_EXCLUSIONS:
                            continue
                        if "simpleproductivityblocker" in f_norm.lower() or "spb_" in f_norm.lower():
                            continue
                        targets.add(f_norm)
                        
            # Close handles for files that are no longer targets
            for path in list(self._locked_files_map.keys()):
                if path not in targets:
                    h = self._locked_files_map.pop(path)
                    try:
                        win32file.CloseHandle(h)
                        self.logger.info(f"RELEASED LOCK: {path}")
                    except Exception as e:
                        self.logger.debug(f"Failed to release handle for {path}: {e}")
                        
            # Open handles for new target files
            for path in targets:
                if path in self._locked_files_map:
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
                    self._locked_files_map[path] = handle
                    self.logger.info(f"EXCLUSIVE LOCK: {path}")
                except Exception as e:
                    self.logger.debug(f"Handle Lock Failed for {path}: {e}")

    def _unlock_files(self):
        """Release all exclusive handles."""
        if os.name != 'nt': return
        with self._file_lock:
            for path, h in list(self._locked_files_map.items()):
                try:
                    win32file.CloseHandle(h)
                    self.logger.info(f"RELEASED LOCK: {path}")
                except OSError as e:
                    self.logger.debug(f"CloseHandle failed for {path}: {e}")
                except Exception as e:
                    self.logger.debug(f"Unexpected CloseHandle exception: {e}")
            self._locked_files_map.clear()

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
                except Exception as e:
                    self.logger.debug(f"Shell window URL query error: {e}")
                    continue
            for window in targets:
                try:
                    window.Quit()
                except Exception as e:
                    self.logger.debug(f"Failed to Quit window: {e}")
                    try:
                        window.Navigate("C:\\")
                    except Exception as ex:
                        self.logger.debug(f"Failed to Navigate window: {ex}")
        except Exception as e:
                self.logger.debug(f"Shell windows check failed: {e}")

    def _extract_path_via_uia(self, hwnd):
        """Attempt to extract file path via UI Automation (fallback for custom dialogs).
        Returns path string if found, None otherwise.
        """
        if not self.ui_automation_enabled:
            return None
        try:
            import ctypes
            from ctypes import wintypes
            
            # Lazy import pywinauto with UIA backend
            try:
                from pywinauto import Desktop
                from pywinauto.uia_defines import ELEMENT_INFO_MAPPING
            except ImportError:
                self.logger.debug("pywinauto not installed, skipping UIA fallback")
                return None
            
            try:
                app_window = Desktop(backend='uia').from_handle(hwnd)
                # Search for common path controls: Edit boxes, ComboBox, breadcrumb
                for control in app_window.descendants():
                    try:
                        if control.class_name() in ['Edit', 'ComboBox']:
                            text = control.get_value() or control.window_text()
                            if text and (':\\' in text or '\\\\' in text):
                                return text
                    except Exception:
                        pass
                return None
            except Exception as e:
                self.logger.debug(f"UIA dialog path extraction failed: {e}")
                return None
        except Exception as e:
            self.logger.debug(f"UIA fallback error: {e}")
            return None

    def _check_file_dialog_windows(self):
        """Enumerate top-level dialogs and close file-open dialogs showing blocked folders."""
        if os.name != 'nt':
            return
        try:
            import win32gui, win32process, win32con
        except Exception as e:
            self.logger.debug(f"File dialog check dependencies missing: {e}")
            return

        def enum_handler(hwnd, lParam):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                cls = win32gui.GetClassName(hwnd)
                # Common file dialog class is '#32770'
                if cls != '#32770':
                    return True
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                except Exception:
                    return True
                try:
                    proc = psutil.Process(pid)
                except Exception:
                    return True
                name_lower = (proc.name() or "").lower()
                # Respect global allowlist and local allowlist
                if name_lower in self._global_allowlisted_processes or name_lower in self._allowlisted_processes:
                    return True

                # Try to extract text from title and child controls as path candidates
                path_candidates = []
                try:
                    title = win32gui.GetWindowText(hwnd) or ""
                    if title:
                        path_candidates.extend(self._extract_path_candidates(title))
                except Exception:
                    pass

                try:
                    # collect some child texts (shallow scan)
                    child = win32gui.FindWindowEx(hwnd, 0, None, None)
                    stack = [child] if child else []
                    while stack:
                        ch = stack.pop()
                        try:
                            txt = win32gui.GetWindowText(ch)
                            if txt:
                                path_candidates.extend(self._extract_path_candidates(txt))
                        except Exception:
                            pass
                        # push next sibling and first child
                        try:
                            sib = win32gui.FindWindowEx(hwnd, ch, None, None)
                            if sib:
                                stack.append(sib)
                        except Exception:
                            pass
                        try:
                            first_child = win32gui.FindWindowEx(ch, 0, None, None)
                            if first_child:
                                stack.append(first_child)
                        except Exception:
                            pass
                except Exception:
                    pass

                for p in path_candidates:
                    p_norm = self._normalize_path(p)
                    if self._is_in_blocked_folder(p_norm):
                        try:
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                            self.logger.info(f"Dialog closed (blocked folder) for PID {pid}: {p_norm}")
                        except Exception as e:
                            self.logger.debug(f"Failed to close dialog hwnd {hwnd}: {e}")
                        return True
                
                if not path_candidates and self.ui_automation_enabled:
                    uia_path = self._extract_path_via_uia(hwnd)
                    if uia_path:
                        p_norm = self._normalize_path(uia_path)
                        if self._is_in_blocked_folder(p_norm):
                            try:
                                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                                self.logger.info(f"Dialog closed via UIA (blocked folder) for PID {pid}: {p_norm}")
                            except Exception as e:
                                self.logger.debug(f"Failed to close dialog hwnd {hwnd}: {e}")
                            return True
                return True
            except Exception as e:
                self.logger.debug(f"Dialog enum handler error: {e}")
                return True

        try:
            win32gui.EnumWindows(enum_handler, None)
        except Exception as e:
            self.logger.debug(f"EnumWindows failed: {e}")

    def _scan_process_open_files_and_enforce(self):
        """Scan process open files and terminate processes with handles inside blocked folders."""
        if not self.aggressive_process_enforcement:
            return
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name_lower = (proc.info.get('name') or "").lower()
                    if name_lower in SYSTEM_SAFETY_EXCLUSIONS: 
                        continue
                    if name_lower in self._global_allowlisted_processes:
                        continue
                    try:
                        files = proc.open_files()
                    except Exception:
                        continue
                    for f in files:
                        try:
                            f_norm = self._normalize_path(f.path)
                        except Exception:
                            continue
                        if self._is_in_blocked_folder(f_norm):
                            self.logger.info(f"TERMINATING: {name_lower} (Open file in blocked folder: {f_norm})")
                            try:
                                proc.kill()
                            except Exception as e:
                                self.logger.debug(f"Failed to kill process {proc.pid}: {e}")
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    self.logger.debug(f"Process scan error for PID {proc.pid if proc else 'unknown'}: {e}")
        except Exception as e:
            self.logger.debug(f"Process open-files scan failed: {e}")

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

            # Strict structural Windows directory protection
            if os.name == 'nt' and exe:
                system_root = os.environ.get("SystemRoot", "C:\\Windows").lower()
                if exe.startswith(system_root + os.sep) or exe == system_root:
                    return False

            # 0. Global Allowlist (Cloud Allowlist) - OVERRIDES ALL
            if name_lower in self._global_allowlisted_processes: 
                return False
                
            if exe and self._global_allowlisted_keywords:
                exe_norm = self._normalize_path(exe)
                for kw in self._global_allowlisted_keywords:
                    if kw in exe_norm: 
                        return False

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
                for arg in cmdline:
                    arg_str = str(arg)
                    candidates = self._extract_path_candidates(arg_str)
                    for candidate in candidates:
                        candidate_norm = self._normalize_path(candidate)
                        if candidate_norm in self.blocked_file_paths:
                            self.logger.info(f"TERMINATING: {name_lower} (Blocked File in Cmdline: {candidate_norm})")
                            return True
                        if self._is_in_blocked_folder(candidate_norm):
                            self.logger.info(f"TERMINATING: {name_lower} (Path inside Blocked Folder in Cmdline: {candidate_norm})")
                            return True

            # 2. Allowlist Exceptions (Group Level)
            if self._allowlist_enabled:
                if name_lower in self._allowlisted_processes: 
                    return False
                if exe and self._allowlisted_keywords:
                    exe_norm = self._normalize_path(exe)
                    for kw in self._allowlisted_keywords:
                        if kw in exe_norm: 
                            return False

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
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                self.logger.debug(f"Failed to read CWD for process {proc.pid}: {e}")
            except Exception as e:
                self.logger.debug(f"Unexpected exception reading CWD for process {proc.pid}: {e}")

            return False
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            self.logger.debug(f"Process query error for {proc.pid}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error in _should_terminate_proc: {e}", exc_info=True)
            return False

    def _watch_processes(self):
        shell = None
        if pythoncom and win32com:
            try:
                pythoncom.CoInitialize()
                shell = win32com.client.Dispatch("Shell.Application")
            except Exception as e:
                self.logger.debug(f"CoInitialize/Dispatch failed: {e}")
            
        last_handle_check = 0.0
        last_scan_check = 0.0
        while not self._stop_event.is_set():
            now = time.time()
            self._sync_locks_if_needed(now)
            if self.blocked_folder_roots and shell and (now - self._last_shell_check) >= self._shell_interval:
                self._last_shell_check = now
                self._check_shell_windows(shell)
                # Also attempt to close file dialogs owned by apps (MS common dialogs)
                if getattr(self, 'dialog_enforcement_enabled', True):
                    try:
                        self._check_file_dialog_windows()
                    except Exception as e:
                        self.logger.debug(f"File dialog check failed: {e}")
                # Aggressive scan for open files in blocked folders (throttled)
                if getattr(self, 'aggressive_process_enforcement', False) and (now - last_scan_check) >= getattr(self, 'aggressive_scan_interval', 10):
                    last_scan_check = now
                    try:
                        self._scan_process_open_files_and_enforce()
                    except Exception as e:
                        self.logger.debug(f"Process scan enforcement failed: {e}")

            if self.blocked_app_names or self.blocked_app_paths or self.blocked_file_paths or self.blocked_folder_roots:
                try:
                    for proc in psutil.process_iter(['name', 'exe', 'cmdline']):
                        if self._should_terminate_proc(proc, now, last_handle_check):
                            try:
                                proc.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                                self.logger.debug(f"Failed to kill process {proc.pid}: {e}")
                            except Exception as e:
                                self.logger.error(f"Unexpected error killing process {proc.pid}: {e}")
                except Exception as e:
                    self.logger.error(f"Error iterating processes: {e}")
                
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
            if self._path_isfile_safe(path):
                new_list = [p for p in self.blocked_file_paths if self._normalize_path(p) != self._normalize_path(path)]
                self.set_blocked_files(new_list)
            elif self._path_isdir_safe(path):
                new_list = [p for p in self.blocked_folder_roots if self._normalize_path(p) != self._normalize_path(path)]
                self.set_blocked_folders(new_list)
            return True # Successfully queued

        # Additive blocking
        if self._path_isfile_safe(path):
            new_list = list(set(self.blocked_file_paths).union({path}))
            self.set_blocked_files(new_list)
        elif self._path_isdir_safe(path):
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
