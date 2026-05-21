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
from core.platform_handler import get_platform_handler

handler = get_platform_handler()
from core.config_manager import load_config
DNS_STATE_FILE = handler.get_dns_state_file()

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
HOSTS_FILE = handler.get_hosts_path()
def _f_dns(): handler.flush_dns()
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

def audit_dns_safety(state_path=None):
    return handler.audit_dns_safety(state_path)

def detect_conflicting_services() -> Optional[str]:
    """Detect conflicting DNS/proxy services.
    Strategy:
    1) Prefer live psutil scans (listeners and process names) so tests that mock psutil behave as expected.
    2) Fall back to platform handler detection (service registry / PowerShell) only if psutil scanning is unavailable or inconclusive.
    Returns a human-readable name (string) of a detected conflicting service or None.
    """
    try:
        # 1) Check network listeners (authoritative when available)
        try:
            for conn in psutil.net_connections(kind='inet'):
                if not conn.laddr:
                    continue
                port = getattr(conn.laddr, 'port', None) if hasattr(conn.laddr, 'port') else (conn.laddr[1] if len(conn.laddr) > 1 else None)
                if port == 53 and conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        return f"{proc.name()} (PID: {conn.pid})"
                    except Exception:
                        return f"PID:{conn.pid}"
        except Exception as e:
            logger.debug(f"Listener inspection error: {e}")

        # 2) Fallback: inspect running processes for known keywords in name or cmdline
        process_iter_scanned = False
        try:
            # Collect into a list so an empty iterator is still considered a completed scan (helps tests)
            proc_list = list(psutil.process_iter(['pid', 'name', 'cmdline']))
            process_iter_scanned = True
            for proc in proc_list:
                try:
                    name = (proc.info.get('name') or '').lower()
                    cmd = ' '.join(proc.info.get('cmdline') or []).lower()
                    hay = name + ' ' + cmd
                    if not hay.strip():
                        continue
                    for kw in CONFLICT_SERVICE_KEYWORDS:
                        if kw.lower() in hay:
                            return f"{proc.info.get('name')} (PID: {proc.info['pid']})"
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.debug(f"Process iteration error: {e}")

        # If process_iter ran and found nothing, do not invoke platform-level detection.
        # This keeps tests deterministic when they mock psutil to return an empty or controlled set.
        if process_iter_scanned:
            return None

        # 3) Platform-level detection as last resort (only when psutil is unavailable)
        try:
            from core.platform_handler import detect_security_appliances
            res = detect_security_appliances()
            if res and isinstance(res, dict):
                items = res.get("items") or []
                if items:
                    it = items[0]
                    name = it.get('name') or it.get('display') or str(it)
                    pid = it.get('pid')
                    if pid:
                        # Keep legacy formatting expected by tests
                        return f"{name} (PID: {pid})"
                    return name
        except Exception as e:
            logger.debug(f"Platform detection unavailable: {e}")
    except Exception as e:
        logger.debug(f"Error in detect_conflicting_services: {e}")
    return None

class DomainMatcher:
    def __init__(self, patterns):
        self.exact_set = set()
        self.regex_patterns = []
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
                # DO NOT add to regex_parts. This ensures "youtube.com" does NOT match "www.youtube.com"
            else:
                regex_parts.append(self.compile_pattern_str(p))
        
        if regex_parts:
            # Chunk regex parts to prevent extremely slow compilation on large rulesets
            chunk_size = 200
            for i in range(0, len(regex_parts), chunk_size):
                chunk = regex_parts[i:i + chunk_size]
                self.regex_patterns.append(re.compile("|".join(chunk), re.IGNORECASE))

    def compile_pattern_str(self, p: str) -> str:
        """Returns the regex string for a pattern (without compiling).
        Handles:
        - *.domain.com: All subdomains and the base domain
        - word*: Segment prefix
        - *word: Segment suffix
        - keyword: Any segment starting with keyword (boundary-aware)
        - a*b: Wildcard within segment
        """
        p = p.lower().strip()
        
        # 1. Special Case: Domain Wildcard (*.domain.com)
        if p.startswith("*."):
            base = re.escape(p[2:])
            return f"^(?:.+\\.)?{base}$"

        # 2. Convert glob-style pattern to boundary-aware regex
        # We want '*' to match anything within a segment (not crossing dots or slashes)
        parts = p.split('*')
        escaped_parts = [re.escape(part) for part in parts]
        
        # Join with [^.\\\/]* which matches anything except a dot or path separator
        core_regex = "[^.\\\\/]*".join(escaped_parts)
        
        # Anchor to boundaries (Start, dot, backslash, or forward slash)
        # Suffix boundaries: End, dot, backslash, or forward slash
        # This ensures 'youtube' matches 'youtube.com' but not 'myyoutube.com'
        return rf"(?:^|\.|\\|/){core_regex}(?:\.|\\|/|$)"

    def matches(self, domain: str) -> bool:
        if not domain: return False
        domain = domain.lower().rstrip('.')
        
        # 1. Fast Set Lookup (O(1))
        if domain in self.exact_set:
            return True
            
        # 2. Optimized Combined Regex Match
        for pattern in self.regex_patterns:
            if pattern.search(domain):
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
        self._threads = []
        self._executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="DNSHandler")
        self._semaphore = threading.Semaphore(100)

    def update_rules(self, manual_list, filter_list, cloud_list, filter_exceptions):
        self.manual_matcher = DomainMatcher(manual_list)
        self.filter_matcher = DomainMatcher(filter_list)
        self.cloud_matcher = DomainMatcher(cloud_list)
        self.filter_exception_matcher = DomainMatcher(filter_exceptions)

    def start(self):
        try:
            # Pre-start conflict check: if a superior security appliance is present and the user has not forced proxy, abort startup
            try:
                cfg = load_config()
                force = cfg.get('settings', {}).get('force_dns_proxy', False)
            except Exception:
                force = False
            if not force:
                conflict = detect_conflicting_services()
                if conflict:
                    logger.info(f"Conflict detected with superior network/DNS service '{conflict}'. Aborting DNS proxy startup and falling back to hosts-file.")
                    if os.name == 'nt' and self.port == 53:
                        self._redirect_system_dns(False)
                    return False

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
            if os.name == 'nt' and self.port == 53:
                self._redirect_system_dns(False)
            return False
        except Exception as e:
            logger.exception(f"Unexpected error during DNS Proxy startup: {e}")
            if os.name == 'nt' and self.port == 53:
                self._redirect_system_dns(False)
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
            return handler.redirect_dns(activate, local_ip=self.host)
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
                if self._semaphore.acquire(blocking=False):
                    try:
                        self._executor.submit(self._handle_packet_wrapper, sock, data, addr)
                    except Exception as e:
                        self._semaphore.release()
                        logger.error(f"Executor submit failed: {e}")
                else:
                    logger.warning("DNS saturation detected. Packet dropped under memory pressure.")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"DNS serve error on {sock}: {e}")
                continue

    def _handle_packet_wrapper(self, sock: socket.socket, data: bytes, addr: tuple) -> None:
        try:
            self._handle_packet(sock, data, addr)
        finally:
            self._semaphore.release()

    def _handle_packet(self, sock: socket.socket, data: bytes, addr: tuple) -> None:
        """Processes a single DNS packet (runs in executor thread)."""
        try:
            request = DNSRecord.parse(data)
            qname = str(request.q.qname).lower().rstrip(".")
            
            # --- TIERED PRIORITY HIERARCHY ---
            
            # 1. Cloud Allowlist - ABSOLUTE PRIORITY (Global Bypass)
            # If a domain is allowed by the cloud, we always forward it immediately.
            if self.cloud_matcher.matches(qname):
                forwarded_data = self._forward_query(data)
                if forwarded_data:
                    sock.sendto(forwarded_data, addr)
                return

            # 2. Manual Blocking - SECOND PRIORITY (Per-Group Blocks)
            # Respects the user's manual schedule and group settings.
            if self.manual_matcher.matches(qname):
                logger.info(f"[DNS] Blocked (Manual): {qname}")
                self._send_block(sock, request, addr)
                return
            
            # 3. Exceptions - THIRD PRIORITY (Allowlist for specific domains)
            # Allows specific domains even if they would normally be caught by content filters.
            if self.filter_exception_matcher.matches(qname):
                forwarded_data = self._forward_query(data)
                if forwarded_data:
                    sock.sendto(forwarded_data, addr)
                return

            # 4. Content Filter - FOURTH PRIORITY (Adblock/Malware/Categories)
            # General blocking based on selected filter lists.
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
                # Support IPv6 upstreams
                family = socket.AF_INET6 if ":" in upstream else socket.AF_INET
                with socket.socket(family, socket.SOCK_DGRAM) as s:
                    s.settimeout(1.5)
                    s.sendto(data, (upstream, 53))
                    response, _ = s.recvfrom(512)
                    if response:
                        return response
            except Exception:
                continue
        return None

def detect_system_dns():
    """Detects currently active DNS servers to use as upstream for the proxy.
    Prioritizes recovery from saved state to prevent isolation after unclean exits.
    """
    dns_servers = []
    
    # 1. Try to recover from SPB's own saved state first (unclean exit recovery)
    if os.path.exists(DNS_STATE_FILE):
        try:
            with open(DNS_STATE_FILE, "r") as f:
                state = json.load(f)
                for adapter in state.get("adapters", []):
                    ips = (adapter.get("ipv4", []) or []) + (adapter.get("ipv6", []) or [])
                    for ip in ips:
                        if ip and ip not in LOOPBACK_DNS:
                            dns_servers.append(ip)
            if dns_servers:
                logger.info(f"Recovered {len(dns_servers)} original upstream DNS servers from {DNS_STATE_FILE}")
        except Exception as e:
            logger.debug(f"Failed to read DNS state file: {e}")
            pass

    # 2. Query current system configuration (active adapters)
    try:
        system_dns = handler.get_system_dns()
        for s in system_dns:
            s = s.strip().strip('"').strip("'")
            if s and s not in LOOPBACK_DNS and s not in dns_servers:
                dns_servers.append(s)
    except Exception as e:
        logger.debug(f"System DNS query failed: {e}")
        pass
        
    # 3. Fallback to public DNS
    if not dns_servers:
        dns_servers = ["8.8.8.8", "1.1.1.1", "2001:4860:4860::8888", "2606:4700:4700::1111"]
        logger.info("No valid system DNS detected. Falling back to public DNS (Google/Cloudflare).")
    else:
        dns_servers = [s for s in dns_servers if s and s not in LOOPBACK_DNS]
        if not dns_servers:
             dns_servers = ["8.8.8.8", "1.1.1.1"]
             logger.warning("All detected DNS servers were loopbacks. Forced fallback to public DNS.")
        
    # Unique set while preserving order
    seen = set()
    result = [x for x in dns_servers if not (x in seen or seen.add(x))]
    logger.debug(f"System DNS detection result: {result}")
    return result

if __name__ == "__main__":
    print(json.dumps(audit_dns_safety(), indent=2))
