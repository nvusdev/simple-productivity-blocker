import psutil
import threading
import time
import os
import pythoncom
import win32com.client
import urllib.parse

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
        self._allowlist_enabled = True

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

    def _normalize_path(self, path):
        return os.path.normcase(os.path.abspath(path))

    def _looks_like_path(self, value):
        if not value:
            return False
        if os.path.isabs(value):
            return True
        if value.startswith("\\\\"):
            return True
        if len(value) >= 3 and value[1] == ":" and value[2] in ("\\", "/"):
            return True
        if os.path.sep in value:
            return True
        if os.path.altsep and os.path.altsep in value:
            return True
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
        self._watcher_thread = threading.Thread(target=self._watch_processes, daemon=True)
        self._watcher_thread.start()

    def stop(self):
        self.is_active = False
        self._stop_event.set()
        if self._watcher_thread:
            self._watcher_thread.join(timeout=2)

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


            if self.blocked_app_names or self.blocked_app_paths or self.blocked_file_paths or self.blocked_folder_roots:
                for proc in psutil.process_iter(['name', 'pid', 'exe', 'cmdline']):
                    try:
                        name = proc.info.get('name')
                        exe = proc.info.get('exe')
                        cmdline = proc.info.get('cmdline')
                        name_lower = (name or "").lower()
                        skip_file_folder = self._allowlist_enabled and name_lower in self._allowlisted_processes
                        
                        should_kill = False
                        
                        # 1. Check App Names
                        if name:
                            if name_lower in self.blocked_app_names:
                                should_kill = True

                        if exe and not should_kill:
                            exe_norm = self._normalize_path(exe)
                            exe_base = os.path.basename(exe_norm).lower()
                            if exe_base in self.blocked_app_names or exe_norm in self.blocked_app_paths:
                                should_kill = True

                        # 2. Check Folders in Exe Path or CWD
                        if not should_kill and self.blocked_folder_roots and not skip_file_folder:
                            if exe:
                                exe_norm = self._normalize_path(exe)
                                if self._is_in_blocked_folder(exe_norm):
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


                        # 3. Check File/Folder Paths in CmdLine
                        if not should_kill and cmdline and (self.blocked_app_names or self.blocked_app_paths or self.blocked_file_paths or self.blocked_folder_roots):
                            for arg in cmdline:
                                arg_str = str(arg).strip("\"'")
                                if not arg_str:
                                    continue

                                arg_lower = arg_str.lower()
                                for name in self.blocked_app_names:
                                    if self._arg_mentions_filename(arg_lower, name):
                                        should_kill = True
                                        break
                                if should_kill:
                                    break

                                if not skip_file_folder:
                                    for name in self.blocked_file_names:
                                        if self._arg_mentions_filename(arg_lower, name):
                                            should_kill = True
                                            break
                                    if should_kill:
                                        break

                                for candidate in self._extract_path_candidates(arg_str):
                                    arg_norm = self._normalize_path(candidate)
                                    if arg_norm in self.blocked_app_paths:
                                        should_kill = True
                                        break
                                    if not skip_file_folder and arg_norm in self.blocked_file_paths:
                                        should_kill = True
                                        break
                                    if not skip_file_folder and self.blocked_folder_roots and self._is_in_blocked_folder(arg_norm):
                                        should_kill = True
                                        break
                                if should_kill:
                                    break

                        if should_kill:
                            try:
                                proc.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass

            interval = self._fast_interval if time.time() < self._fast_until else self._base_interval
            time.sleep(interval)
