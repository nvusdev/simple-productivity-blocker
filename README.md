# Simple Productivity Blocker (SPB)

A system-level focus and time management suite for Windows.

Simple Productivity Blocker is designed for people who need absolute focus. Browser extensions are too easy to turn off. Basic app blockers can be bypassed or closed. SPB operates directly at the Windows operating system level to ensure that when you decide to lock in and work, your computer enforces that decision. 

It combines advanced website filtering, application termination, and strict file access controls into one clean interface.

## Why use SPB?

* **System-Level Enforcement:** Instead of just asking you to stop scrolling, SPB uses a "Triple-Lock" suite (Registry + File Handles + NTFS ACLs) to lock down files and folders. During a focus session, the operating system itself denies access to your distractions at the kernel level.
* **Smart DNS Interception:** SPB catches website requests before they leave your computer. You can block specific sites, use wildcards to block entire networks, or apply our curated filters for categories like Social Media, Gaming, and Adult Content.
* **Schedule Your Focus:** Create different profiles for different needs. Set SPB to lock down your gaming folders during work hours or block entertainment websites all day.
* **Crash-Proof Recovery:** SPB logs every permission change to a recovery history. If your computer loses power or crashes, the background service performs a surgical "Safe-Boot" sweep on the next startup to reconcile and restore your normal access.
* **Battery-Aware Performance:** The background service uses intelligent caching and performance profiles (Passive, Balanced, Strict) to minimize CPU wake-ups. On battery mode, the system dynamically adjusts its scanning frequency to save power.

## The Enforcement Engine (Under the Hood)

SPB is built to eliminate the "willpower gap" by removing any easy bypasses. Here is how it secures your focus behind the scenes:

* **The Triple-Lock Suite:** SPB does not just look for running apps and close them. It registers blocked applications with the Windows `DisallowRun` policy, applies exclusive `msvcrt` file handle locks, and modifies NTFS ACLs (`icacls`) to ensure that blocked exes cannot be launched, renamed, or read.
* **Deep Process Scanning:** You cannot bypass a block by simply renaming an executable or moving it to a new folder. SPB scans the full file path, the current working directory, and the command-line arguments of every launched process.
* **Active Window Interception:** If a user tries to circumvent file blocks by manually navigating through Windows File Explorer, SPB detects and instantly terminates any Explorer windows attempting to view restricted directories.
* **Dual-Layer Network Traps:** SPB intercepts network requests using a local DNS proxy, but it also automatically manages your system `hosts` file as a fallback layer. If a request somehow bypasses the proxy, the hosts file catches the traffic and drops it.
* **SSRF & Path Hardening:** For custom blocklists, SPB resolves remote hostnames to IPs and blocks any access to private or reserved network ranges (SSRF protection). Local lists are restricted to the application configuration directory to prevent unauthorized system file access.
* **Encrypted Vulnerability Lists:** For sensitive categories like Adult Content or Gambling, the blocklists are XOR-encrypted directly into the application, preventing users from opening configuration files and deleting domains during a moment of weakness.

## Core Capabilities

### Website and Network Control
* Block specific domains or use keywords to catch related sites.
* Apply pre-built filters for common distractions (Streaming, Shopping, Ads, etc.).
* Add specific exceptions for sites you still need to access within a blocked category.

### Application and File Locking
* Instantly close any program by its name or file path.
* Block entire directories. SPB will stop any application from opening files inside a protected folder.
* Prevent Windows File Explorer from opening or viewing blocked folders.

### Customization and Safety
* Set your "Performance Mode" to control how aggressively the blocker checks for running programs.
* Maintain a "Cloud Allowlist" to ensure critical work applications (like OneDrive, Git, or your code editor) are never accidentally blocked by broad folder rules.

## Installation

Because SPB modifies system permissions and network files to do its job, it requires Administrator rights.

1. Download the latest release zip file from the Releases page.
2. Extract the downloaded archive to a folder on your computer.
3. Right-click `spb_installer.exe` and select "Run as Administrator".
4. Once installed, use the new desktop shortcut to open the dashboard and configure your first profile.

## Safe Uninstallation

SPB takes system modifications seriously. If you ever need to remove the software, please use the provided uninstaller rather than deleting files manually.

Run `spb_uninstaller.exe` located in the installation directory (usually `C:\Program Files\Simple Productivity Blocker`). The uninstaller will safely restore all Windows file permissions, reset your network settings, and clean up background tasks before completely removing the application.

## For Developers

SPB is built with Python and utilizes a decoupled architecture to separate the interface from the enforcement engine.

1. **The Dashboard:** A user interface built with CustomTkinter that edits your configuration state.
2. **The Daemon:** A hardened background service that monitors the system, manages the local DNS proxy, and enforces the rules.

To build the project from source, ensure you have Python installed along with the required dependencies, then run the provided PowerShell build script.

```powershell
pip install -r requirements.txt
.\build.ps1
```


## Disclaimer

This software modifies Windows security descriptors and the system hosts file. While we have built extensive recovery and safety mechanisms into the code, please use this tool responsibly and maintain backups of your critical work.
