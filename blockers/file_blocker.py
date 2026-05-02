import os
import win32file
import win32con

class FileBlocker:
    def __init__(self):
        self.blocked_files = []
        self._file_handles = []

    def set_blocked_files(self, files):
        self.blocked_files = files

    def start(self):
        self._lock_files()

    def stop(self):
        self._unlock_files()

    def _lock_files(self):
        self._unlock_files()
        for file_path in self.blocked_files:
            if os.path.exists(file_path):
                try:
                    # Open with no share mode (0) - this is an exclusive lock
                    handle = win32file.CreateFile(
                        file_path,
                        win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                        0, # 0 means exclusive lock, no sharing
                        None,
                        win32con.OPEN_EXISTING,
                        win32con.FILE_ATTRIBUTE_NORMAL,
                        None
                    )
                    self._file_handles.append(handle)
                except Exception as e:
                    print(f"Failed to lock {file_path}: {e}")

    def _unlock_files(self):
        for handle in self._file_handles:
            try:
                win32file.CloseHandle(handle)
            except Exception:
                pass
        self._file_handles.clear()
