import os
import logging
import socket
import threading
import re
import time
import subprocess
import psutil
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Set, Any, Dict
from dnslib import DNSRecord, QTYPE, RR, A, AAAA, DNSHeader

logger = logging.getLogger("SPB_Daemon")

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

class DomainMatcher:
    def __init__(self, patterns):
        self.exact_set = set()
        self.regex_pattern = None
        regex_parts = []
        
        for p in patterns:
            p = p.strip().lower()
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
        """Returns the regex string for a pattern (without compiling)."""
        # 1. Wildcard Domain (*.domain.com)
        if p.startswith("*."):
            base = re.escape(p[2:])
            return f"(?:^|.*\\.){base}$"

        # 2. Prefix match (word*)
        if p.endswith("*") and not p.startswith("*"):
            prefix = re.escape(p[:-1])
            return f"^{prefix}.*"

        # 3. Suffix match (*word)
        if p.startswith("*") and not p.endswith("*"):
            suffix = re.escape(p[1:])
            return f".*{suffix}$"

        # 4. Explicit Wildcard anywhere else (a*b)
        if "*" in p:
            return f"^{re.escape(p).replace(r'\*', '.*')}$"

        # 5. Keyword (no dots) -> Boundary-aware Substring match
        if "." not in p:
            # Matches keyword as a full label OR as a prefix of a label
            # e.g., 'youtube' matches 'youtube.com' and 'www.youtube.com' and 'music.youtube.com'
            return f"(?:^|\\.){re.escape(p)}[^.]*(?:\\.|$)"

        # 6. Absolute domain match (matches domain and all its subdomains)
        safe = re.escape(p)
        return f"(?:^|.*\\.){safe}$"

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
    def __init__(self, manual_list, filter_list, cloud_list=None, filter_exceptions=None, upstream_dns=None, port=53):
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
            threading.Thread(target=self._serve, args=(self._sock,), daemon=True, name="DNS4ServeLoop").start()
            if self._sock6:
                threading.Thread(target=self._serve, args=(self._sock6,), daemon=True, name="DNS6ServeLoop").start()
            
            # Direct system DNS to local proxy
            if os.name == 'nt':
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
        if os.name == 'nt':
            self._redirect_system_dns(False)
        for s in [self._sock, self._sock6]:
            if s:
                try: s.close()
                except: pass

    def _redirect_system_dns(self, activate):
        """Forces the system to use our local proxy for all active adapters."""
        try:
            if activate:
                # Set DNS to 127.0.0.1 (IPv4) and ::1 (IPv6) for all active network adapters
                # This prevents bypass via IPv6 DNS priority in Windows
                cmd = 'powershell -Command "Get-NetAdapter | Where-Object {$_.Status -eq \'Up\'} | ForEach-Object { ' \
                      'Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ServerAddresses (\'127.0.0.1\', \'::1\') }"'
            else:
                # Reset DNS to DHCP (Automatic)
                cmd = 'powershell -Command "Get-NetAdapter | Where-Object {$_.Status -eq \'Up\'} | ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ResetServerAddresses }"'
            
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.returncode != 0:
                logger.error(f"PowerShell DNS Error: {res.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to modify system DNS: {e}")
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

