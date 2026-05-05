# Simple Productivity Blocker

Block distracting apps, files, and websites with schedules, content filters, and group profiles.

Simple Productivity Blocker is a free, open-source application that helps you manage your time. Block websites at the system level via the hosts file, terminate distracting applications when they open, prevent access to specific files, and enforce content filters across categories like social media, adult content, gambling, and piracy. You can schedule blocks by day and time, create multiple blocking profiles, and protect your settings with a security challenge.

## Features

* **Website Blocking:** Block domains at the system level via the hosts file and a local DNS interceptor. Supports **absolute domains**, **wildcards** (`*.site.com`), and **advanced pattern matching** (prefixes `~pre*`, suffixes `~*suf`, and keywords `~*key*`). Blocks survive browser restarts and incognito mode.
* **Micro DNS Server:** Includes a built-in, lightweight DNS proxy that transparently intercepts requests on port 53. It is cross-compatible with external firewalls (like **Portmaster**), third-party DNS services (like **1.1.1.1** or **NextDNS**), and corporate network settings.
* **App Blocking:** Instantly terminates any running process that matches a blocked application name upon detection.
* **File Blocking:** Prevents applications from opening a blocked file by monitoring process command-line arguments and terminating violators.
* **Folder Blocking:** Block entire directories. Actively intercepts and closes File Explorer tabs navigating to the directory, and terminates any application that attempts to execute files within the path.
* **Content Filters:** Enable curated blocklists across **10 categories**: Ads & Trackers, Malware, Social Media, Adult Content (encrypted), Gambling (encrypted), Piracy (encrypted), Entertainment, Shopping, AI/Tech, and **Gaming & Game Stores**.
* **Exceptions (Allowlist):** Whitelist specific domains within Content Filters. Whitelisted domains are never blocked by content filters, but explicit Website blocks always take priority.
* **Scheduling:** Set start and end times and active days per profile. The "Enforce All Day" option runs the Content Filter continuously.
* **Multiple Profiles:** Create separate blocking profiles like Work, Study, or Personal that run simultaneously.
* **Security Challenge:** Require typing a randomly generated string before accessing settings to make the blocker tamper-resistant.
* **Custom Lists:** Add your own blocklist URLs or local `.txt` files to extend the content filter.
* **Global Settings:** Centralized "Options" menu for application-wide configuration.
* **Performance Modes:** Toggle between Passive, Balanced, and Strict polling rates to optimize CPU usage vs. enforcement speed.
* **Cloud Allowlist:** Enhanced protection for 30+ critical system and cloud synchronization processes (OneDrive, Dropbox, etc.).
* **Advanced Notifications:** 10+ toggleable notification events for block attempts, schedule changes, and daemon activity.
* **Silent Persistence:** The background daemon installs as a silent background task, automatically launching at system logon with elevated privileges without prompts.

## Installation

### Windows
1. Download the latest release `.zip` from the [Releases](https://github.com/nvusdev/simple-productivity-blocker/releases) page.
2. Extract the archive.
3. Run `spb_installer.exe`. It will prompt for Administrator privileges.
4. A desktop shortcut is created automatically. Launch **Simple Productivity Blocker** from your desktop.

> **Administrator privileges are required.** The application modifies the system `hosts` file, redirects DNS to a local proxy, and manages processes, requiring elevated access on Windows.

### Linux
1. Download the latest release `.zip` from the [Releases](https://github.com/nvusdev/simple-productivity-blocker/releases) page.
2. Extract the archive.
3. Open a terminal in the extracted directory and run `sudo ./install.sh` (or manually configure the daemon to run as a systemd service).
4. Launch the application from your desktop environment or terminal.

> **Root privileges are required.** The application modifies `/etc/hosts` and terminates system processes, requiring root access on Linux.

## Uninstallation

### Windows
Run `spb_uninstaller.exe` located in `C:\Program Files\Simple Productivity Blocker\`.

### Linux
Run `sudo /opt/SimpleProductivityBlocker/spb_uninstaller` (or the equivalent path depending on your installation method) to remove the application.

The uninstaller will:
* Terminate all background SPB processes
* Restore your original `hosts` file and system DNS settings
* Flush DNS cache
* Remove all application files and configuration data
* Remove the desktop shortcut

All blocks are fully lifted upon uninstallation.

## Running from Source (Developers)

Requires Python 3.10 or newer.

```bash
git clone https://github.com/nvusdev/simple-productivity-blocker.git
cd simple-productivity-blocker
pip install -r requirements.txt
