import socket
import threading
import re
import time
from dnslib import DNSRecord, QTYPE, RR, A, DNSHeader

class DomainMatcher:
    def __init__(self, patterns):
        self.patterns = []
        for p in patterns:
            self.patterns.append(self.compile_pattern(p))

    def compile_pattern(self, pattern):
        p = pattern.strip().lower()
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
            # Wildcard: *.site.com -> .*\.site\.com$
            regex = p.replace(".", "\\.").replace("*", ".*") + "$"
            return re.compile(regex)
        else:
            # Explicit: site.com -> ^site\.com$ (and handle trailing dot)
            regex = r"^" + re.escape(p) + r"\.?$"
            return re.compile(regex)

    def matches(self, domain):
        domain = domain.lower().rstrip('.')
        for regex in self.patterns:
            if regex.search(domain):
                return True
        return False

class DNSProxyServer:
    def __init__(self, blocklist, upstream_dns="8.8.8.8"):
        self.matcher = DomainMatcher(blocklist)
        self.upstream_dns = upstream_dns
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
            return True
        except Exception as e:
            print(f"DNS Proxy failed to start on port 53: {e}")
            return False

    def stop(self):
        self.running = False
        if self._sock:
            self._sock.close()

    def _serve(self):
        while self.running:
            try:
                data, addr = self._sock.recvfrom(512)
                request = DNSRecord.parse(data)
                qname = str(request.q.qname).lower()
                
                if self.matcher.matches(qname):
                    # Blocked!
                    reply = request.reply()
                    reply.add_answer(RR(request.q.qname, QTYPE.A, rdata=A("127.0.0.1"), ttl=60))
                    self._sock.sendto(reply.pack(), addr)
                else:
                    # Forward to upstream
                    forwarded_data = self._forward_query(data)
                    if forwarded_data:
                        self._sock.sendto(forwarded_data, addr)
            except Exception:
                continue

    def _forward_query(self, data):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(2.0)
                s.sendto(data, (self.upstream_dns, 53))
                response, _ = s.recvfrom(512)
                return response
        except Exception:
            return None

def detect_system_dns():
    # Simple detection for Windows/Linux
    if os.name == 'nt':
        # Use a common one if we can't detect easily, or use netsh
        return "8.8.8.8" 
    else:
        try:
            with open('/etc/resolv.conf', 'r') as f:
                for line in f:
                    if line.startswith('nameserver'):
                        return line.split()[1]
        except:
            pass
    return "8.8.8.8"

import os
