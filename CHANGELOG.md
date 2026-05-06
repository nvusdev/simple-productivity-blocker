# Simple Productivity Blocker - Version History

## [1.3.3] - 2026-05-06
### Added
- **UI Stability Patch**: Fixed a high-priority `KeyError` in the configuration loader.
- **Project Sanitization**: Deprecated legacy scripts into `/legacy` and updated build dependencies (Pillow).
- **Final Hardening**: Synchronized versioning across all entry points (Installer/Uninstaller/Makefile).

## [1.3.2] - 2026-05-06
### Added
- **Antigravity Protocol (Security Hardening)**: Replaced insecure `%ProgramFiles%` environment resolution with the native Win32 `SHGetKnownFolderPath` API.
- **Cross-Profile Persistence Cleanup**: The installer and uninstaller now iterate through `HKEY_USERS` SIDs to ensure "ghost" startup stubs are cleared for all users, regardless of UAC context.
- **Atomic Configuration Management**: Implemented an atomic `os.replace` strategy with a 10-attempt retry loop to eliminate file-locking race conditions between the GUI and Daemon.
- **Invisible Startup Protocol**: Implemented `attributes('-alpha', 0.0)` stealth phase to eliminate UI flashing during window hydration.
- **Modular Installer Architecture**: Decomposed the monolithic installer into specialized, auditable functions.

### Fixed
- **PermissionError (WinError 5)**: Resolved an issue where ghost Python instances would lock configuration files during re-installation.
- **Profile Mismatch**: Fixed a bug where the installer would fail to clean up the correct user's registry startup entry when elevated via UAC.

## [1.3.1] - 2026-05-05
### Added
- **Linux Readiness**: Created `PlatformHandler` and `Makefile` to support the v1.3.1 Linux development roadmap.
- **Enter-to-Save UX**: The "Rename Profile" dialog now supports the `Enter` key for faster submission.

### Fixed
- **DNS Allowlist Priority**: The DNS Proxy Server now correctly prioritizes the Allowlist (Exceptions) over the Content Filter blocklist.
- **Wildcard Subdomain Matching**: Refined Regex patterns so that `domain.com` and `*.domain.com` both effectively cover the base domain and all subdomains.
- **Anti-Flash Startup**: Implemented the `withdraw/deiconify` pattern to eliminate UI flickering on application launch.

## [1.3.0] - 2026-05-05
### Added
- **Micro DNS Proxy Server**: Integrated a local DNS interceptor on port 53 to support advanced pattern matching and bypass third-party DNS limitations.
- **Advanced Pattern Matching**: Support for wildcards (`*.site.com`), keywords (`~*word*`), prefixes, and suffixes.
- **Gaming & Game Stores Category**: Comprehensive filter for Steam, Epic Games, Riot, and more.
- **XOR-Encrypted Payloads**: High-risk blocklists (Adult, Piracy, Gambling) are now encrypted and compressed within the binary.

### Changed
- **Massive Blocklist Expansion**: Added 300+ new domains across Piracy, Adult, and Anime categories.
- **Native Windows Hardening**: Switched to `msvcrt` for file locking and bundled `pywin32` system DLLs for more robust folder monitoring.

## [1.2.3] - 2026-05-05
### Added
- **Protected Path Keywords**: The Cloud Allowlist now supports path-based keywords. Any process running from a directory containing a protected keyword (e.g., `OneDrive`, `AppData`, `antigravity`) is automatically exempted from all blocking logic.
- **Deep Command-Line Inspection**: Improved the allowlist engine to protect processes based on command-line arguments, ensuring that script-based tools (like Python agents) aren't killed while performing productive tasks.

### Fixed
- **Allowlist Integration Bug**: Resolved a major issue where the background daemon was not receiving allowlist updates from the GUI configuration, rendering the "Cloud Allowlist" ineffective in previous versions.
- **False Positive Termination**: Fixed a logic error where an allowlisted process could still be killed if its arguments contained the name of a blocked app. The allowlist now provides absolute immunity.

## [1.2.2] - 2026-05-04
### Added
- **Protected Environment Support**: Added `antigravity.exe`, `gemini.exe`, `node.exe`, `git.exe`, and common shells to the default Cloud Allowlist to ensure AI agents and developer tools are never accidentally blocked.
- **Improved Process Protection**: Renamed internal process names in the allowlist to match the latest build artifacts (`SimpleProductivityBlocker.exe` and `SPB_Daemon.exe`).

### Fixed
- **Allowlist Priority Bug**: Fixed a logic error in `app_blocker.py` where processes in the Cloud Allowlist could still be terminated if their executable name matched a blocked app. The allowlist now strictly overrides all blocking mechanisms.

## [1.2.1] - 2026-05-04
### Added
- **New Branding**: Replaced the default CustomTkinter logo with a custom application icon (`newlogo.png`).
- **Enhanced Folder Redundancy**: The folder blocker now monitors the Working Directory (CWD) of all running processes. If a process is launched from within a blocked folder (or any of its subfolders), it is immediately terminated.

### Changed
- **UI Scaling**: Increased the default window height to prevent UI elements from being squished on smaller screens or high-DPI displays.
- **Robust Explorer Interception**: Refactored the File Explorer monitoring loop to prevent accidental crashes or stalls when closing multiple windows simultaneously.

### Fixed
- **Folder Blocking Loop**: Resolved an issue where folder enforcement could prematurely stop after terminating a single process.

### Added
- **Directory/Folder Blocking**: Added a new 'Folders' tab allowing users to block entire directories. The daemon now actively uses Windows Shell COM (`win32com.client`) to intercept and close any Windows File Explorer windows attempting to access blocked directories.
- **Uninstaller Packaging**: Created a standalone `spb_uninstaller.exe` that safely removes the scheduled daemon task, restores the Windows hosts file, and deletes program files. It is now automatically packaged in the build process.
- **Tinder Ad Blocking**: Expanded the `ads_trackers` content filter list to aggressively block Tinder and associated telemetry tracking APIs (`tinder.com`, `gotinder.com`, `api.gotinder.com`).

### Changed
- **Silent Background Execution**: Changed `build.ps1` and `build.sh` to compile `daemon.exe` with the `--windowed` flag. This prevents the command prompt window from flashing or remaining open when the daemon starts in the background.
- **Installer Improvements**: The `spb_installer.exe` will now actively search for and terminate any running instances of `daemon.exe` before attempting to copy the new files, preventing Permission/File In Use errors.
- **UI & UX Polish**: 
  - Adjusted the timer element during saves to smoothly hide once the countdown reaches 0 seconds, removing the redundant "Applied!" text to prevent visual clutter next to the "All changes saved ✅" label.
  - Centered the main application window properly on launch using `update_idletasks()`.
- **Content Filter Logic Updates**: Migrated YouTube and its related CDN domains (`youtube.com`, `googlevideo.com`, `ytimg.com`, etc.) from the 'Social Media' category to the 'Entertainment' category to better reflect their actual usage.

### Fixed
- **Host File Persistence Bug**: Fixed an edge case where appending new hosts entries could concatenate with the last line. The host file string builder now strictly enforces a trailing newline.
- **Path Matching Accuracy**: Overhauled the core path matching engine in `app_blocker.py` to use `os.path.normcase` and `os.path.abspath`. This fixes inconsistencies where uppercase vs lowercase directory strings or backslashes vs forward slashes would cause blocks to fail.
