# Simple Productivity Blocker

**Block distracting apps, files, and websites with schedules, content filters, and group profiles.**

Simple Productivity Blocker is a free, open-source application that helps you manage your time. Block websites at the system level via the hosts file, terminate distracting applications when they open, prevent access to specific files, and enforce content filters across categories like social media, adult content, gambling, and piracy. You can schedule blocks by day and time, create multiple blocking profiles, and protect your settings with a security challenge.

---

## 🚀 Features

*   **Website Blocking**: Block domains at the system level via the hosts file. Both base domains and `www.` variants are blocked automatically. Blocks survive browser restarts and incognito mode.
*   **App Blocking**: Instantly terminates any running process that matches a blocked application name upon detection.
*   **File Blocking**: Prevents applications from opening a blocked file by monitoring process command-line arguments and terminating violators.
*   **Folder Blocking**: Block entire directories. Actively intercepts and closes File Explorer tabs navigating to the directory, and terminates any application that attempts to execute files within the path.
*   **Content Filters**: Enable curated blocklists across **10 categories**: Ads & Trackers, Malware, Social Media, Adult Content (encrypted), Gambling (encrypted), Piracy (encrypted), Entertainment, Shopping, AI/Tech, and Gaming & Game Stores.
*   **Exceptions (Allowlist)**: Whitelist specific domains within Content Filters. Whitelisted domains are never blocked by content filters, but explicit Website blocks always take priority.
*   **Scheduling**: Set start and end times and active days per profile. The "Enforce All Day" option runs the Content Filter continuously.
*   **Multiple Profiles**: Create separate blocking profiles like Work, Study, or Personal that run simultaneously.
*   **Security Challenge**: Require typing a randomly generated string before accessing settings to make the blocker tamper-resistant.
*   **Custom Lists**: Add your own blocklist URLs or local `.txt` files to extend the content filter.
*   **Global Settings**: Centralized "Options" menu for application-wide configuration.
*   **Performance Modes**: Toggle between **Passive, Balanced, and Strict** polling rates to optimize CPU usage vs. enforcement speed.
*   **Cloud Allowlist**: Enhanced protection for 30+ critical system and cloud synchronization processes (OneDrive, Dropbox, etc.).
*   **Advanced Notifications**: 10+ toggleable notification events for block attempts, schedule changes, and daemon activity.
*   **Silent Persistence**: The background daemon installs as a silent background task, automatically launching at system logon with elevated privileges without prompts.

---

## 📦 Installation

### Windows
1.  Download the latest release `.zip` from the **Releases** page.
2.  Extract the archive.
3.  Run `spb_installer.exe`. It will prompt for Administrator privileges.
4.  A desktop shortcut is created automatically. Launch **Simple Productivity Blocker** from your desktop.

> [!IMPORTANT]
> **Administrator privileges are required.** The application modifies the system hosts file and manages processes, requiring elevated access on Windows.

### Linux
1.  Download the latest release `.zip` from the **Releases** page.
2.  Extract the archive.
3.  Open a terminal in the extracted directory and run `sudo ./install.sh` (or manually configure the daemon to run as a systemd service).
4.  Launch the application from your desktop environment or terminal.

> [!IMPORTANT]
> **Root privileges are required.** The application modifies `/etc/hosts` and terminates system processes, requiring root access on Linux.

---

## 🗑️ Uninstallation

### Windows
Run `spb_uninstaller.exe` located in `C:\Program Files\Simple Productivity Blocker\`.

### Linux
Run `sudo /opt/SimpleProductivityBlocker/spb_uninstaller` (or the equivalent path depending on your installation method) to remove the application.

**The uninstaller will:**
*   Terminate all background SPB processes.
*   Restore your original hosts file.
*   Flush DNS cache.
*   Remove all application files and configuration data.
*   Remove the desktop shortcut.

*All blocks are fully lifted upon uninstallation.*

---

## 🛠️ Running from Source (Developers)

**Requires Python 3.10 or newer.**

```bash
git clone https://github.com/nvusdev/simple-productivity-blocker.git
cd simple-productivity-blocker
pip install -r requirements.txt
```

### Windows
Run the application as Administrator:
```powershell
python main.py
```

### Linux
Run the application with sudo:
```bash
sudo python3 main.py
```

---

## 🏗️ Building Executables

### Windows
```powershell
# Run as Administrator
.\build.ps1
```

### Linux
```bash
# Run with necessary permissions
./build.sh
```
*Output is placed in `dist/SimpleProductivityBlocker/`. Zip that folder to distribute.*

---

## 📐 Architecture

Simple Productivity Blocker utilizes a decoupled, two-part architecture to ensure stability, performance, and tamper resistance:

1.  **User Interface (`spb`)**: Built with CustomTkinter, this application acts purely as a configuration editor. It reads and writes to a central `config.json` file. It does not enforce blocks directly.
2.  **Background Daemon (`daemon`)**: A headless background process that constantly monitors the `config.json` file for changes using a 3-second debounce mechanism. When changes are detected, it recomputes the active blocking rules and applies them to the system. It handles writing to the system hosts file for website blocks and utilizes `psutil` and OS Shell integrations to actively terminate restricted applications, files, and folders.

The daemon installs itself as a persistent background task (e.g., Windows Scheduled Task) that launches silently at system boot with elevated privileges. Sensitive content blocklists are **XOR-encrypted** within the compiled binaries to prevent trivial circumvention via source code inspection.

---

## 🛡️ Security Notes

*   **Encrypted Payloads**: Sensitive blocklist categories (Adult Content, Gambling, Piracy) are stored encrypted in the compiled binary. They cannot be read from plaintext source.
*   **Privilege Requirement**: The application requires Administrator/Root privileges to function. This is the only reliable way to modify the hosts file and terminate system processes.
*   **Managed Environments**: Non-admin users on a machine cannot open the settings UI or change the configuration without the Administrator password, making this effective for parental controls and managed environments.

---

## ⚖️ Disclaimer
This application modifies the system hosts file (`C:\Windows\System32\drivers\etc\hosts` or `/etc/hosts`). A backup is automatically created at `hosts.backup` before any modifications. The uninstaller restores this backup. Use responsibly.
