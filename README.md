# Simple Productivity Blocker

Block distracting apps, files, and websites with schedules, content filters, and group profiles.

Simple Productivity Blocker is a free, open-source Windows application that helps you manage your time. Block websites at the system level via the hosts file, terminate distracting applications when they open, prevent access to specific files, and enforce content filters across categories like social media, adult content, gambling, and piracy. You can schedule blocks by day and time, create multiple blocking profiles, and protect your settings with a security challenge.

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

## Installation (Windows)

1. Download the latest release `.zip` from the [Releases](https://github.com/nvusdev/simple-productivity-blocker/releases) page.
2. Extract the archive.
3. Run `spb_installer.exe`. It will prompt for Administrator privileges.
4. A desktop shortcut is created automatically. Launch **Simple Productivity Blocker** from your desktop.

> **Administrator privileges are required.** The application modifies the system `hosts` file and manages processes, requiring elevated access on Windows.

## Uninstallation

Run `spb_uninstaller.exe` located in `C:\Program Files\Simple Productivity Blocker\`.

The uninstaller will:
* Terminate all background SPB processes
* Restore your original `hosts` file
* Flush DNS
* Remove all application files and configuration data
* Remove the desktop shortcut

All blocks are fully lifted upon uninstallation.

## Running from Source (Developers)

Requires Python 3.10 or newer.
```bash
git clone [https://github.com/nvusdev/simple-productivity-blocker.git](https://github.com/nvusdev/simple-productivity-blocker.git)
cd simple-productivity-blocker
pip install -r requirements.txt

# Windows: run as Administrator
python main.py
```

## Building Executables

```powershell
# Windows PowerShell: run as Administrator
.\build.ps1
```

Output is placed in `dist\spb\`. Zip that folder to distribute.

## Security Notes

* Sensitive blocklist categories (Adult Content, Gambling, Piracy) are stored encrypted in the compiled binary. They cannot be read from plaintext source.
* The application requires Administrator privileges to function. This is the only reliable way to modify the `hosts` file and terminate system processes.
* Non-admin users on a machine cannot open the settings UI or change the configuration without the Administrator password, making this effective for parental controls and managed environments.

## Disclaimer

This application modifies the system `hosts` file (`C:\Windows\System32\drivers\etc\hosts`). A backup is automatically created at `hosts.backup` before any modifications. The uninstaller restores this backup. Use responsibly.
