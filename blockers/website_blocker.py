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
BLOCK_BEGIN = "# --- SPB Block Begin ---"
BLOCK_END   = "# --- SPB Block End ---"

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

def _strip_spb_entries(lines):
    """Remove both old per-line # SPB comments and new block-marker sections."""
    result = []
    inside_block = False
    for line in lines:
        stripped = line.strip()
        if stripped == BLOCK_BEGIN:
            inside_block = True
            continue
        if stripped == BLOCK_END:
            inside_block = False
            continue
        if inside_block:
            continue
        # Legacy migration: remove old per-line tagged entries
        if stripped.endswith("# SPB") or stripped.endswith("# ProductivityApp"):
            continue
        result.append(line)
    return result

def apply_blocks(websites, block_doh=True):
    try:
        if not os.path.exists(BACKUP_FILE) and os.path.exists(HOSTS_FILE):
            shutil.copy2(HOSTS_FILE, BACKUP_FILE)
            
        with open(HOSTS_FILE, 'r') as f:
            lines = f.readlines()
            
        # Strip all existing SPB entries (new block markers + legacy per-line tags)
        clean_lines = _strip_spb_entries(lines)
        
        if clean_lines and not clean_lines[-1].endswith('\n'):
            clean_lines[-1] += '\n'
        
        # Build the domain set
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

        if final_domains:
            block_lines = [BLOCK_BEGIN + "\n"]
            for domain in sorted(final_domains):
                block_lines.append(f"{REDIRECT_IP} {domain}\n")
                block_lines.append(f":: {domain}\n")
            block_lines.append(BLOCK_END + "\n")
            clean_lines.extend(block_lines)

        with open(HOSTS_FILE, 'w') as f:
            f.writelines(clean_lines)
            
        flush_dns()
            
    except PermissionError:
        print("Permission denied: Cannot write to hosts file.")

def remove_blocks():
    try:
        with open(HOSTS_FILE, 'r') as f:
            lines = f.readlines()
            
        clean_lines = _strip_spb_entries(lines)
        
        with open(HOSTS_FILE, 'w') as f:
            f.writelines(clean_lines)
            
        flush_dns()
    except PermissionError:
        pass
