import psutil
import threading
import time
import os
import pythoncom
import win32com.client
import urllib.parse

class ProcessMonitor:
    def __init__(self):
        self.blocked_apps = []
        self.blocked_files = []
        self.blocked_folders = []
        self.is_active = False
        self._watcher_thread = None
        self._stop_event = threading.Event()

    def set_blocked_apps(self, apps):
        self.blocked_apps = [app.lower().strip() for app in apps]

    def set_blocked_files(self, files):
        # We store exact paths or basenames lowercased
        self.blocked_files = [f.lower().strip() for f in files]

    def set_blocked_folders(self, folders):
        self.blocked_folders = [os.path.normcase(os.path.abspath(f.strip())) for f in folders if f.strip()]

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
            if self.blocked_folders and shell:
                try:
                    for window in shell.Windows():
                        url = window.LocationURL
                        if url.startswith("file:///"):
                            path = urllib.parse.unquote(url[8:])
                            path = path.replace('/', '\\')
                            path_norm = os.path.normcase(os.path.abspath(path))
                            for bf in self.blocked_folders:
                                if path_norm.startswith(bf):
                                    window.Quit()
                                    break
                except Exception:
                    pass

            if self.blocked_apps or self.blocked_files or self.blocked_folders:
                for proc in psutil.process_iter(['name', 'pid', 'exe', 'cmdline']):
                    try:
                        name = proc.info.get('name')
                        exe = proc.info.get('exe')
                        cmdline = proc.info.get('cmdline')
                        
                        should_kill = False
                        
                        # 1. Check App Names
                        if name:
                            name_lower = name.lower()
                            if name_lower in self.blocked_apps:
                                should_kill = True
                            for blocked in self.blocked_apps:
                                if os.path.basename(blocked) == name_lower:
                                    should_kill = True
                                    
                        if exe and not should_kill:
                            exe_lower = exe.lower()
                            if exe_lower in self.blocked_apps:
                                should_kill = True

                        # 2. Check Folders in Exe Path
                        if exe and not should_kill and self.blocked_folders:
                            exe_norm = os.path.normcase(os.path.abspath(exe))
                            for bf in self.blocked_folders:
                                if exe_norm.startswith(bf):
                                    should_kill = True
                                    break

                        # 3. Check File/Folder Paths in CmdLine
                        if not should_kill and cmdline and (self.blocked_files or self.blocked_folders):
                            cmdline_str = " ".join([str(arg).lower() for arg in cmdline])
                            
                            if self.blocked_files:
                                for blocked_file in self.blocked_files:
                                    if blocked_file in cmdline_str:
                                        should_kill = True
                                        break
                                    basename = os.path.basename(blocked_file)
                                    if basename and basename in cmdline_str:
                                        should_kill = True
                                        break
                                        
                            if not should_kill and self.blocked_folders:
                                cmd_norm = cmdline_str.replace('/', '\\')
                                for bf in self.blocked_folders:
                                    if bf in cmd_norm:
                                        should_kill = True
                                        break

                        if should_kill:
                            proc.kill()
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
            time.sleep(1)
