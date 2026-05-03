# Simple Productivity Blocker - Version History

## [Unreleased]
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
