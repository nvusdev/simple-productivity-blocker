import os
import subprocess
import shutil

if os.name == 'nt':
    HOSTS_FILE = r"C:\Windows\System32\drivers\etc\hosts"
    BACKUP_FILE = r"C:\Windows\System32\drivers\etc\hosts.backup"
else:
    HOSTS_FILE = "/etc/hosts"
    BACKUP_FILE = "/etc/hosts.backup"

REDIRECT_IP = "0.0.0.0"

# Common DoH providers to block to prevent bypassing hosts file
DOH_PROVIDERS = [
    "dns.google",
    "cloudflare-dns.com",
    "dns.quad9.net",
    "doh.opendns.com",
    "doh.adguard.com"
]

def flush_dns():
    try:
        if os.name == 'nt':
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            try:
                subprocess.run(["systemd-resolve", "--flush-caches"], capture_output=True)
            except FileNotFoundError:
                try:
                    subprocess.run(["resolvectl", "flush-caches"], capture_output=True)
                except FileNotFoundError:
                    pass
    except Exception:
        pass

def apply_blocks(websites, block_doh=True):
    try:
        if not os.path.exists(BACKUP_FILE) and os.path.exists(HOSTS_FILE):
            shutil.copy2(HOSTS_FILE, BACKUP_FILE)
            
        with open(HOSTS_FILE, 'r') as f:
            lines = f.readlines()
            
        # Clean existing blocks
        new_lines = [line for line in lines if not line.strip().endswith(" # SPB")]
        
        # Add new blocks
        domains_to_block = list(websites)
        if block_doh:
            domains_to_block.extend(DOH_PROVIDERS)
            
        final_domains = set()
        for domain in domains_to_block:
            d = domain.strip().lower()
            if d:
                if d.startswith("www."):
                    base = d[4:]
                    final_domains.add(base)
                    final_domains.add(d)
                else:
                    final_domains.add(d)
                    final_domains.add("www." + d)
            
        for domain in final_domains:
            new_lines.append(f"{REDIRECT_IP} {domain} # SPB\n")
            new_lines.append(f":: {domain} # SPB\n")
                
        with open(HOSTS_FILE, 'w') as f:
            f.writelines(new_lines)
            
        flush_dns()
            
    except PermissionError:
        print("Permission denied: Cannot write to hosts file.")

def remove_blocks():
    try:
        with open(HOSTS_FILE, 'r') as f:
            lines = f.readlines()
            
        new_lines = [line for line in lines if not line.strip().endswith(" # SPB")]
        
        with open(HOSTS_FILE, 'w') as f:
            f.writelines(new_lines)
            
        flush_dns()
    except PermissionError:
        pass
