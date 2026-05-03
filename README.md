# Simple Productivity Blocker

Block distracting apps, files, and websites with schedules, content filters, and group profiles.

Simple Productivity Blocker is a free, open-source application that helps you manage your time. Block websites at the system level via the hosts file, terminate distracting applications when they open, prevent access to specific files, and enforce content filters across categories like social media, adult content, gambling, and piracy. You can schedule blocks by day and time, create multiple blocking profiles, and protect your settings with a security challenge.

## Features

* **Website Blocking:** Block domains at the system level via the hosts file. Both base domains and `www.` variants are blocked automatically. Blocks survive browser restarts and incognito mode.
* **App Blocking:** Instantly terminates any running process that matches a blocked application name upon detection.
* **File Blocking:** Prevents applications from opening a blocked file by monitoring process command-line arguments and terminating violators.
* **Content Filters:** Enable curated blocklists across 9 categories: Ads & Trackers, Malware, Social Media, Adult Content (encrypted), Gambling (encrypted), Piracy (encrypted), Entertainment, Shopping, and AI.
* **Exceptions (Allowlist):** Whitelist specific domains within Content Filters. Whitelisted domains are never blocked by content filters, but explicit Website blocks always take priority.
* **Scheduling:** Set start and end times and active days per profile. The "Enforce All Day" option runs the Content Filter continuously.
* **Multiple Profiles:** Create separate blocking profiles like Work, Study, or Personal that run simultaneously.
* **Security Challenge:** Require typing a randomly generated string before accessing settings to make the blocker tamper-resistant.
* **Custom Lists:** Add your own blocklist URLs or local `.txt` files to extend the content filter.
* **Uninstaller:** Removes all blocks, restores your `hosts` file, flushes DNS, and deletes all application data.

## Installation

### Windows

If you downloaded the compiled release package:

1. Extract the `.zip` file.
2. Run `spb_installer.exe`. This will prompt for Administrator privileges.
3. The installer will copy the necessary files to your `C:\Program Files\Simple Productivity Blocker` directory and create a convenient desktop shortcut.

### Linux

If you downloaded the compiled Linux package:

1. Extract the archive.
2. Open a terminal in the extracted folder.
3. Run `sudo ./install.sh`. This will move the binary to `/opt/` and create a desktop entry so it appears in your application menu.

### Running from Source (Developers)

Ensure you have Python 3.8+ installed.

1. Clone the repository:
   ```bash
   git clone https://github.com/nvusdev/simple-productivity-blocker.git
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application (requires Administrator/sudo privileges to write to the `hosts` file):
   ```bash
   # On Windows
   python main.py

   # On Linux
   sudo python main.py
   ```

## Building the Executables

If you wish to compile the application into a standalone folder using PyInstaller, build scripts have been provided.

**Windows:** Run `.\build.ps1` in PowerShell. This will generate `dist\spb` containing the app, daemon, and the installer wizard.

**Linux:** Run `bash build.sh` in your terminal. This will generate the `dist/spb` folder which can be distributed to users alongside `install.sh`.

## Uninstallation

Run `spb_uninstaller.exe` located in `C:\Program Files\Simple Productivity Blocker\` on Windows, or re-run `install.sh --uninstall` on Linux.

The uninstaller will:
* Terminate all background SPB processes
* Restore your original `hosts` file
* Flush DNS
* Remove all application files and configuration data
* Remove the desktop shortcut

All blocks are fully lifted upon uninstallation.

## Architecture

The application is split into two processes that communicate through a shared JSON configuration file.

**`main.py` - Settings UI**

The graphical settings dashboard, built with `customtkinter`. It handles all user interaction: creating and editing group profiles, configuring website, app, and file blocklists, enabling content filter categories, setting schedules, and toggling the security challenge. All changes are debounced and written to the shared config file, which the daemon picks up automatically.

**`daemon.py` - Background Enforcement Process**

A persistent background process that runs with elevated privileges and performs the actual enforcement loop every 5 seconds:

* Reads the shared config and checks each group's schedule using `core/scheduler.py` to determine if it is currently active.
* Aggregates all blocked websites, apps, files, and content filter domains across every active group into unified lists. Multiple active groups stack additively.
* Writes the final domain list to the system `hosts` file via `blockers/website_blocker.py`, pointing all blocked domains to `0.0.0.0`. Both the bare domain and the `www.` variant are written. Exceptions (allowlisted domains) are stripped from the list before writing.
* Polls running processes via `psutil` through `blockers/app_blocker.py` and terminates any process whose executable name matches a blocked app.
* Monitors process command-line arguments via `blockers/file_blocker.py` and terminates any process that was launched with a blocked file path as an argument.
* Fetches and caches remote custom blocklist URLs (24-hour TTL) and parses local `.txt` blocklist files through `CustomListManager`.

**`core/config_manager.py` - Shared Configuration**

Manages reading and writing the `config.json` file stored in the system's shared program data directory (`C:\ProgramData\SimpleProductivityBlocker` on Windows, `~/.config/SimpleProductivityBlocker` on Linux). Uses a threading lock to prevent concurrent write conflicts between the UI and daemon processes. Also handles automatic migration from older single-profile config formats to the current multi-group schema.

**`blockers/`**

* `website_blocker.py`: Writes and removes `hosts` file entries. Handles the `# SPB START` / `# SPB END` block markers to isolate SPB's entries from the rest of the file.
* `app_blocker.py`: Runs a background thread that continuously scans running processes and kills any whose name matches the blocked list.
* `file_blocker.py`: Runs a background thread that scans process command-line arguments and kills any process launched with a blocked file path.

## Security Notes

* Sensitive blocklist categories (Adult Content, Gambling, Piracy) are stored encrypted in the compiled binary. They cannot be read from plaintext source.
* The application requires Administrator privileges to function. This is the only reliable way to modify the `hosts` file and terminate system processes.
* Non-admin users on a machine cannot open the settings UI or change the configuration without the Administrator password, making this effective for parental controls and managed environments.

## Disclaimer

This application modifies the system `hosts` file (`C:\Windows\System32\drivers\etc\hosts`). A backup is automatically created at `hosts.backup` before any modifications. The uninstaller restores this backup. Use responsibly.
