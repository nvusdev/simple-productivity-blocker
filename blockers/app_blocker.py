import psutil
import threading
import time
import os
import pythoncom
import win32com.client
import urllib.parse
try:
    import portalocker
    HAS_PORTALOCKER = True
except ImportError:
    HAS_PORTALOCKER = False
    print("Warning: 'portalocker' module not found. File locking will be disabled.")
import sys

if os.name == 'nt':
    import winreg

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
        self._allowlist_enabled = True
        self._locked_files = []

    def configure_performance(self, mode):
        mode = (mode or "").strip().lower()
        if mode == "aggressive":
            self._fast_interval = 0.25
            self._base_interval = 0.5
            self._shell_interval = 1.0
        elif mode == "eco":
            self._fast_interval = 1.0
            self._base_interval = 2.0
            self._shell_interval = 3.0
        else:
            self._fast_interval = 0.5
            self._base_interval = 1.0
            self._shell_interval = 2.0

    def set_allowlisted_processes(self, processes, enabled=True):
        self._allowlist_enabled = bool(enabled)
        self._allowlisted_processes = {
            str(p).strip().lower() for p in (processes or []) if str(p).strip()
        }

    def set_allowlisted_keywords(self, keywords):
        self._allowlisted_keywords = {
            str(k).strip().lower() for k in (keywords or []) if str(k).strip()
        }

    def _normalize_path(self, path):
        return os.path.normcase(os.path.abspath(path))

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

    def _arg_mentions_filename(self, arg_lower, name):
        if arg_lower == name:
            return True
        if arg_lower.endswith(os.path.sep + name):
            return True
        if os.path.altsep and arg_lower.endswith(os.path.altsep + name):
            return True
        if "=" in arg_lower and arg_lower.endswith(name):
            return True
        return False

    def _is_in_blocked_folder(self, path_norm):
        for root, prefix in zip(self.blocked_folder_roots, self.blocked_folder_prefixes):
            if path_norm == root or path_norm.startswith(prefix):
                return True
        return False

    def set_blocked_apps(self, apps):
        self._fast_until = time.time() + 10
        self.blocked_app_names.clear()
        self.blocked_app_paths.clear()
        for app in apps:
            app = app.strip()
            if not app:
                continue
            app_lower = app.lower()
            base = os.path.basename(app_lower)
            if base:
                self.blocked_app_names.add(base)
                stem = os.path.splitext(base)[0]
                if stem and stem != base:
                    self.blocked_app_names.add(stem)
            if self._looks_like_path(app):
                self.blocked_app_paths.add(self._normalize_path(app))
        
        if self.is_active:
            self._apply_disallow_run()

    def set_blocked_files(self, files):
        self._fast_until = time.time() + 10
        self.blocked_file_paths.clear()
        self.blocked_file_names.clear()
        for file_path in files:
            file_path = file_path.strip()
            if not file_path:
                continue
            norm = self._normalize_path(file_path)
            self.blocked_file_paths.add(norm)
            base = os.path.basename(norm)
            if base:
                self.blocked_file_names.add(base.lower())
        
        if self.is_active:
            self._apply_file_locks()

    def set_blocked_folders(self, folders):
        self._fast_until = time.time() + 10
        self.blocked_folder_roots = []
        self.blocked_folder_prefixes = []
        for folder in folders:
            folder = folder.strip()
            if not folder:
                continue
            root = self._normalize_path(folder)
            prefix = root if root.endswith(os.path.sep) else root + os.path.sep
            self.blocked_folder_roots.append(root)
            self.blocked_folder_prefixes.append(prefix)

    def start(self):
        if self.is_active:
            return
        self.is_active = True
        self._stop_event.clear()
        self._apply_disallow_run()
        self._apply_file_locks()
        self._watcher_thread = threading.Thread(target=self._watch_processes, daemon=True)
        self._watcher_thread.start()

    def stop(self):
        self.is_active = False
        self._stop_event.set()
        self._clear_disallow_run()
        self._clear_file_locks()
        if self._watcher_thread:
            self._watcher_thread.join(timeout=2)

    def _apply_disallow_run(self):
        if os.name != 'nt': return
        try:
            # 1. Enable DisallowRun policy
            policy_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer")
            winreg.SetValueEx(policy_key, "DisallowRun", 0, winreg.REG_DWORD, 1)
            
            # 2. Fill the DisallowRun list
            list_key = winreg.CreateKey(policy_key, "DisallowRun")
            # Clear existing
            try:
                i = 0
                while True:
                    name, _, _ = winreg.EnumValue(list_key, 0)
                    winreg.DeleteValue(list_key, name)
            except OSError:
                pass
            
            # Add new (only .exe names)
            idx = 1
            for app in self.blocked_app_names:
                if app.endswith(".exe"):
                    winreg.SetValueEx(list_key, str(idx), 0, winreg.REG_SZ, app)
                    idx += 1
            
            winreg.CloseKey(list_key)
            winreg.CloseKey(policy_key)
        except Exception as e:
            print(f"Failed to apply DisallowRun: {e}")

    def _clear_disallow_run(self):
        if os.name != 'nt': return
        try:
            policy_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(policy_key, "DisallowRun", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(policy_key)
        except Exception:
            pass

    def _apply_file_lock(self, file_path):
        if not HAS_PORTALOCKER:
            return
        try:
            # We open the file in read-mode with an exclusive lock (LockFlags.EXCLUSIVE | LockFlags.NON_BLOCKING)
            # This prevents other processes from opening the file.
            f = open(file_path, 'r')
            portalocker.lock(f, portalocker.LockFlags.EXCLUSIVE | portalocker.LockFlags.NON_BLOCKING)
            self.locked_file_handles[file_path] = f
        except (portalocker.exceptions.LockException, IOError):
            # File already in use or access denied, which is fine (it's effectively blocked)
            pass
        except Exception:
            pass

    def _apply_file_locks(self):
        self._clear_file_locks()
        for path in self.blocked_file_paths:
            try:
                if os.path.exists(path):
                    f = open(path, "rb+")
                    portalocker.lock(f, portalocker.LOCK_EX | portalocker.LOCK_NB)
                    self._locked_files.append(f)
            except Exception:
                continue

    def _clear_file_locks(self):
        for f in self._locked_files:
            try:
                portalocker.unlock(f)
                f.close()
            except Exception:
                pass
        self._locked_files = []

    def _watch_processes(self):
        shell = None
        try:
            pythoncom.CoInitialize()
            shell = win32com.client.Dispatch("Shell.Application")
        except:
            pass
            
        while not self._stop_event.is_set():
            now = time.time()
            if self.blocked_folder_roots and shell and (now - self._last_shell_check) >= self._shell_interval:
                self._last_shell_check = now
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
                        except Exception:
                            continue
                    
                    for window in targets:
                        try:
                            window.Quit()
                        except Exception:
                            try:
                                window.Navigate("C:\\")
                            except Exception:
                                pass
                except Exception:
                    pass

            # Polling loop remains for non-DisallowRun blocks (paths, cmdline args, folders)
            if self.blocked_app_paths or self.blocked_file_paths or self.blocked_folder_roots:
                for proc in psutil.process_iter(['name', 'pid', 'exe', 'cmdline']):
                    try:
                        name = proc.info.get('name')
                        exe = proc.info.get('exe')
                        cmdline = proc.info.get('cmdline')
                        name_lower = (name or "").lower()
                        
                        is_allowlisted = False
                        if self._allowlist_enabled:
                            if name_lower in self._allowlisted_processes:
                                is_allowlisted = True
                            if not is_allowlisted and self._allowlisted_keywords:
                                search_text = ""
                                if exe: search_text += exe.lower() + " "
                                if cmdline: search_text += " ".join(str(a).lower() for a in cmdline)
                                if any(kw in search_text for kw in self._allowlisted_keywords):
                                    is_allowlisted = True
                        
                        if is_allowlisted:
                            continue
                            
                        should_kill = False
                        if exe:
                            exe_norm = self._normalize_path(exe)
                            if exe_norm in self.blocked_app_paths:
                                should_kill = True
                            elif self._is_in_blocked_folder(exe_norm):
                                should_kill = True
                        
                        if not should_kill:
                            try:
                                cwd = proc.cwd()
                                if cwd:
                                    cwd_norm = self._normalize_path(cwd)
                                    if self._is_in_blocked_folder(cwd_norm):
                                        should_kill = True
                            except Exception:
                                pass

                        if not should_kill and cmdline:
                            for arg in cmdline:
                                arg_str = str(arg).strip("\"'")
                                if not arg_str: continue
                                for candidate in self._extract_path_candidates(arg_str):
                                    arg_norm = self._normalize_path(candidate)
                                    if arg_norm in self.blocked_file_paths or self._is_in_blocked_folder(arg_norm):
                                        should_kill = True
                                        break
                                if should_kill: break

                        if should_kill:
                            try:
                                proc.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass

            interval = self._fast_interval if time.time() < self._fast_until else self._base_interval
            time.sleep(interval)
