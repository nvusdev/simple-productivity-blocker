import win32com.client
import time

try:
    shell = win32com.client.Dispatch("Shell.Application")
    for window in shell.Windows():
        url = window.LocationURL
        if url.startswith("file:///"):
            print("Trying to close:", url)
            try:
                window.Quit()
            except Exception as e:
                print("Failed to Quit:", e)
                try:
                    window.Navigate("C:\\")
                except Exception as e2:
                    print("Failed to Navigate:", e2)
except Exception as e:
    print("Error:", e)
