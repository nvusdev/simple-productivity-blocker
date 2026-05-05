import os
import sys
import subprocess

class PlatformHandler:
    def get_hosts_path(self):
        raise NotImplementedError
    
    def flush_dns(self):
        raise NotImplementedError

    def set_startup(self, enabled):
        raise NotImplementedError

    def is_startup_enabled(self):
        raise NotImplementedError

    def redirect_dns(self, activate, local_ip="127.0.0.1"):
        raise NotImplementedError

class WindowsHandler(PlatformHandler):
    def get_hosts_path(self):
        return r"C:\Windows\System32\drivers\etc\hosts"

    def flush_dns(self):
        subprocess.run("ipconfig /flushdns", shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def set_startup(self, enabled):
        from core.persistence import set_startup as win_set_startup
        return win_set_startup(enabled)

    def is_startup_enabled(self):
        from core.persistence import is_startup_enabled as win_is_startup
        return win_is_startup()

    def redirect_dns(self, activate, local_ip="127.0.0.1"):
        try:
            if activate:
                cmd = f'powershell -Command "Get-NetAdapter | Where-Object {{$_.Status -eq \'Up\'}} | ForEach-Object {{ Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ServerAddresses \'{local_ip}\' }}"'
            else:
                cmd = 'powershell -Command "Get-NetAdapter | Where-Object {$_.Status -eq \'Up\'} | ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ResetServerAddresses }"'
            subprocess.run(cmd, shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except Exception:
            return False

class LinuxHandler(PlatformHandler):
    def get_hosts_path(self):
        return "/etc/hosts"

    def flush_dns(self):
        # Common Linux DNS flush commands
        commands = [
            ["systemd-resolve", "--flush-caches"],
            ["resolvectl", "flush-caches"],
            ["/etc/init.d/nscd", "restart"]
        ]
        for cmd in commands:
            try: subprocess.run(cmd, capture_output=True)
            except: continue

    def set_startup(self, enabled):
        # Will implement systemd unit management in v1.3.1
        return False

    def is_startup_enabled(self):
        # Will check for systemd unit in v1.3.1
        return False

    def redirect_dns(self, activate, local_ip="127.0.0.1"):
        # Will implement nftables / resolv.conf logic in v1.3.1
        return False

def get_platform_handler():
    if os.name == 'nt':
        return WindowsHandler()
    else:
        return LinuxHandler()
