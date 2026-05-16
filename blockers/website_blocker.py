import os
import subprocess
import shutil

from core.platform_handler import get_platform_handler

handler = get_platform_handler()
HOSTS_FILE = handler.get_hosts_path()
BACKUP_FILE = handler.get_backup_hosts_path()

if os.name == 'nt':
    import msvcrt
    import winreg
    import logging
    logger = logging.getLogger("SPB_Daemon")
else:
    logger = None

_locked_hosts_handle = None

REDIRECT_IP = "0.0.0.0"
BLOCK_BEGIN = "# --- SPB Block Begin ---"
BLOCK_END   = "# --- SPB Block End ---"

# Common DoH providers to block to prevent bypassing DNS rules
DOH_PROVIDERS = [
    "dns.google", "dns64.dns.google", "8.8.8.8", "8.8.4.4",
    "cloudflare-dns.com", "1.1.1.1", "1.0.0.1",
    "dns.quad9.net", "9.9.9.9",
    "doh.opendns.com", "doh.adguard.com",
    "doh.cleanbrowsing.org", "doh.mullvad.net",
    "dns.nextdns.io", "dns.controld.com",
    "family-filter.cleanbrowsing.org", "dns.google.com",
    "mozilla.cloudflare-dns.com", "firefox.dns.google",
    "dns.alidns.com", "doh.pub", "dot.pub",
    "dns.tuna.tsinghua.edu.cn", "doh.li", "dns.switch.ch"
]

def flush_dns():
    handler.flush_dns()

def expand_keyword_list(websites):
    """Expands dot-less keywords into common domain variations for hosts-file fallback."""
    expanded = []
    # Pruned TLD list for performance
    # Expanded TLD list for better coverage
    COMMON_TLDS = [
        ".com", ".net", ".org", ".io", ".tv", ".me", ".info", ".biz", ".co", 
        ".uk", ".co.uk", ".de", ".ca", ".fr", ".jp", ".ru", ".site", ".online", ".xyz",
        ".app", ".dev", ".studio", ".shop", ".blog", ".news", ".tech", ".be", ".ly"
    ]
    # Expanded subdomains to cover common patterns
    COMMON_SUBDOMAINS = ["", "www."]

    for d in websites:
        d = d.strip().lower()
        if d.startswith("*."):
            d = d[2:]
        d = d.lstrip("*").lstrip(".")
        
        if not d: continue
        
        # Strip legacy keyword prefixes
        if d.startswith("~"):
            d = d[1:]
        
        if "." not in d:
            # Expand keyword to common TLDs and their subdomains
            for tld in COMMON_TLDS:
                base_domain = d + tld
                for sub in COMMON_SUBDOMAINS:
                    expanded.append(sub + base_domain)
        else:
            # For already-dotted domains, ensure common subdomains are covered
            base_d = d
            if d.startswith("www."):
                base_d = d[4:]
            
            for sub in COMMON_SUBDOMAINS:
                if sub: # Avoid adding base twice if sub is empty
                    expanded.append(sub + base_d)
                else:
                    expanded.append(base_d)
    return list(set(expanded))

def _apply_file_lock():
    """Vector 1: Hold an exclusive handle on the hosts file."""
    global _locked_hosts_handle
    if os.name != 'nt' or _locked_hosts_handle: return
    try:
        _locked_hosts_handle = open(HOSTS_FILE, "r")
        # Lock the entire file range (max 32-bit offset) to prevent any modifications
        msvcrt.locking(_locked_hosts_handle.fileno(), msvcrt.LK_NBLCK, 0x7FFFFFFF)
        if logger: logger.info("Hosts file locked (Vector 1)")
    except Exception as e:
        if logger: logger.debug(f"Failed to lock hosts file: {e}")
        if _locked_hosts_handle:
            _locked_hosts_handle.close()
            _locked_hosts_handle = None

def _clear_file_lock():
    global _locked_hosts_handle
    if _locked_hosts_handle:
        try:
            _locked_hosts_handle.close()
        except: pass
        _locked_hosts_handle = None
        if logger: logger.info("Hosts file handle released.")

def _apply_acl_lock(lock=True):
    """Vector 2: NTFS ACL Denial for Everyone."""
    if os.name != 'nt': return
    target = "*S-1-1-0" # Everyone
    try:
        if lock:
            # Deny write/modify to everyone, grant full to System/Admins
            args = ["icacls", HOSTS_FILE, "/inheritance:r", 
                    "/grant:r", "System:(F)", "/grant:r", "Administrators:(F)",
                    "/deny", f"{target}:(W,M)", "/c", "/q"]
        else:
            # 1. Take ownership first to ensure we can reset permissions
            subprocess.run(["takeown", "/f", HOSTS_FILE, "/a"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            # 2. Grant Admins full control
            subprocess.run(["icacls", HOSTS_FILE, "/grant", "Administrators:(F)", "/c", "/q"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            # 3. Restore inheritance and remove Deny
            args = ["icacls", HOSTS_FILE, "/inheritance:e", "/remove:d", target, "/c", "/q"]
        
        res = subprocess.run(args, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if res.returncode == 0:
            if logger: logger.info(f"Hosts ACL {'Locked' if lock else 'Restored'} (Vector 2)")
    except Exception as e:
        if logger: logger.debug(f"ACL error: {e}")

def apply_browser_policies(activate=True):
    """Vector 3: Disable DNS-over-HTTPS (DoH) via Registry/Config for browsers."""
    handler.apply_browser_policies(activate)
    if logger: logger.info(f"Browser DoH Policies {'Enforced' if activate else 'Cleared'} (Vector 3)")

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
        # Pre-execution: Clear existing locks to allow writing
        _clear_file_lock()
        _apply_acl_lock(False)
        
        if not os.path.exists(BACKUP_FILE) and os.path.exists(HOSTS_FILE):
            shutil.copy2(HOSTS_FILE, BACKUP_FILE)
            
        with open(HOSTS_FILE, 'r') as f:
            lines = f.readlines()
            
        # Strip all existing SPB entries (new block markers + legacy per-line tags)
        clean_lines = _strip_spb_entries(lines)
        
        if clean_lines and not clean_lines[-1].endswith('\n'):
            clean_lines[-1] += '\n'
        
        # Build the domain set
        domains_to_block = expand_keyword_list(websites)

        if block_doh:
            domains_to_block.extend(DOH_PROVIDERS)
            
        final_domains = set()
        for domain in domains_to_block:
            d = domain.strip().lower()
            if not d:
                continue 
            
            # Note: Hosts file doesn't support wildcards (*), but we've stripped them 
            # in expand_keyword_list to at least block the base domain.
                
            # Triple-entry: base, www, and ensure both IPv4/IPv6 coverage
            if d.startswith("www."):
                base = d[4:]
                final_domains.add(base)
                final_domains.add(d)
            else:
                final_domains.add(d)
                final_domains.add("www." + d)

        if final_domains:
            block_lines = [BLOCK_BEGIN + "\n"]
            # Sort for consistency
            for domain in sorted(list(final_domains)):
                # Expansion: IPv4 + IPv6 + www (already in set)
                block_lines.append(f"0.0.0.0 {domain}\n")
                block_lines.append(f"::1 {domain}\n")
            block_lines.append(BLOCK_END + "\n")
            clean_lines.extend(block_lines)

        with open(HOSTS_FILE, 'w') as f:
            f.writelines(clean_lines)
            
        # Post-execution: Re-apply Triple-Lock
        if final_domains:
            _apply_file_lock()
            _apply_acl_lock(True)
            if block_doh:
                apply_browser_policies(True)
                
        flush_dns()
            
    except PermissionError:
        if logger: logger.error("Permission denied: Cannot write to hosts file.")
    except Exception as e:
        if logger: logger.exception(f"Unexpected error in apply_blocks: {e}")

def remove_blocks(keep_policies=False):
    try:
        _clear_file_lock()
        _apply_acl_lock(False)
        if not keep_policies:
            apply_browser_policies(False)
        
        if not os.path.exists(HOSTS_FILE): return
        
        with open(HOSTS_FILE, 'r') as f:
            lines = f.readlines()
            
        clean_lines = _strip_spb_entries(lines)
        
        with open(HOSTS_FILE, 'w') as f:
            f.writelines(clean_lines)
            
        flush_dns()
    except Exception as e:
        if logger: logger.debug(f"Error in remove_blocks: {e}")

def sync_website_protection(websites, active=True, using_dns_proxy=False, redundancy_list=None):
    """
    High-level entry point to synchronize website blocking state.
    Handles switching between DNS Proxy and Hosts-file fallback automatically.
    """
    if not active:
        remove_blocks(keep_policies=False)
        return

    if using_dns_proxy:
        # If using DNS proxy, we keep the hosts file clear of bloat,
        # but we MUST ensure critical/redundancy domains are still present
        # to prevent bypass via other proxies or DoH.
        if redundancy_list:
            apply_blocks(redundancy_list, block_doh=True)
        else:
            remove_blocks(keep_policies=True)
        
        # Always enforce browser policies to prevent DoH bypass
        apply_browser_policies(True)
    else:
        # Fallback to full hosts file blocking
        apply_blocks(websites, block_doh=True)
