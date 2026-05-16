import os
import sys
import subprocess
import json
import time
import logging

logger = logging.getLogger("SPB_Daemon")

class PlatformHandler:
    def get_hosts_path(self):
        raise NotImplementedError
    
    def get_backup_hosts_path(self):
        raise NotImplementedError

    def get_dns_state_file(self):
        raise NotImplementedError

    def get_data_dir(self):
        raise NotImplementedError

    def is_admin(self):
        raise NotImplementedError

    def flush_dns(self):
        raise NotImplementedError

    def set_startup(self, enabled):
        raise NotImplementedError

    def is_startup_enabled(self):
        raise NotImplementedError

    def redirect_dns(self, activate, local_ip="127.0.0.1", state_path=None):
        raise NotImplementedError

    def apply_browser_policies(self, activate=True):
        raise NotImplementedError

    def get_system_dns(self):
        raise NotImplementedError
    
    def dns_points_to_local(self, local_ip="127.0.0.1", state_path=None):
        """Return True when platform DNS redirection remains pointed at local resolver addresses."""
        return True

    def audit_dns_safety(self, state_path=None):
        return {}

class WindowsHandler(PlatformHandler):
    PROTECTED_ADAPTER_KEYWORDS = (
        "tailscale", "wintun", "wireguard", "openvpn", "zerotier", "vpn",
        "portmaster", "proton", "mullvad", "nord", "zscaler", "globalprotect",
        "anyconnect", "fortinet", "forti", "cloudflare", "adguard", "nextdns"
    )
    CONFLICT_SERVICE_KEYWORDS = (
        "Portmaster", "VPN", "WireGuard", "OpenVPN", "Tailscale", "ZeroTier",
        "Wintun", "Nord", "Mullvad", "Cisco", "AnyConnect", "Zscaler",
        "GlobalProtect", "Forti", "Cloudflare", "Proton", "Surfshark",
        "ExpressVPN", "AdGuard", "NextDNS", "YogaDNS", "Acrylic", "Dnscrypt", "Stubby"
    )

    def get_hosts_path(self):
        return r"C:\Windows\System32\drivers\etc\hosts"

    def get_backup_hosts_path(self):
        return r"C:\Windows\System32\drivers\etc\hosts.backup"

    def get_dns_state_file(self):
        return os.path.join(self.get_data_dir(), "dns_state.json")

    def get_data_dir(self):
        return os.path.join(os.getenv("PROGRAMDATA", r"C:\ProgramData"), "SimpleProductivityBlocker")

    def is_admin(self):
        from core.win32_utils import is_admin as win_is_admin
        return win_is_admin()

    def flush_dns(self):
        subprocess.run("ipconfig /flushdns", shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def set_startup(self, enabled):
        from core.persistence import set_startup as win_set_startup
        return win_set_startup(enabled)

    def is_startup_enabled(self):
        from core.persistence import is_startup_enabled as win_is_startup
        return win_is_startup()

    def _run_powershell_json(self, script: str):
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip() or "PowerShell command failed")
        text = res.stdout.strip()
        if not text: return []
        data = json.loads(text)
        return data if isinstance(data, list) else [data]

    def redirect_dns(self, activate, local_ip="127.0.0.1", state_path=None):
        if not state_path: state_path = self.get_dns_state_file()
        try:
            if activate:
                state = self._snapshot_dns_state(state_path=state_path)
                if state.get("warnings"):
                    for warning in state["warnings"]:
                        logger.warning(f"DNS safety: {warning}")
                return self._apply_local_dns(state, ipv4=local_ip, state_path=state_path)
            else:
                return self._restore_dns_state(state_path=state_path)
        except Exception as e:
            logger.error(f"Failed to modify system DNS: {e}")
            return False

    def _snapshot_dns_state(self, state_path):
        script = r"""
$items = Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | ForEach-Object {
  $idx = $_.ifIndex
  $v4 = @(Get-DnsClientServerAddress -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ServerAddresses)
  $v6 = @(Get-DnsClientServerAddress -InterfaceIndex $idx -AddressFamily IPv6 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ServerAddresses)
  [pscustomobject]@{ alias = $_.Name; description = $_.InterfaceDescription; index = $idx; status = $_.Status; ipv4 = $v4; ipv6 = $v6 }
}
$items | ConvertTo-Json -Depth 4
"""
        adapters = self._run_powershell_json(script)
        normalized = []
        eligible = []
        warnings = []
        for item in adapters:
            adapter = {
                "alias": str(item.get("alias", "")),
                "description": str(item.get("description", "")),
                "index": int(item.get("index", 0)),
                "ipv4": item.get("ipv4", []),
                "ipv6": item.get("ipv6", [])
            }
            haystack = (adapter["alias"] + " " + adapter["description"]).lower()
            protected = any(k in haystack for k in self.PROTECTED_ADAPTER_KEYWORDS)
            if protected:
                warnings.append(f"Skipping protected adapter: {adapter['alias']}")
            elif adapter["index"] > 0:
                eligible.append(adapter["index"])
            normalized.append(adapter)
        
        return {
            "version": 1,
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "adapters": normalized,
            "eligible": eligible,
            "warnings": warnings
        }

    def _apply_local_dns(self, state, ipv4, state_path):
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, "w") as f: json.dump(state, f, indent=2)
        
        ok = True
        for idx in state["eligible"]:
            script = f"Set-DnsClientServerAddress -InterfaceIndex {idx} -ServerAddresses @('{ipv4}', '::1')"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.returncode != 0: ok = False
        return ok

    def _restore_dns_state(self, state_path):
        if not os.path.exists(state_path): return False
        try:
            with open(state_path, "r") as f: state = json.load(f)
            ok = True
            for adapter in state["adapters"]:
                if adapter["index"] in state["eligible"]:
                    orig = adapter["ipv4"] + adapter["ipv6"]
                    if orig:
                        quoted = ", ".join(f"'{s}'" for s in orig)
                        script = f"Set-DnsClientServerAddress -InterfaceIndex {adapter['index']} -ServerAddresses @({quoted})"
                    else:
                        script = f"Set-DnsClientServerAddress -InterfaceIndex {adapter['index']} -ResetServerAddresses"
                    res = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    if res.returncode != 0: ok = False
            if ok: os.remove(state_path)
            return ok
        except: return False

    def audit_dns_safety(self, state_path=None):
        if not state_path: state_path = self.get_dns_state_file()
        state = self._snapshot_dns_state(state_path)
        conflicts = []
        pattern = "|".join(self.CONFLICT_SERVICE_KEYWORDS)
        script = f"Get-Service | Where-Object {{$_.Name -match '{pattern}' -or $_.DisplayName -match '{pattern}'}} | Select-Object Name,DisplayName,Status | ConvertTo-Json"
        try: conflicts = self._run_powershell_json(script)
        except: pass
        return {
            "eligible": state["eligible"],
            "warnings": state["warnings"],
            "conflicting_services": conflicts,
            "stored_state_exists": os.path.exists(state_path)
        }
    
    def get_system_dns(self):
        script = 'Get-DnsClientServerAddress | Where-Object {$_.ServerAddresses -ne $null} | Select-Object -ExpandProperty ServerAddresses'
        try: return self._run_powershell_json(script)
        except: return []
    
    def dns_points_to_local(self, local_ip="127.0.0.1", state_path=None):
        """Validate that eligible active adapters still resolve DNS through localhost loopbacks."""
        if not state_path:
            state_path = self.get_dns_state_file()
        try:
            allowed_loopbacks = {"127.0.0.1", "::1"}
            if local_ip:
                allowed_loopbacks.add(str(local_ip).strip())
            state = self._snapshot_dns_state(state_path)
            eligible = set(state.get("eligible", []))
            if not eligible:
                return True
            for adapter in state.get("adapters", []):
                if adapter.get("index") not in eligible:
                    continue
                raw_ips = (adapter.get("ipv4") or []) + (adapter.get("ipv6") or [])
                configured = [str(ip).strip() for ip in raw_ips]
                configured = [ip for ip in configured if ip]
                if not any(ip in allowed_loopbacks for ip in configured):
                    return False
            return True
        except Exception as e:
            logger.debug(f"dns_points_to_local check failed: {e}")
            return False

    def apply_browser_policies(self, activate=True):
        import winreg
        policies = [
            # Chrome
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Google\Chrome", "DnsOverHttpsMode", "off", winreg.REG_SZ),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Google\Chrome", "BuiltInDnsClientEnabled", 0, winreg.REG_DWORD),
            # Edge
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Edge", "DnsOverHttpsMode", "off", winreg.REG_SZ),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Edge", "BuiltInDnsClientEnabled", 0, winreg.REG_DWORD),
            # Firefox
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Mozilla\Firefox\DNSOverHTTPS", "Enabled", 0, winreg.REG_DWORD),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Mozilla\Firefox\DNSOverHTTPS", "Locked", 1, winreg.REG_DWORD)
        ]
        for root, path, name, value, vtype in policies:
            try:
                if activate:
                    key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, name, 0, vtype, value)
                    winreg.CloseKey(key)
                else:
                    try:
                        key = winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE)
                        winreg.DeleteValue(key, name)
                        winreg.CloseKey(key)
                    except FileNotFoundError: pass
            except: pass

class LinuxHandler(PlatformHandler):
    def get_hosts_path(self):
        return "/etc/hosts"

    def get_backup_hosts_path(self):
        return "/etc/hosts.backup"

    def get_dns_state_file(self):
        return os.path.join(self.get_data_dir(), "dns_state.json")

    def get_data_dir(self):
        return os.path.expanduser("~/.config/SimpleProductivityBlocker")

    def is_admin(self):
        return os.getuid() == 0

    def flush_dns(self):
        commands = [
            ["systemd-resolve", "--flush-caches"],
            ["resolvectl", "flush-caches"],
            ["/etc/init.d/nscd", "restart"]
        ]
        for cmd in commands:
            try: subprocess.run(cmd, capture_output=True)
            except: continue

    def set_startup(self, enabled):
        return False

    def is_startup_enabled(self):
        return False

    def redirect_dns(self, activate, local_ip="127.0.0.1", state_path=None):
        return False

    def apply_browser_policies(self, activate=True):
        return False

    def get_system_dns(self):
        dns_servers = []
        if os.path.exists('/etc/resolv.conf'):
            with open('/etc/resolv.conf', 'r') as f:
                for line in f:
                    if line.startswith('nameserver'):
                        ip = line.split()[1].strip()
                        dns_servers.append(ip)
        return dns_servers

    def dns_points_to_local(self, local_ip="127.0.0.1", state_path=None):
        return True

def get_platform_handler():
    if os.name == 'nt':
        return WindowsHandler()
    else:
        return LinuxHandler()
