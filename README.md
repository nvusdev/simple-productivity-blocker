# Simple Productivity Blocker

Block distracting apps, files, and websites with smart schedules, content filters, and group profiles. Built for focus, designed for simplicity.

Simple Productivity Blocker is a free, open-source Windows application that helps you take back your time. Block websites at the system level (hosts file), terminate distracting applications the moment they open, prevent access to specific files, and enforce content filters across categories like social media, adult content, gambling, piracy, and more. Schedule blocks by day and time, create multiple blocking profiles, and protect your settings with a security challenge.

---

## Features

- **Website Blocking:** Block domains at the system level via the hosts file. Both base domains and `www.` variants are blocked automatically. Blocks survive browser restarts and incognito mode.
- **App Blocking:** Instantly terminates any running process that matches a blocked application name the moment it is detected.
- **File Blocking:** Prevents any application from opening a blocked file by monitoring process command-line arguments and terminating violators immediately.
- **Content Filters:** Quickly enable curated blocklists across 9 categories:
  - Ads, Trackers & Telemetry
  - Malware & Annoyances
  - Social Media & Chat
  - Adult Content (18+) *(encrypted)*
  - Gambling & Betting *(encrypted)*
  - Piracy & Illegal Sites *(encrypted)*
  - Entertainment & Streaming
  - Shopping
  - AI & Tech
- **Exceptions (Allowlist):** Whitelist specific domains within Content Filters — whitelisted domains are never blocked by content filters, but explicit Website blocks always take priority.
- **Scheduling:** Set start/end times and active days per profile. "Enforce All Day" on the Content Filter runs it 24/7 regardless of schedule.
- **Multiple Profiles (Groups):** Create separate blocking profiles (e.g., Work, Study, Personal) that run simultaneously and additively.
- **Security Challenge:** Require typing a randomly generated string before accessing settings — makes the blocker tamper-resistant.
- **Custom Lists:** Add your own blocklist URLs (hosts-format) or local `.txt` files to extend the content filter.
- **Uninstaller:** Gracefully removes all blocks, restores your `hosts` file, flushes DNS, and deletes all application data.

---

## Installation (Windows)

1. Download the latest release `.zip` from the [Releases](https://github.com/nvusdev/simple-productivity-blocker/releases) page.
2. Extract the archive.
3. Run `spb_installer.exe` — it will prompt for Administrator privileges.
4. A desktop shortcut is created automatically. Launch **Simple Productivity Blocker** from your desktop.

> **Administrator privileges are required.** The application modifies the system `hosts` file and manages processes — both of which require elevated access on Windows.

---

## Uninstallation

Run `spb_uninstaller.exe` (located in `C:\Program Files\Simple Productivity Blocker\`).

The uninstaller will:
- Terminate all background SPB processes
- Restore your original `hosts` file
- Flush DNS
- Remove all application files and configuration data
- Remove the desktop shortcut

All blocks are fully lifted upon uninstallation.

---

## Running from Source (Developers)

Requires Python 3.10+.

```bash
git clone https://github.com/nvusdev/simple-productivity-blocker.git
cd simple-productivity-blocker
pip install -r requirements.txt

# Windows — run as Administrator
python main.py
```

---

## Building Executables

```powershell
# Windows (PowerShell, run as Administrator)
.\build.ps1
```

Output is placed in `dist\spb\`. Zip that folder to distribute.

---

## Architecture

| File | Role |
|---|---|
| `main.py` | GUI dashboard built with `customtkinter` |
| `daemon.py` | Background process: reads config, applies hosts-file blocks, runs the process monitor |
| `blockers/app_blocker.py` | Unified `ProcessMonitor` — handles both app and file blocking via process scanning |
| `blockers/website_blocker.py` | Reads/writes the system `hosts` file and flushes DNS |
| `core/config_manager.py` | Thread-safe JSON config load/save |
| `core/scheduler.py` | Evaluates whether a group's schedule is currently active |
| `spb_installer.py` | Installs the application to Program Files and creates a shortcut |
| `spb_uninstaller.py` | Reverses all changes and removes all application data |

---

## Security Notes

- Sensitive blocklist categories (Adult Content, Gambling, Piracy) are stored encrypted in the compiled binary. They cannot be read from plaintext source.
- The application requires Administrator privileges to function. This is by design — it is the only reliable way to modify the `hosts` file and terminate system processes.
- Non-admin users on a machine cannot open the settings UI or change the configuration without the Administrator password, making this effective for parental controls and managed environments.

---

## Disclaimer

This application modifies the system `hosts` file (`C:\Windows\System32\drivers\etc\hosts`). A backup is automatically created at `hosts.backup` before any modifications. The uninstaller restores this backup. Use responsibly.
