import win32com.client
import urllib.parse
import os

try:
    shell = win32com.client.Dispatch("Shell.Application")
    for window in shell.Windows():
        url = window.LocationURL
        if url.startswith("file:///"):
            path = urllib.parse.unquote(url[8:])
            path = path.replace('/', '\\')
            print("Found window:", path)
except Exception as e:
    print("Error:", e)
