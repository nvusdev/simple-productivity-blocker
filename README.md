# Simple Productivity Blocker

Block distracting apps and websites with daily limits and simple schedules, delay opening, interrupt scrolling, block apps and websites, reduce screen time. 

Simple Productivity Blocker is a free app that helps you reduce your screen time by pausing, interrupting, or locking your distracting websites and apps. You can customize your settings by app, day, and time to encourage you to stay focused. Stay focused on work by restricting the amount of time you spend on time-wasting websites. Take control of time-consuming websites by blocking them completely, set daily time limits for specific sites, and customize your blocklist and time allowances to match your productivity goals.

## Features

- **Website & App Blocking:** Completely block specific URLs, desktop applications, or specific files.
- **Aggregated Content Filters:** Quickly toggle blocks for categories like Ads, Trackers, Social Media, Adult Content, Gambling, Piracy, and more using an extensive built-in dictionary.
- **Complex Scheduling:** Set specific start and end times for blocking across different days of the week.
- **"Enforce All Day" Mode:** Need total lockdown? Bypass the schedule and enforce blocks 24/7.
- **Security Check:** Prevents easily disabling the blocker by requiring you to type a randomly generated string before accessing the dashboard.
- **Multiple Profiles (Groups):** Create multiple profiles with different configurations.
- **Cross-Platform:** Works natively on both Windows and Linux environments.

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
   git clone https://github.com/yourusername/simple-productivity-blocker.git
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

If you wish to compile the application into a standalone folder using `PyInstaller`, build scripts have been provided.

**Windows:**
Run `.\build.ps1` in PowerShell. This will generate `dist\spb` containing the app, daemon, and the installer wizard.

**Linux:**
Run `bash build.sh` in your terminal. This will generate the `dist/spb` folder which can be distributed to users alongside `install.sh`.

## Architecture
- **main.py:** The UI dashboard built using `customtkinter`. It configures the rules and settings.
- **daemon.py:** The background process that monitors active windows (`psutil`) and alters DNS resolution (`/etc/hosts`) based on the active schedule. It runs with elevated privileges to ensure system integrity.

## Disclaimer
This application modifies the system `hosts` file to block internet traffic. A `hosts.backup` is automatically created. Ensure you run this application responsibly.
