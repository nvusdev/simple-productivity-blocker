import psutil
import threading
import time

class AppBlocker:
    def __init__(self):
        self.blocked_apps = []
        self.is_active = False
        self._watcher_thread = None
        self._stop_event = threading.Event()

    def set_blocked_apps(self, apps):
        self.blocked_apps = [app.lower().strip() for app in apps]

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
        import os
        while not self._stop_event.is_set():
            if self.blocked_apps:
                for proc in psutil.process_iter(['name', 'pid', 'exe']):
                    try:
                        name = proc.info.get('name')
                        exe = proc.info.get('exe')
                        
                        should_kill = False
                        
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

                        if should_kill:
                            proc.kill()
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
            time.sleep(1)
