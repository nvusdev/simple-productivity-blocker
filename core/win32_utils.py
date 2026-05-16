import os
import ctypes
import uuid
from ctypes import wintypes

# --- Win32 API Helpers ---
class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_byte * 8)
    ]
    def __init__(self, uuid_str):
        u = uuid.UUID(uuid_str)
        ctypes.Structure.__init__(self)
        self.Data1 = u.time_low
        self.Data2 = u.time_mid
        self.Data3 = u.time_hi_version
        for i in range(8):
            self.Data4[i] = u.bytes[8 + i]

def get_known_folder_path(folder_guid_str):
    """Securely resolve Windows Known Folders (Desktop, Program Files, etc)."""
    try:
        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
        SHGetKnownFolderPath.restype = wintypes.HRESULT
        
        folder_id = GUID(folder_guid_str)
        path_ptr = ctypes.c_void_p()
        
        result = SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None, ctypes.byref(path_ptr))
        if result == 0:
            path = ctypes.cast(path_ptr, ctypes.c_wchar_p).value
            ctypes.windll.ole32.CoTaskMemFree(path_ptr)
            return path
    except Exception:
        pass
    return None

def get_program_files_path():
    # FOLDERID_ProgramFiles: {905e63b6-c1bf-494e-b29c-65b732d3d21a}
    path = get_known_folder_path("{905e63b6-c1bf-494e-b29c-65b732d3d21a}")
    return path or os.environ.get("ProgramFiles", "C:\\Program Files")

def get_desktop_path():
    # FOLDERID_Desktop: {B4BFCC3A-DB2C-424C-B029-7FE99A87C641}
    path = get_known_folder_path("{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}")
    return path or os.path.join(os.environ["USERPROFILE"], "Desktop")

def is_admin():
    """Universal administrator check for Windows."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False
