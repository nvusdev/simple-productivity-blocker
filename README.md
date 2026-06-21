# Simple Productivity Blocker (SPB)

![Version](https://img.shields.io/badge/version-1.6.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-windows-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-stable-success.svg)

A system-level focus and time management suite for Windows.

Official website: [nvus.dev/spb](https://nvus.dev/spb/)

Simple Productivity Blocker is designed for people who need absolute focus. Browser extensions are too easy to turn off. Basic app blockers can be bypassed or closed. SPB operates directly at the Windows operating system level to ensure that when you decide to lock in and work, your computer enforces that decision.

It combines advanced website filtering, application termination, strict file and folder access controls, profile schedules, network safety checks, and transactional recovery tooling into one clean interface.

## Why use SPB?

* **System-Level Enforcement:** Instead of just asking you to stop scrolling, SPB uses Windows process monitoring, policy controls, file handles, and NTFS ACLs to lock down apps, files, and folders. During a focus session, the operating system itself helps enforce your rules.
* **Smart DNS Interception:** SPB catches website requests before they leave your computer when local DNS interception is safe. You can block specific sites, use wildcard patterns, block keywords, or apply curated filters for categories like Social Media, Gaming, Shopping, and Adult Content.
* **Schedule Your Focus:** Create different profiles for different needs. Each group can have its own schedule, selected days, time window, or all-day enforcement.
* **Crash-Proof Recovery:** SPB logs permission-sensitive changes to recovery history. If your computer loses power, crashes, or a block becomes orphaned, the daemon and recovery tools can reconcile and restore normal access.
* **Network Fail-Safes:** SPB audits adapters before changing DNS, skips risky VPN or security-managed adapters, preserves original DNS state, and falls back to hosts-file blocking when local DNS proxying is unsafe.
* **Battery-Aware Performance:** The background service uses caching and performance profiles (Passive, Balanced, Strict) to control how aggressively it scans for running programs.

## Compatibility with Security Appliances

SPB is designed to coexist with Portmaster, VPNs, corporate DNS clients, and other DNS/security tools. When a service that owns port 53 is detected, SPB automatically yields: the DNS proxy does not start, and all active blocks are applied directly to the Windows hosts file instead. Internet connectivity is preserved. The About tab in the application displays a notice when compatibility mode is active.

The detection is layered:

1. Check for port-53 listeners via psutil (authoritative)
2. Scan running process names for known keywords (Portmaster, Mullvad, VPN, etc.)
3. Query the Windows service registry as a last resort

Advanced users who need to force DNS proxy mode regardless can set `force_dns_proxy: true` in `config.json` under `settings`. This is not recommended unless you understand the risk of two services competing for port 53.

## The Enforcement Engine (Under the Hood)

SPB is built to eliminate the "willpower gap" by removing easy bypasses while keeping recovery paths available. Here is how it secures your focus behind the scenes:

* **The Triple-Lock Suite**: SPB does not just look for running apps and close them. It uses high-security `win32file` exclusive handles to prevent binary execution, alongside native NTFS ACLs (`icacls`) to lock down files and folders.
* **Dual-Layer Lock Redundancy**: SPB prefers a local DNS proxy for flexible pattern matching. Critical domains like YouTube and Discord are mirrored to the Windows `hosts` file automatically, creating a secondary lock that prevents bypass via third-party proxies or DoH.
* **Transactional Lifecycle**: Installer and uninstaller operations use a LIFO rollback stack and post-condition audits. This ensures that the system is never left in a partial or unstable state during maintenance.
* **Atomic Recovery History**: SPB uses a write-ahead logging strategy with `fsync` and atomic file swaps. This guarantees that your recovery history is never corrupted, even during a system crash.
* **SSRF & Path Hardening**: Custom blocklists are validated to reduce unsafe network and local path access. Local lists are restricted to the application configuration area.
* **Encrypted Vulnerability Lists**: Sensitive category lists can be stored in an obfuscated form to make casual tampering harder during a moment of weakness.

## Core Capabilities

### Website and Network Control

* Block specific domains, wildcard patterns, and keyword-style matches.
* Apply pre-built filters for common distractions such as streaming, shopping, ads, gaming, music, and adult content.
* Add exceptions for sites that should remain accessible inside a blocked category.
* Use a read-only DNS safety audit to inspect active adapters, VPN-style services, stale loopback DNS, and stored DNS recovery state.

### Application and File Locking

* Instantly close any program by executable name or file path.
* Block individual files during active focus windows.
* Block entire directories so applications cannot open protected content inside them.
* Prevent Windows File Explorer from opening or viewing blocked folders.
* Automatically release blocks when a group becomes inactive, goes off schedule, or is deleted.

### Profiles, Schedules, and Global Settings

* Create multiple blocking groups for different contexts.
* Give each group its own days, time window, or all-day schedule.
* Keep global safety settings above all groups, including performance mode, cloud allowlist, protected path keywords, startup behavior, and notifications.
* Maintain a cloud and system allowlist so important tools like OneDrive, Git, code editors, and Windows services are not accidentally blocked by broad folder rules.

### Recovery and Safety

* Restore stored DNS state if local DNS proxying fails.
* Fall back to hosts-file blocking when adapter rewriting is unsafe.
* Keep recovery history for ACL-protected files and folders.
* Use `recovery_uplift.exe` as an emergency tool to restore DNS, clean hosts entries, clear browser DNS-over-HTTPS policies, remove the daemon scheduled task, and force-unlock protected paths.

## Installation

Because SPB modifies system permissions and network settings to do its job, it requires Administrator rights.

1. Download the latest release zip file from the Releases page.
2. Extract the downloaded archive to a folder on your computer.
3. Right-click `spb_installer.exe` and select "Run as Administrator".
4. Once installed, use the desktop shortcut to open the dashboard and configure your first profile.
5. Add blocked websites, apps, files, or folders, then configure each group schedule.

## Safe Uninstallation

SPB takes system modifications seriously. If you ever need to remove the software, please use the provided uninstaller rather than deleting files manually.

Run `spb_uninstaller.exe` located in the installation directory, usually:

```text
C:\Program Files\Simple Productivity Blocker
```

The uninstaller stops SPB processes, removes startup persistence, restores stored DNS state, cleans SPB hosts-file entries, releases file and folder ACL blocks, and removes installed files.

If you need emergency recovery without a full uninstall, run:

```text
recovery_uplift.exe
```

This helper is intended for restoring access or connectivity if an install, uninstall, or daemon state becomes broken.

## Troubleshooting & Security

### Antivirus False Positives
Because SPB performs high-integrity system actions (modifying DNS, changing file permissions, and managing background tasks), some Antivirus software (like SentinelOne or Bitdefender) may flag the executables as suspicious. 
* **Recommendation:** If you encounter blocked actions or missing files, add the SPB installation directory (`C:\Program Files\Simple Productivity Blocker`) to your Antivirus allowlist/exclusions.

### Safe Mode Recovery
If you are unable to access your system or network in Normal Mode, SPB is designed to be fully manageable in **Windows Safe Mode**.
1. Boot into Safe Mode (The daemon will not run).
2. Run `recovery_uplift.exe` from the installation folder.
3. Select "Full Restore" to strip all blocks and reset network settings.

## For Developers

SPB is built with Python and uses a decoupled architecture to separate the interface from the enforcement engine.

1. **The Dashboard:** A CustomTkinter interface that edits configuration state, groups, schedules, and global settings.
2. **The Daemon:** A background service that evaluates active groups, manages website protection, monitors processes, applies file and folder enforcement, and performs safety recovery.

To build the project from source, install the required dependencies, then run the PowerShell build script.

```powershell
pip install -r requirements.txt
.\build.ps1
```

When possible, run builds from a non-administrator PowerShell terminal. PyInstaller warns on administrator builds today and may block them in future versions.

The release package is written to:

```text
dist\SimpleProductivityBlocker
```

It contains the dashboard, daemon, installer, uninstaller, recovery helper, changelog, and bundled pywin32 components.

Useful development checks:

```powershell
python -m unittest discover tests
```

Run the stress suite:

```powershell
python tests\stress\run_suite.py
```

Compile-check the main modules:

```powershell
python -m compileall core blockers daemon.py spb_uninstaller.py recovery_uplift.py
```

The DNS stress tests use high ports and should not rewrite system adapter DNS.

## Repository Notes

Generated build output belongs in `dist/` and `build/`, both of which are ignored. Local runtime state such as `config.json`, recovery history, DNS snapshots, logs, coverage reports, PyInstaller specs, scratch files, and local agent indexes should not be committed.

## Legal Documents

This project is released under the following terms:

*   **[License (MIT)](LICENSE)**
*   **[Privacy Policy](PRIVACY_POLICY.md)**
*   **[End User License Agreement (EULA)](EULA.md)**

## Disclaimer

This software modifies Windows security descriptors, scheduled tasks, browser policy keys, DNS settings, and the system hosts file. While SPB includes recovery and safety mechanisms, please use it responsibly, test changes carefully, and maintain backups of critical work.
