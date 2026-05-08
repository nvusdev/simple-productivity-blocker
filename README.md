# Simple Productivity Blocker (SPB)

A system-level focus and time management suite for Windows.

Simple Productivity Blocker is built for people who need their computer to enforce a focus decision after they make it. Browser extensions can be disabled, ordinary app blockers can be closed, and hosts-file edits alone are easy to bypass. SPB combines website blocking, app termination, file and folder access controls, profile schedules, and recovery tooling into one desktop application.

SPB modifies operating system settings by design. It should be used carefully, tested on your own machine before wider use, and removed only through the provided recovery or uninstall tools.

## Current capabilities

* **profile-based blocking:** create multiple groups of blocked websites, apps, files, and folders.
* **per-group schedules:** each group can run all the time, only on selected days, inside a time window, or all day on selected days.
* **website and dns blocking:** block domains, keywords, wildcard patterns, and curated content categories.
* **app blocking:** terminate blocked processes by executable name or path.
* **file and folder blocking:** apply file handles and NTFS ACL rules so protected files or folders cannot be opened during an active block.
* **folder navigation control:** close File Explorer windows that try to browse into blocked folders.
* **global safety settings:** keep cloud sync tools, developer tools, and critical system processes protected from broad blocks.
* **network fail-safes:** audit adapters, skip risky dns rewrites, preserve original dns state, and fall back to hosts-file blocking when local dns interception is unsafe.
* **recovery tooling:** restore file permissions, hosts entries, dns settings, browser dns-over-https policies, and scheduled task state.

## How enforcement works

SPB has two main pieces:

1. **dashboard:** the CustomTkinter interface that edits profiles, schedules, global settings, and safety options.
2. **daemon:** the background protection engine that reads the saved configuration and enforces active blocks.

The daemon evaluates every group independently. A group only contributes websites, apps, files, folders, and adblock categories when that group is enabled and its schedule is active. Global settings sit above the groups and control safety behavior such as performance mode, cloud allowlisting, cloud path keywords, startup behavior, and notifications.

For local app and file protection, SPB combines process scanning, Windows policy entries, file locks, and NTFS ACL changes. For websites, SPB prefers a local dns proxy when the network environment is safe, then falls back to managed hosts-file entries when dns interception is unavailable or unsafe.

## Network safety model

SPB is intentionally conservative around network changes.

Before redirecting system dns, the daemon captures adapter state in `dns_state.json`. It skips adapters that already have explicit dns servers, look like VPN or security adapters, or belong to tools such as Tailscale, Portmaster, ProtonVPN, WireGuard, Wintun, Zscaler, GlobalProtect, AdGuard, or NextDNS. If no adapter is safe to rewrite, SPB uses hosts-file protection instead of forcing dns changes.

The dns proxy also has a watchdog. If the proxy becomes unhealthy, SPB restores stored adapter dns state and switches to hosts-file fallback.

You can run a read-only audit from source:

```powershell
python blockers\dns_server.py
```

The audit reports active adapters, skipped adapters, stale loopback dns, stored dns state, and known VPN or dns security services. It does not change adapter settings.

## Installation

SPB is currently built for Windows.

1. Download the latest release zip.
2. Extract the archive.
3. Right-click `spb_installer.exe` and choose `run as administrator`.
4. Open the installed dashboard from the desktop shortcut.
5. Create one or more groups, configure their schedules, and add the websites, apps, files, or folders you want blocked.

Administrator rights are required because SPB manages Windows permissions, scheduled tasks, browser policy keys, dns settings, and the hosts file.

## Recovery and uninstall

Use the provided tools instead of deleting installed files manually.

`spb_uninstaller.exe` performs a full uninstall. It stops SPB processes, removes startup persistence, restores stored dns state, cleans SPB hosts-file entries, releases ACL blocks, and removes installed files.

`recovery_uplift.exe` is the emergency recovery helper. Use it when you need to restore access or connectivity without doing a full uninstall, or when an install state is broken. It can restore stored adapter dns, clear browser dns-over-https policies, remove the daemon scheduled task, clean hosts entries, unlock paths from recovery history, and manually force-unlock a path you enter.

## Build from source

Install Python dependencies first:

```powershell
pip install -r requirements.txt
```

Run the build script from a non-administrator PowerShell terminal when possible:

```powershell
.\build.ps1
```

The build output is written to:

```text
dist\SimpleProductivityBlocker
```

The packaged folder contains the dashboard executable, daemon executable, installer, uninstaller, emergency recovery helper, changelog, and bundled pywin32 components.

## Development checks

Run the unit tests:

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

The dns stress tests use high ports and should not rewrite system adapter dns.

## Repository notes

Generated build output belongs in `dist/` and `build/`, both of which are ignored. Local state such as `config.json`, recovery history, dns snapshots, logs, coverage reports, PyInstaller specs, local agent indexes, and scratch diagnostics should not be committed.

The release package should be made from `dist\SimpleProductivityBlocker` after a clean build.

## Disclaimer

SPB modifies Windows security descriptors, scheduled tasks, browser policy keys, dns settings, and the system hosts file. The project includes recovery mechanisms, but you should still keep backups of important work and test carefully before relying on strict blocking rules.
