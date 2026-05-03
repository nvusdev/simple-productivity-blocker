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
IPV6_LOOPBACK = "::1"

SPB_BEGIN = "# SPB BEGIN"
SPB_END = "# SPB END"

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

def _strip_spb_block(lines):
    begin_idx = None
    end_idx = None
    for idx, line in enumerate(lines):
        if line.strip() == SPB_BEGIN:
            begin_idx = idx
            break

    if begin_idx is not None:
        for idx in range(begin_idx + 1, len(lines)):
            if lines[idx].strip() == SPB_END:
                end_idx = idx
                break

    if begin_idx is not None and end_idx is not None and end_idx > begin_idx:
        cleaned = lines[:begin_idx] + lines[end_idx + 1:]
    else:
        cleaned = list(lines)

    cleaned = [line for line in cleaned if not line.strip().endswith("# SPB")]
    cleaned = [line for line in cleaned if line.strip() not in (SPB_BEGIN, SPB_END)]
    return cleaned

def apply_blocks(websites, block_doh=True):
    try:
        if not os.path.exists(BACKUP_FILE) and os.path.exists(HOSTS_FILE):
            shutil.copy2(HOSTS_FILE, BACKUP_FILE)
            
        with open(HOSTS_FILE, 'r') as f:
            lines = f.readlines()
            
        # Clean existing blocks
        new_lines = _strip_spb_block(lines)
        
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
        
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
            
        block_lines = [f"{SPB_BEGIN}\n"]
        for domain in sorted(final_domains):
            block_lines.append(f"{REDIRECT_IP} {domain}\n")
            block_lines.append(f"{IPV6_LOOPBACK} {domain}\n")
        block_lines.append(f"{SPB_END}\n")

        new_lines.extend(block_lines)
                
        with open(HOSTS_FILE, 'w') as f:
            f.writelines(new_lines)
            
        flush_dns()
            
    except PermissionError:
        print("Permission denied: Cannot write to hosts file.")

def remove_blocks():
    try:
        with open(HOSTS_FILE, 'r') as f:
            lines = f.readlines()
            
        new_lines = _strip_spb_block(lines)
        
        with open(HOSTS_FILE, 'w') as f:
            f.writelines(new_lines)
            
        flush_dns()
    except PermissionError:
        pass
