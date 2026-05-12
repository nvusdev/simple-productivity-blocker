import os
import logging
import socket
import threading
import re
import time
import subprocess
import psutil
import traceback
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Set, Any, Dict
from dnslib import DNSRecord, QTYPE, RR, A, AAAA, DNSHeader

logger = logging.getLogger("SPB_Daemon")
DNS_STATE_FILE = os.path.join(
    os.getenv("PROGRAMDATA", r"C:\ProgramData"),
    "SimpleProductivityBlocker",
    "dns_state.json"
) if os.name == 'nt' else os.path.expanduser("~/.config/SimpleProductivityBlocker/dns_state.json")

LOOPBACK_DNS = {"127.0.0.1", "::1"}
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

# Robust Import Hardening for flush_dns and HOSTS_FILE
HOSTS_FILE = r"C:\Windows\System32\drivers\etc\hosts" if os.name == 'nt' else "/etc/hosts"
def _f_dns(): pass
flush_dns = _f_dns

try:
    # Try importing as part of the package first
    try:
        from . import website_blocker as wb
    except (ImportError, ValueError):
        # Fallback to direct import if running as a script or standalone
        try:
            import blockers.website_blocker as wb
        except ImportError:
            import website_blocker as wb
            
    flush_dns = wb.flush_dns
    HOSTS_FILE = wb.HOSTS_FILE
except Exception as e:
    # Use debug logging to capture potential resolution issues without flooding console
    logger.debug(f"Module resolution fallback for website_blocker: {e}")

def _ensure_state_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)

def _run_powershell_json(script: str):
    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or "PowerShell command failed")
    text = res.stdout.strip()
    if not text:
        return []
    data = json.loads(text)
    return data if isinstance(data, list) else [data]

def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    return [str(value)] if str(value).strip() else []

def _is_loopback_only(addresses) -> bool:
    addresses = set(_as_list(addresses))
    return bool(addresses) and addresses.issubset(LOOPBACK_DNS)

def _has_non_loopback(addresses) -> bool:
    return any(a not in LOOPBACK_DNS for a in _as_list(addresses))

def _is_protected_adapter(adapter: Dict[str, Any]) -> bool:
    haystack = " ".join([
        str(adapter.get("alias", "")),
        str(adapter.get("description", "")),
    ]).lower()
    return any(k in haystack for k in PROTECTED_ADAPTER_KEYWORDS)

def snapshot_dns_state(adapters=None, state_path=DNS_STATE_FILE):
    """Capture active adapter DNS state and mark which adapters are safe to redirect."""
    if os.name != 'nt':
        return {"version": 1, "platform": os.name, "adapters": [], "eligible": [], "warnings": ["DNS snapshots are Windows-only."]}

    if adapters is None:
        script = r"""
$items = Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | ForEach-Object {
  $idx = $_.ifIndex
  $v4 = @(Get-DnsClientServerAddress -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ServerAddresses)
  $v6 = @(Get-DnsClientServerAddress -InterfaceIndex $idx -AddressFamily IPv6 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ServerAddresses)
  [pscustomobject]@{
    alias = $_.Name
    description = $_.InterfaceDescription
    index = $idx
    status = $_.Status
    ipv4 = $v4
    ipv6 = $v6
  }
}
$items | ConvertTo-Json -Depth 4
"""
        adapters = _run_powershell_json(script)

    warnings = []
    normalized = []
    eligible = []
    for item in adapters:
        adapter = {
            "alias": str(item.get("alias", item.get("Name", ""))),
            "description": str(item.get("description", item.get("InterfaceDescription", ""))),
            "index": int(item.get("index", item.get("InterfaceIndex", 0))),
            "status": str(item.get("status", item.get("Status", ""))),
            "ipv4": _as_list(item.get("ipv4", item.get("IPv4", []))),
            "ipv6": _as_list(item.get("ipv6", item.get("IPv6", []))),
        }
        adapter["protected"] = _is_protected_adapter(adapter)
        adapter["has_existing_dns"] = _has_non_loopback(adapter["ipv4"] + adapter["ipv6"])
        adapter["stale_loopback_dns"] = _is_loopback_only(adapter["ipv4"] + adapter["ipv6"])
        adapter["eligible"] = (
            adapter["index"] > 0
            and not adapter["protected"]
        )
        if adapter["protected"]:
            warnings.append(f"Skipping protected adapter: {adapter['alias']}")
        elif adapter["eligible"]:
            eligible.append(adapter["index"])
            if adapter["has_existing_dns"]:
                warnings.append(f"Intercepting adapter with custom DNS (used as upstream): {adapter['alias']}")
        normalized.append(adapter)

    state = {
        "version": 1,
        "platform": os.name,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "state_path": state_path,
        "adapters": normalized,
        "eligible": eligible,
        "warnings": list(dict.fromkeys(warnings)),
    }
    return state

def _save_dns_state(state, state_path=DNS_STATE_FILE):
    _ensure_state_dir(state_path)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def _load_dns_state(state_path=DNS_STATE_FILE):
    if not os.path.exists(state_path):
        return None
    with open(state_path, "r", encoding="utf-8") as f:
        return json.load(f)

def _set_adapter_dns(index: int, servers: List[str]) -> bool:
    if servers:
        quoted = ", ".join("'" + s.replace("'", "''") + "'" for s in servers)
        script = f"Set-DnsClientServerAddress -InterfaceIndex {int(index)} -ServerAddresses @({quoted})"
    else:
        script = f"Set-DnsClientServerAddress -InterfaceIndex {int(index)} -ResetServerAddresses"
    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )
    if res.returncode != 0:
        logger.error(f"PowerShell DNS Error for interface {index}: {res.stderr.strip()}")
        return False
    return True

def apply_local_dns(state, ipv4="127.0.0.1", ipv6="::1", state_path=DNS_STATE_FILE) -> bool:
    """Persist a snapshot, then point only eligible adapters at the local DNS proxy."""
    if os.name != 'nt':
        return False
    eligible = set(state.get("eligible", []))
    if not eligible:
        logger.warning("DNS safety: no adapters eligible for local DNS redirection.")
        return False
    _save_dns_state(state, state_path)
    ok = True
    for adapter in state.get("adapters", []):
        if adapter.get("index") not in eligible:
            continue
        if not _set_adapter_dns(adapter["index"], [ipv4, ipv6]):
            ok = False
    return ok

def restore_dns_state(state=None, state_path=DNS_STATE_FILE) -> bool:
    """Restore previously captured adapter DNS state."""
    if os.name != 'nt':
        return False
    if state is None:
        state = _load_dns_state(state_path)
    if not state:
        return False
    ok = True
    for adapter in state.get("adapters", []):
        if adapter.get("index") not in set(state.get("eligible", [])):
            continue
        original = _as_list(adapter.get("ipv4", [])) + _as_list(adapter.get("ipv6", []))
        if not _set_adapter_dns(adapter["index"], original):
            ok = False
    if ok:
        try:
            os.remove(state_path)
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug(f"DNS state cleanup failed: {e}")
    return ok

def audit_dns_safety(state_path=DNS_STATE_FILE):
    state = snapshot_dns_state(state_path=state_path)
    stale = [
        a["alias"] for a in state.get("adapters", [])
        if a.get("stale_loopback_dns") and not a.get("eligible")
    ]
    conflicts = []
    if os.name == 'nt':
        pattern = "|".join(CONFLICT_SERVICE_KEYWORDS)
        script = (
            "Get-Service | Where-Object {$_.Name -match '" + pattern + "' -or $_.DisplayName -match '" + pattern + "'} "
            "| Select-Object Name,DisplayName,Status,StartType | ConvertTo-Json -Depth 3"
        )
        try:
            conflicts = _run_powershell_json(script)
        except Exception as e:
            state.setdefault("warnings", []).append(f"Service audit failed: {e}")
    return {
        "adapters": state.get("adapters", []),
        "eligible": state.get("eligible", []),
        "warnings": state.get("warnings", []),
        "stale_loopback_adapters": stale,
        "conflicting_services": conflicts,
        "stored_state_exists": os.path.exists(state_path),
    }

class DomainMatcher:
    def __init__(self, patterns):
        self.exact_set = set()
        self.regex_pattern = None
        regex_parts = []
        
        for p in patterns:
            if not p: continue
            p = str(p).strip().lower()
            if not p: continue
            
            # Normalize: strip legacy keyword prefix
            if p.startswith("~"):
                p = p[1:]
                
            if "*" not in p and "." in p:
                self.exact_set.add(p)
                # Still add to regex for subdomain matching if it's a base domain
                regex_parts.append(self.compile_pattern_str(p))
            else:
                regex_parts.append(self.compile_pattern_str(p))
        
        if regex_parts:
            # Join all patterns with OR to leverage optimized regex engine
            self.regex_pattern = re.compile("|".join(regex_parts), re.IGNORECASE)

    def compile_pattern_str(self, p: str) -> str:
        """Returns the regex string for a pattern (without compiling).
        Handles:
        - *.domain.com: All subdomains
        - word*: Label prefix
        - *word: Label suffix
        - keyword: Any label starting with keyword
        - a*b: Wildcard within label
        """
        p = p.lower().strip()
        
        # 1. Special Case: Domain Wildcard (*.domain.com)
        if p.startswith("*."):
            base = re.escape(p[2:])
            return f"(?:^|.*\\.){base}$"

        # 2. Convert glob-style pattern to label-aware regex
        # We want '*' to match anything within a label (not crossing dots)
        # and the overall pattern to match a sequence of labels.
        
        # Escape everything except '*'
        parts = p.split('*')
        escaped_parts = [re.escape(part) for part in parts]
        
        # Join with [^.]* which matches anything except a dot
        # This keeps the wildcard within the scope of a label
        core_regex = "[^.]*".join(escaped_parts)
        
        # If it's a plain keyword (no dots, no wildcards), allow it to match as a label prefix
        # This matches user expectation: 'youtube' matches 'youtube-extra.com'
        if "." not in p and "*" not in p:
            core_regex = f"{core_regex}[^.]*"

        # Anchor to label boundaries (start of string or after a dot)
        # and end of label (end of string or before a dot)
        return f"(?:^|\\.){core_regex}(?:\\.|$)"

    def matches(self, domain: str) -> bool:
        if not domain: return False
        domain = domain.lower().rstrip('.')
        
        # 1. Fast Set Lookup (O(1))
        if domain in self.exact_set:
            return True
            
        # 2. Optimized Combined Regex Match
        if self.regex_pattern and self.regex_pattern.search(domain):
            return True
        return False

class DNSProxyServer:
    def __init__(self, manual_list, filter_list, cloud_list=None, filter_exceptions=None, upstream_dns=None, port=53, state_path=DNS_STATE_FILE):
        self.manual_matcher = DomainMatcher(manual_list)
        self.filter_matcher = DomainMatcher(filter_list)
        self.cloud_matcher = DomainMatcher(cloud_list if cloud_list else [])
        self.filter_exception_matcher = DomainMatcher(filter_exceptions if filter_exceptions else [])
        # Fallback to standard if no upstreams detected
        self.upstream_dnss = upstream_dns if upstream_dns else ["8.8.8.8", "1.1.1.1"]
        self.port = port
        self.host = '127.0.0.1'
        self.running = False
        self._sock = None
        self._sock6 = None
        self._state_path = state_path
        self._dns_state = None
        self._threads = []
        self._executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="DNSHandler")

    def update_rules(self, manual_list, filter_list, cloud_list, filter_exceptions):
        self.manual_matcher = DomainMatcher(manual_list)
        self.filter_matcher = DomainMatcher(filter_list)
        self.cloud_matcher = DomainMatcher(cloud_list)
        self.filter_exception_matcher = DomainMatcher(filter_exceptions)

    def start(self):
        try:
            # Create IPv4 socket
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Try to bind to all interfaces for IPv4
            try:
                self._sock.bind(('0.0.0.0', self.port))
            except socket.error:
                # Fallback to loopback if 0.0.0.0 fails
                self._sock.bind(('127.0.0.1', self.port))
            
            # Optional: Create IPv6 socket if supported
            self._sock6 = None
            try:
                self._sock6 = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                self._sock6.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # On some systems, binding to :: includes IPv4 (dual-stack)
                # but on Windows it usually doesn't by default unless configured.
                # We'll just bind to ::1 to catch local IPv6 DNS traffic.
                self._sock6.bind(('::1', self.port))
            except Exception as e:
                logger.debug(f"IPv6 DNS binding skipped/failed: {e}")
                self._sock6 = None

            self.running = True
            t4 = threading.Thread(target=self._serve, args=(self._sock,), daemon=True, name="DNS4ServeLoop")
            t4.start()
            self._threads = [t4]
            if self._sock6:
                t6 = threading.Thread(target=self._serve, args=(self._sock6,), daemon=True, name="DNS6ServeLoop")
                t6.start()
                self._threads.append(t6)
            
            # Direct system DNS to local proxy only for the real system DNS port.
            # Tests and high-port diagnostics must never rewrite real adapters.
            if os.name == 'nt' and self.port == 53:
                restore_dns_state(state_path=self._state_path)
                self._dns_state = snapshot_dns_state(state_path=self._state_path)
                res = self._redirect_system_dns(True)
                if not res:
                    logger.error("DNS Proxy started but failed to redirect system DNS. Protection is BYPASSED.")
                    self.stop()
                    return False
            
            flush_dns()
            logger.info(f"DNS Proxy Server active on port {self.port} (IPv4 + IPv6 Loopback)")
            return True
        except socket.error as se:
            conflicting_proc = "Unknown"
            pid = None
            try:
                # Granular diagnostic loop for port 53 contention
                for conn in psutil.net_connections(kind='udp4'):
                    if conn.laddr.port == self.port:
                        pid = conn.pid
                        if pid:
                            proc = psutil.Process(pid)
                            conflicting_proc = f"{proc.name()} (PID: {pid})"
                        break
            except (psutil.AccessDenied, psutil.NoSuchProcess) as pe:
                logger.debug(f"Permission denied while inspecting PID {pid}: {pe}")
                conflicting_proc = f"System/Admin Process (PID: {pid})" if pid else "Access Denied"
            except Exception as ex:
                logger.debug(f"Diagnostic error: {ex}")
            
            logger.error(f"DNS Proxy failed to bind to port {self.port}: {se}. (Potential Culprit: {conflicting_proc})")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error during DNS Proxy startup: {e}")
            return False

    def stop(self):
        self.running = False
        if os.name == 'nt' and self.port == 53:
            self._redirect_system_dns(False)
        for s in [self._sock, self._sock6]:
            if s:
                try: s.close()
                except: pass
        self._threads = []

    def _redirect_system_dns(self, activate):
        """Forces the system to use our local proxy for all active adapters."""
        try:
            if activate:
                state = self._dns_state or snapshot_dns_state(state_path=self._state_path)
                if state.get("warnings"):
                    for warning in state["warnings"]:
                        logger.warning(f"DNS safety: {warning}")
                return apply_local_dns(state, state_path=self._state_path)
            else:
                return restore_dns_state(state_path=self._state_path)
        except Exception as e:
            logger.error(f"Failed to modify system DNS: {e}")
            return False

    def is_healthy(self) -> bool:
        if not self.running:
            return False
        if not any(t.is_alive() for t in self._threads):
            return False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(0.75)
                q = DNSRecord.question("spb-healthcheck.local")
                s.sendto(q.pack(), ("127.0.0.1", self.port))
                # A timeout is acceptable if upstream is unavailable; this check mainly verifies socket send path.
                try:
                    s.recvfrom(512)
                except socket.timeout:
                    pass
            return True
        except Exception:
            return False

    def _serve(self, sock) -> None:
        """Main UDP server loop."""
        while self.running:
            try:
                data, addr = sock.recvfrom(512)
                # Offload to thread pool for non-blocking serving
                self._executor.submit(self._handle_packet, sock, data, addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"DNS serve error on {sock}: {e}")
                continue

    def _handle_packet(self, sock: socket.socket, data: bytes, addr: tuple) -> None:
        """Processes a single DNS packet (runs in executor thread)."""
        try:
            request = DNSRecord.parse(data)
            qname = str(request.q.qname).lower().rstrip(".")
            
            # --- TIERED PRIORITY CHECK ---
            
            # 1. Cloud Allowlist - ABSOLUTE PRIORITY (Always Allowed)
            if self.cloud_matcher.matches(qname):
                forwarded_data = self._forward_query(data)
                if forwarded_data:
                    sock.sendto(forwarded_data, addr)
                return

            # 2. Manual Blocks - HIGHER than filter exceptions
            if self.manual_matcher.matches(qname):
                logger.info(f"[DNS] Blocked (Manual): {qname}")
                self._send_block(sock, request, addr)
                return
            
            # 3. Filter Exceptions - Allows specific keywords/domains within filter lists
            if self.filter_exception_matcher.matches(qname):
                forwarded_data = self._forward_query(data)
                if forwarded_data:
                    sock.sendto(forwarded_data, addr)
                return

            # 4. Content Filters (Adblock/Categories)
            if self.filter_matcher.matches(qname):
                logger.info(f"[DNS] Blocked (Filter): {qname}")
                self._send_block(sock, request, addr)
                return

            # Default: Forward to upstream
            forwarded_data = self._forward_query(data)
            if forwarded_data:
                sock.sendto(forwarded_data, addr)
        except Exception as e:
            logger.error(f"DNS packet processing error for {addr}: {e}")

    def _send_block(self, sock, request, addr):
        reply = request.reply()
        qtype = request.q.qtype
        if qtype == QTYPE.A:
            reply.add_answer(RR(request.q.qname, QTYPE.A, rdata=A("0.0.0.0"), ttl=60))
        elif qtype == QTYPE.AAAA:
            reply.add_answer(RR(request.q.qname, QTYPE.AAAA, rdata=AAAA("::1"), ttl=60))
        sock.sendto(reply.pack(), addr)

    def _forward_query(self, data):
        # Try each upstream until one works
        for upstream in self.upstream_dnss:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.settimeout(1.5)
                    s.sendto(data, (upstream, 53))
                    response, _ = s.recvfrom(512)
                    if response:
                        return response
            except Exception:
                continue
        return None

def detect_system_dns():
    """Detects currently active DNS servers to use as upstream for the proxy."""
    dns_servers = []
    try:
        if os.name == 'nt':
            # Use PowerShell to find current IPv4 DNS servers that AREN'T loopback
            cmd = 'powershell -Command "Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object {$_.ServerAddresses -ne $null -and $_.ServerAddresses -notcontains \'127.0.0.1\'} | Select-Object -ExpandProperty ServerAddresses"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.stdout:
                dns_servers = [s.strip() for s in res.stdout.splitlines() if s.strip()]
        else:
            if os.path.exists('/etc/resolv.conf'):
                with open('/etc/resolv.conf', 'r') as f:
                    for line in f:
                        if line.startswith('nameserver'):
                            ip = line.split()[1].strip()
                            if ip != '127.0.0.1': dns_servers.append(ip)
    except Exception:
        pass
        
    # Filter unique and return, fallback if empty
    dns_servers = list(dict.fromkeys(dns_servers)) 
    return dns_servers if dns_servers else ["8.8.8.8", "1.1.1.1"]

if __name__ == "__main__":
    print(json.dumps(audit_dns_safety(), indent=2))
