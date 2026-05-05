# Simple Productivity Blocker - Version History

## [1.3.0] - 2026-05-05
### Added
- **Micro DNS Proxy Server**: Implemented a local DNS server on `127.0.0.1:53` for proactive website blocking. Supports new regex syntax: wildcards (`*`), keywords (`~word`), and prefix/suffix matches.
- **Proactive App Prevention**: Transitioned from polling-based killing to Windows `DisallowRun` Registry policies. Blocked applications are now prevented from starting by the OS itself.
- **Exclusive File Locking**: Implemented OS-level file locking for blocked files, ensuring they remain unopenable by any process.
- **Portable Configuration**: Added Import/Export functionality for settings. Users can now backup their configuration to encoded `.spb` files and restore them on any machine.
- **Unified Startup Management**: New cross-platform persistence layer using the Windows Registry `Run` key and Linux `.desktop` files.

### Changed
- **Architecture Refactor**: The daemon now operates as a stateful security engine rather than a reactive script.
- **Improved DNS Fallback**: If Port 53 is occupied, the daemon automatically falls back to the legacy `hosts` file method to ensure continuous protection.

### Fixed
- **UI Consistency**: Updated tooltips and descriptions across the app to reflect new v1.3.0 capabilities.

# Simple Productivity Blocker

Block distracting apps, files, and websites with schedules, content filters, and group profiles.

Simple Productivity Blocker is a free, open-source application that helps you manage your time. **v1.3.0** introduces a major shift from reactive polling to proactive prevention using system-integrated security engines.

## Features

* **Website Blocking (DNS Proxy):** [NEW] v1.3.0 uses a local DNS Proxy (127.0.0.1:53) for "invisible" and instant blocking. Supports advanced syntax:
    * **Explicit:** `site.com` (Exact match)
    * **Wildcard:** `*.site.com` (All subdomains)
    * **Keyword:** `~word` (Matches phrase anywhere in domain)
    * **Prefix/Suffix:** `~abc*` or `~*xyz`
* **App Blocking (DisallowRun):** [NEW] Uses Windows Registry policies to prevent restricted applications from even initializing. A secondary polling layer remains for path-based and command-line enforcement.
* **File Blocking (Exclusive Locking):** [NEW] Proactively locks blocked files at the OS level, triggering native "File in use" errors and preventing access by any application.
* **Folder Blocking:** Block entire directories. Actively intercepts and closes File Explorer tabs navigating to the directory, and terminates any application that attempts to execute files within the path.
* **Content Filters:** Enable curated blocklists across 9 categories. v1.3.0 features optimized regex matching for near-zero latency.
* **Exceptions (Allowlist):** Whitelist specific domains within Content Filters.
* **Scheduling:** Set start and end times and active days per profile.
* **Multiple Profiles:** Create separate blocking profiles that run simultaneously.
* **Security Challenge:** Require typing a randomly generated string before accessing settings.
* **Portable Configs:** [NEW] Backup and restore your entire configuration via encoded `.spb` files from the About dashboard.
* **Startup Management:** [NEW] Unified "Start at Login" toggle for Windows (Registry-based) and Linux (.desktop based).
* **Performance Modes:** Toggle between Passive, Balanced, and Strict rates.
* **Cloud Allowlist:** Absolute protection for critical system and developer processes (antigravity, node, git, etc.).

## Installation

### Windows
1. Download the latest release `.zip` from the [Releases](https://github.com/nvusdev/simple-productivity-blocker/releases) page.
2. Extract the archive.
3. Run `spb_installer.exe`.
4. A desktop shortcut is created automatically.

> **Administrator privileges are required.** v1.3.0 requires elevated access to manage Port 53 (DNS), Registry Policies (DisallowRun), and system processes.

### Linux
1. Download the latest release `.zip`.
2. Extract and run `sudo ./install.sh`.
3. The daemon integrates with your desktop environment's Autostart or Systemd.

## Uninstallation

### Windows
Run `spb_uninstaller.exe` located in `C:\Program Files\Simple Productivity Blocker\`.

The uninstaller will:
* Restore system DNS settings
* Clear Registry Blocking policies
* Flush DNS and restore `hosts` backup
* Remove all application files

## Architecture

Simple Productivity Blocker v1.3.0 utilizes a proactive, system-integrated architecture:

1. **User Interface (spb):** A CustomTkinter editor for `config.json`.
2. **Background Daemon (daemon):** A high-performance interceptor that:
    * Runs a **Micro DNS Server** to intercept domain requests.
    * Manages **Windows Registry Policies** for app execution prevention.
    * Maintains **Exclusive File Locks** on restricted resources.
    * Automatically falls back to legacy `hosts` blocking if Port 53 is occupied.

## Security Notes

* Sensitive blocklists (Adult, Gambling, Piracy) are XOR-encrypted within binaries.
* v1.3.0 uses OS-native prevention mechanisms which are significantly harder to bypass than simple process-killing loops.

## Disclaimer

This application modifies system-level network and policy settings. A backup of the `hosts` file is created. Use responsibly.
