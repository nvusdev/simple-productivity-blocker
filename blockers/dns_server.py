import socket
import threading
import re
import time
import subprocess
import os
from dnslib import DNSRecord, QTYPE, RR, A, AAAA, DNSHeader
from blockers.website_blocker import flush_dns

class DomainMatcher:
    def __init__(self, patterns):
        self.patterns = []
        for p in patterns:
            self.patterns.append(self.compile_pattern(p))

    def compile_pattern(self, pattern):
        p = pattern.strip().lower()
        if p.startswith("."): # Handle .domain.com as wildcard
            p = "*" + p
            
        if p.startswith("~"):
            # Keyword / Prefix / Suffix logic
            body = p[1:]
            if body.startswith("*") and body.endswith("*"):
                # Keyword: ~*word*
                regex = re.escape(body[1:-1])
            elif body.startswith("*"):
                # Suffix: ~*alicious -> [^.]*alicious
                regex = r"[^.]*" + re.escape(body[1:]) + r"$"
            elif body.endswith("*"):
                # Prefix: ~crypto* -> crypto[^.]*
                regex = r"^" + re.escape(body[:-1]) + r"[^.]*"
            else:
                # Keyword (phrase anywhere): ~green_eggs -> .*green_eggs.*
                regex = re.escape(body)
            return re.compile(regex)
        elif "*" in p:
            # Wildcard: *.site.com -> ^(.*\.)?site\.com$
            base = p.replace("*.", "").replace("*", "")
            regex = r"^(.*\.)?" + re.escape(base) + r"$"
            return re.compile(regex)
        else:
            # Explicit: site.com -> ^(.*\.)?site\.com$ (includes subdomains for safety)
            regex = r"^(.*\.)?" + re.escape(p) + r"\.?$"
            return re.compile(regex)

    def matches(self, domain):
        if not domain: return False
        domain = domain.lower().rstrip('.')
        for regex in self.patterns:
            if regex.search(domain):
                return True
        return False

class DNSProxyServer:
    def __init__(self, blocklist, allowlist=None, upstream_dns=None):
        self.block_matcher = DomainMatcher(blocklist)
        self.allow_matcher = DomainMatcher(allowlist if allowlist else [])
        # Fallback to standard if no upstreams detected
        self.upstream_dnss = upstream_dns if upstream_dns else ["8.8.8.8", "1.1.1.1"]
        self.port = 53
        self.host = '127.0.0.1'
        self.running = False
        self._sock = None

    def start(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.bind((self.host, self.port))
            self.running = True
            threading.Thread(target=self._serve, daemon=True).start()
            
            # Direct system DNS to local proxy
            if os.name == 'nt':
                self._redirect_system_dns(True)
            
            flush_dns()
            return True
        except Exception as e:
            print(f"DNS Proxy failed to start on port 53: {e}")
            return False

    def stop(self):
        self.running = False
        if os.name == 'nt':
            self._redirect_system_dns(False)
        if self._sock:
            self._sock.close()

    def _redirect_system_dns(self, activate):
        """Forces the system to use our local proxy for all active adapters."""
        try:
            if activate:
                # Set DNS to 127.0.0.1 for all active network adapters
                cmd = 'powershell -Command "Get-NetAdapter | Where-Object {$_.Status -eq \'Up\'} | ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ServerAddresses \'127.0.0.1\' }"'
            else:
                # Reset DNS to DHCP (Automatic)
                cmd = 'powershell -Command "Get-NetAdapter | Where-Object {$_.Status -eq \'Up\'} | ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ResetServerAddresses }"'
            subprocess.run(cmd, shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            print(f"Failed to modify system DNS: {e}")

    def _serve(self):
        while self.running:
            try:
                data, addr = self._sock.recvfrom(512)
                request = DNSRecord.parse(data)
                qname = str(request.q.qname).lower().rstrip(".")
                qtype = request.q.qtype
                
                # Priority: Allowlist bypasses Blocklist
                if self.allow_matcher.matches(qname):
                    forwarded_data = self._forward_query(data)
                    if forwarded_data:
                        self._sock.sendto(forwarded_data, addr)
                    continue

                if self.block_matcher.matches(qname):
                    # Blocked!
                    reply = request.reply()
                    if qtype == QTYPE.A:
                        reply.add_answer(RR(request.q.qname, QTYPE.A, rdata=A("127.0.0.1"), ttl=60))
                    elif qtype == QTYPE.AAAA:
                        reply.add_answer(RR(request.q.qname, QTYPE.AAAA, rdata=AAAA("::1"), ttl=60))
                    self._sock.sendto(reply.pack(), addr)
                else:
                    # Forward to upstream
                    forwarded_data = self._forward_query(data)
                    if forwarded_data:
                        self._sock.sendto(forwarded_data, addr)
            except Exception:
                continue

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

import os
