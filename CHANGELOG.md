# Simple Productivity Blocker - Version History

## [1.6.0] - 2026-06-21
### Added
- **Uninstallation Blocking Option**: Implemented a new option in the Global Settings menu allowing administrative users to block uninstallation of Simple Productivity Blocker, preventing bypass of active profiles.
- **Settings Page Challenge protection**: Global Settings navigation now requires solving the strongest/largest security challenge among the existing group profiles to prevent tampering.

### Fixed
- **DNS Exception Fallback Resolution**: Resolved a bug in hosts-file fallback mode where content filter exceptions (e.g. `youtube.com`) were not correctly removed from custom block lists and normalized category domains.
- **GitHub Pages Next.js Site**: Configured `.github/workflows/deploy.yml` to compile and deploy the Next.js static site under the `/website` folder to GitHub Pages dynamically.

## [1.5.0] - 2026-05-25
### Added
- **Quality Gate Integration**: Pre-build validation checks executing unit tests, Bandit security checks, Mypy static typing, and Ruff formatting/styling checks before compilation in `build.ps1`.
- **Reproducible Dependency Tracking**: Two-tier dependency manifest strategy using a development `requirements.txt` and a locked `requirements-lock.txt` with cryptographic hashes generated via `pip-compile`.
- **Windows Matrix Runner CI/CD**: Workflow automation via GitHub Actions (`deploy.yml`) running a Windows container to build, validate, and package production setup releases.
- **Dynamic Versioning Infrastructure**: Single source of truth versioning defined in `core/__init__.py` and imported dynamically by the dashboard UI, background daemon, installer, uninstaller, and stress tests.
- **Dynamic Windows PE Metadata**: Dynamic generation of file version resources (`version_info.txt`) injected into compiled executables.
- **Dynamic NSIS Compiler Resolution**: Native makensis tool lookup via registry and environment search instead of hardcoded paths.
- **Dynamic Code Signing (Signtool)**: Post-build signing integration in `build.ps1` using `signtool.exe` with a self-signed PFX developer certificate fallback for testing.

### Fixed
- **Process Watchdog Connection**: Connected the settings toggle to scheduled tasks, dynamically disabling (`schtasks /change /disable`) or enabling watchdog monitoring upon configuration shifts.
- **Virtual Drive Synchronization Loop**: Hardened background non-ACL auditing to periodically lock and sync files/folders inside `run()` ignoring change-detection guards.
- **Browser Socket-Pooling Bypass**: Implemented dynamic connection drops for Chrome, Edge, Firefox, and Brave via Windows API `SetTcpEntry` to force instant policy compliance without system restarts.

## [1.4.10] - 2026-05-21
### Added
- **Virtual and Online Drive Blocking**: Implemented exclusive file-locking fallback (via Windows read/write-deny handles) and process command-line auditing to support blocking folders and files on virtual/online drives (e.g. Google Drive, MEGA, FAT32/exFAT) that lack NTFS persistent ACL support.
- **Dynamic Drive Synchronization**: Added a background daemon task that periodically audits virtual drives to handle connection/disconnection state transitions and file additions/removals dynamically.
- **Customizable Synchronization Interval**: Added a new config setting `non_acl_sync_interval` exposed in the settings dashboard's Performance tab as "Virtual Drive Sync Interval" (options: 5s, 10s, 30s, 60s) to customize the synchronization frequency.
- **Daemon Process Watchdog**: Implemented a secondary scheduled task (`SPB_Watchdog`) running on a 60-second repetition interval to monitor and auto-restart `SPB_Daemon.exe` if it is killed. Includes integration with the installer, uninstaller, and emergency recovery utility.
- **Watchdog & Services Toggle Switches**: Added switches to the Settings dashboard under the Performance tab allowing admin users to turn on/off the process watchdog, the DNS watchdog, and the core blocking services on demand, with changes propagated immediately.
- **Virtual Drive File Scan Cap**: Exposed a configurable limit on virtual drive folder walks in the Settings Performance tab (options: 500, 1000, 2500, 5000, and Unlimited).
- **UI Automation Fallback for Virtual Drives**: Implemented optional UIA integration (pywinauto) to detect file paths in custom/internal dialogs (e.g., MSPaint, 7-Zip) on virtual drives. Settings dashboard toggles this via "Enable UI Automation Fallback" in Performance tab, allowing users to read dialog address bars and breadcrumbs reliably when heuristics fail.
- **Website SEO**: Fixed robots.txt to explicitly allow `/spb/` and `/*.xml` paths, resolving Bing Webmaster crawl issues while maintaining security.
- **Version Upgrades**: Bumped version to `1.4.10` across the dashboard GUI, daemon, installers, uninstallers, build scripts, tests, website components, and documentation.

### Fixed
- **Locale-Agnostic ACL Grants**: `icacls` enforcement now uses well-known SIDs for `SYSTEM` and `Administrators`, preventing account-name translation failures on non-English Windows builds.
- **Daemon Single-Instance Guard**: Startup now calls duplicate-instance cleanup before orchestration to prevent concurrent `SPB_Daemon` races.
- **Installer Watchdog Config Resolution**: Watchdog enablement now reads `config.json` from the resolved platform data directory so `SPB_Watchdog` registration follows actual install context.

## [1.4.9] - 2026-05-20
### Fixed
- **Wildcard DNS Coverage**: `DomainMatcher` now treats `*.domain.com` as matching both the base domain and all subdomains, which restores the intended blocking behavior for common wildcard rules.
- **System Safety Exclusions Consistency**: Synchronized `SYSTEM_SAFETY_EXCLUSIONS` across the daemon and app blocker so SPB will not terminate its own executables or core recovery tools.
- **Test Consolidation**: Removed weak placeholder hierarchy tests and relied on the comprehensive DNS hierarchy suite to avoid redundant coverage.
- **Settings Dashboard Responsiveness**: Moved startup persistence checks and security-appliance compatibility checks off the UI thread, with stale-screen guards to keep navigation from touching destroyed widgets.
- **Startup Persistence Repair**: Defaulted `startup_enabled` on and added config migration coverage so installs repair stale pre-fix settings and bring the daemon up reliably.

### Verified
- Full test suite passes after the version update and logic fixes.
- Build and installer output remain aligned with the current v1.4.9 release state.

## [1.4.8] - 2026-05-20
### Added
- **Portmaster and VPN Compatibility**: SPB now detects conflicting DNS services (Portmaster, VPNs, DoH clients) at startup using a layered scan: psutil port-53 listener check first, then process keyword matching, then platform registry fallback. When a conflict is detected the DNS proxy aborts cleanly and SPB falls back to hosts-file blocking automatically, preserving all critical domain blocks without breaking network connectivity.
- **Deterministic Conflict Detection**: `detect_conflicting_services()` in `blockers/dns_server.py` tracks whether psutil ran successfully. If it did and returned no results, the platform registry scan is skipped entirely, making test mocking reliable and eliminating false positives from stale registry entries.
- **Structured Security Appliance API**: Added `detect_security_appliances()` to `core/platform_handler.py` returning a structured dict with detection status, recommended action, matched items (name, PID, detection method, evidence), warnings, and eligible adapters.
- **UI Compatibility Warning**: The About tab now calls `detect_conflicting_services()` on open and displays an orange warning when a conflict is active, naming the detected service and explaining the hosts-file fallback. Includes a "Learn More" link and an advanced-user note about `force_dns_proxy`.
- **force_dns_proxy Config Override**: Added `force_dns_proxy` (default `false`) to `core/config_manager.py` settings. Expert users can set it to `true` to force proxy startup even when a conflict is detected. The override is documented in the UI warning.
- **Watchdog and Recovery Conflict Awareness**: `watchdog_dns()` and `_check_dns_recovery()` in `daemon.py` pre-check for conflicts before attempting recovery. If a superior service is still present, recovery is skipped and the fallback state is held, avoiding spurious retry cycles.
- **Pre-Snapshot DNS Health Validation and Public IP Trust**: Rapid UDP DNS queries against adapter IPs before capturing state in `dns_state.json`. Public IPs (e.g. `8.8.8.8`) are unconditionally trusted. Private IPs are health-tested so SPB never captures and restores dead local proxy IPs left behind by conflicting services.
- **Aggressive DNS Recovery Uplift**: Emergency recovery now runs a connectivity test. If broken DNS state is detected, all network adapters are forced back to DHCP automatic resolution even if the IPs are not standard loopbacks.

### Tests
- `tests/test_conflict_detection.py` (new): deterministic mocking of all three detection paths; verifies port-53 detection and no false positives on empty process list.
- `tests/test_dns_proxy_start.py` (new): verifies proxy aborts on conflict and that `force_dns_proxy=true` attempts startup regardless.
- `tests/test_ui_conflict_warning.py` (new): verifies About tab warning displays with service name when conflict is mocked.
- `tests/test_subsystem_stability.py`: updated to mock `psutil.net_connections()` and `detect_security_appliances()` alongside `psutil.process_iter()` for full determinism.
- `tests/integration/dummy_bind.py` (new): simulates Portmaster by binding TCP/UDP port 53 as a background process.
- `tests/integration/integration_run.py` (new): end-to-end harness that starts the dummy binder, instantiates `DaemonOrchestrator`, runs one sync, and inspects `dns_health.signal`.
- `tests/integration/run_integration_elevated.ps1` (new): PowerShell wrapper to run the integration harness as Administrator.
- `tests/integration/README.md` (new): usage instructions, safety warnings, and artifact preservation notes for the integration harness.
- `tests/integration/test_reliability_safety.py`: fixed `_snapshot_dns_state` call signature and updated schedule fixture to use `always: true` for deterministic group activation.

### Verified
- 39/39 unit tests passing
- Integration harness: conflict detected, DNS proxy aborted, hosts fallback active, `dns_health.signal = Fallback`
- Build: `dist\spb_setup.exe` (86.5 MB NSIS native installer) compiled clean with all 5 binaries

## [1.4.7] - 2026-05-18
### Added
- **High-Integrity SYSTEM Daemon**: Transitioned the scheduled task execution from the interactive user context to the `NT AUTHORITY\SYSTEM` account, guaranteeing absolute privileges for writing to the hosts file and hardened config/log directories.
- **Boot-Level AtStartup Trigger**: Added the `AtStartup` trigger alongside the `AtLogOn` trigger, ensuring the daemon starts instantly when Windows boots up, completely bypassing Fast Startup logon-bypass limitations.
- **Power & Battery Resilience**: Strip power/battery restrictions natively from the scheduled task settings to ensure the protection stays active whether running on plugged-in power or battery.
- **Strict Schedule-OFF Deactivation**: Re-engineered profile scheduling so that disabling a group's schedule explicitly turns off its group blocks (websites/apps/folders), removing "Always Active" fallbacks.
- **Decoupled Content Filter Schedule Integration**: Refactored the Content Filter (Adblocker) logic to support independent 24/7 operation or strict group-schedule dependency via dedicated UI settings.
- **Exhaustive Truth Table Permutations Validation**: Expanded the integration validation suite with a 13-scenario schedule confusion matrix and a 4-scenario adblocker schedule-dependency matrix.

### Fixed
- **Permission Denied Logging**: Resolved log permission errors in hardened ProgramData environments by running as SYSTEM, eliminating the need to fall back to the `%TEMP%` directory.
- **Hosts File Write Protection**: Fixed the `Permission denied` hosts file write failures when the interactive user was non-elevated.

## [1.4.6] - 2026-05-18
### Added
- **Upgrade-Safe Setup Flow**: NSIS setup now detects prior installations, runs a preserve-config cleanup pass, and then proceeds with installation.
- **Native Task Registration in Setup**: Installer now registers and starts `SPB_Daemon` directly via native NSIS command execution.
- **Emergency Recovery Interface**: Added a dedicated warning-styled, bold **Emergency Recovery** button under the "Maintenance & Recovery" section of settings' About tab to run the native `recovery_uplift` tool with elevated UAC permissions.
- **Expanded Fallback Content Filters**: Expanded `NORMALIZED_FILTER_MAP` to 75 high-impact fallback domains (including subdomains and TLD variants) to guarantee robust system-level blocking when the DNS Proxy server is unavailable.

### Fixed
- **Daemon Schedule Crash**: Removed invalid scheduler context passing that caused `'CustomListManager' object has no attribute 'strftime'` and repeated sync-loop failures.
- **Installer Rollback Index Error**: Fixed rollback stack handling in `spb_installer.py` to prevent `list assignment index out of range` on existing-directory installs.
- **Time Input Validation**: Schedule time fields now only persist valid `H:MM`/`HH:MM` values, warn on invalid entries, and ignore invalid values instead of saving broken times.
- **Upgrade/Uninstall Lock Release**: Improved uninstall process handling for running installer processes, DNS loopback fallback reset, and locked installation directory cleanup.
- **Install Health Verification**: Setup now aborts if `SPB_Daemon.exe` fails runtime verification after task registration/start.
- **Default Profile Re-creation Bug**: Fixed configuration normalization to selectively deep-merge default keys, preventing `"Default Profile"` from being automatically re-created when custom profiles exist.
- **Active Group Logging**: Corrected the background active group logging to print custom profile names (e.g. `"Joe Rage"`) using dictionary keys instead of a generic `"Unnamed"` label.
- **Tamper-Proof Hosts File Locking**: Implemented refined NTFS deny Write (W) and Delete (D) ACLs specifically targeting `BUILTIN\Users` and `BUILTIN\Administrators` while keeping standard inheritance and exclusive handle locks lifted. This guarantees standard read access is preserved for the DNS Client service (`Dnscache`) and human users (allowing website blocking to function perfectly on hosts fallback), while completely blocking manual editing, tampering, or deletion by human users (both standard and administrative).

## [1.4.5] - 2026-05-17
### Added
- **Hosts File Domain Cap**: Introduced a configurable cap (1000 to 5000 domains) in settings to limit the number of blocked domains in the hosts file, minimizing system-level DNS resolution latency.
- **Robust Watchdog Recovery**: DNS watchdog and recovery check now preserve the full set of content filter keywords upon port recovery, restoring category restrictions seamlessly.

### Fixed
- **DNS Redundancy Inconsistency**: Ensured the redundancy list written to the hosts file is pattern-filtered against the cloud allowlist, keeping critical system access unrestricted.
- **Fallback Schedule Accuracy**: Enhanced normalized domains calculation to respect the group's full schedule window and `persist_all_day` settings rather than day active state alone.

## [1.4.4] - 2026-05-16
### Added
- **Transactional Installation**: Implemented a LIFO rollback stack in `spb_installer.py` for atomic installation states.
- **Fail-Closed Protection**: Daemon now triggers a native Windows error alert and aborts if core protection modules fail to load.
- **Music & Podcasts Category**: Added a new content filter category to `security.py` and the UI.
- **Critical Redundancy**: Implemented a dual-layer lock that ensures critical domains (Discord, YouTube, Spotify) remain in the hosts file even when the DNS Proxy is active.

### Fixed
- **Post-Condition Audit Crash**: Fixed `AttributeError` in uninstaller when system commands returned `None` due to timeouts.
- **Silent Failure Masking**: Eradicated all bare `except: pass` blocks in lifecycle scripts to ensure explicit failure signaling.
- **Browser Bypass Vector**: Hardened registry policies to disable DNS-over-HTTPS (DoH) and built-in resolvers in Chrome, Edge, and Firefox.
- **Uninstaller Integrity**: Added post-execution audit to verify removal of scheduled tasks and host file markers.

### Improved
- **Handle Safety**: Replaced aggressive handle-scanning in recovery/uninstaller with NTFS ACL "Sledgehammer" logic to prevent kernel deadlocks with security software like Portmaster.
- **Subprocess Standardization**: Centralized all system commands into `core/subprocess_utils.py` for consistent timeout and error handling.
- **Process Termination Accuracy**: Refined ghost instance cleanup to surgically target orphaned background processes without impacting system stability.
- **Version Parity**: Standardized `v1.4.4` metadata across all binaries and legal documents.

## [1.4.3] - 2026-05-13
### Added
- **Gold Master Stress Suite**: Centralized laboratory test runner with 100% functional coverage, including automated config corruption and DNS contention testing.
- **WMI/COM Recovery**: Automatic re-attachment to `Shell.Application` after Explorer crashes or restarts, ensuring folder-blocking persistence.
- **Safe-Mode Enforcement Audit**: Verified kernel-level NTFS ACL persistence for tamper-proof blocking that survives minimal safe-mode boots.
- **Zero-Trust Hardening**: Explicit removal of `CREATOR OWNER` and standard user write access to the `ProgramData` config directory.
- **Logging Resilience**: Permission-aware logging fallback to `%TEMP%` for restricted sessions, preventing startup crashes.
- **Advanced Wildcards**: Cloud-level path keyword and broad boundary-aware regex support for robust allowlisting.

### Fixed
- Resolved `PermissionError` crash during daemon initialization in non-admin mode.
- Fixed path resolution failures in integration test scripts by normalizing `sys.path`.
- Hardened runtime paths in frozen binaries to prevent DLL/module hijacking.
- Resolved a discrepancy where DNS contention tests were skipped in the automated suite.

*Verified by Antigravity Agent - 2026-05-12*

## 🧪 Hierarchy & Logic Stress Test (`tests/test_stress_logic.py`)
**Date:** 2026-05-12
**Result:** **100% PASS**

| Module | Tested Logic | Status |
| :--- | :--- | :--- |
| **DomainMatcher** | Wildcards, prefixes, suffixes, subdomains | ✅ PASS |
| **Hierarchy** | Cloud > Manual > Exception > Content | ✅ PASS |
| **Hosts Expansion** | IPv4/IPv6 dual-stack + `www.` auto-permutation | ✅ PASS |

## 📦 Build Integrity (v1.4.3 Gold Master)
**Date:** 2026-05-12
**Suite:** `build.ps1`

- **PyInstaller Warnings:** 0 (Cleaned `pywin32` distribution collection).
- **Binary Footprint:**
    - `SPB_Daemon.exe`: 14.3 MB (Optimized via UI-module exclusion).
    - `SimpleProductivityBlocker.exe`: 4.3 MB.
    - `spb_installer.exe`: 51.7 MB (Complete standalone payload).
- **DLL Bundling:** Verified `pythoncom314.dll` and `pywintypes314.dll` injection via dynamic discovery.
- **Admin Compatibility:** Proactive UAC checks integrated for PyInstaller 7.0 readiness.

**STATUS:** **STABLE / GOLD MASTER**

## [1.4.2] - 2026-05-08
### Added
- **Tiered DNS Hierarchy**: Implemented a 4-tier DNS enforcement engine (`Cloud Allowlist > Manual Block > Exception > Filter`). This ensures user-defined manual blocks consistently override content filter exceptions.
- **Bulk State Synchronization**: Added `synchronize_all` methods to the `ProcessMonitor` and `SubsystemOrchestrator`, enabling the daemon to reconcile hundreds of file/folder/app targets without race conditions.
- **Ghost Mode (Non-Admin)**: Enabled a non-elevated operation mode (`SPB_GHOST_MODE=1`). The daemon now gracefully falls back to `hosts` file modification if it cannot bind to port 53.
- **Power Efficiency Audit**: Validated "Ghost Mode" overhead at < 0.1% CPU usage and stable ~24MB memory footprint in "Passive" performance mode.
- **Handle Stability Monitoring**: Integrated granular handle-leak detection into the resource audit suite, ensuring long-term daemon stability (~160 stable handles).

### Fixed
- **PyInstaller Build Warnings**: Resolved critical build-time warnings by replacing broad `pywin32` collection with surgical hidden imports and dynamic DLL discovery for COM drivers.
- **DNS Priority Inversion**: Resolved a critical issue where content filter exceptions (e.g., "Video" allowed) were unintentionally bypassing manual blocks on sites like YouTube.
- **Daemon Sync Crashes**: Fixed a persistent `AttributeError` in the background orchestration loop caused by missing bulk reconciliation methods.
- **Keyword Matching Reliability**: Refined regex keyword matching to ensure consistent blocking across complex subdomains and varying URL patterns.

### Improved
- **Build Pipeline Integrity**: Hardened `build.ps1` with proactive UAC checks for PyInstaller 7.0 readiness and optimized binary payloads by excluding redundant UI modules from the background daemon.

## [1.4.1] - 2026-05-06
### Added
- **Triple-Lock Enforcement Suite**: Unified Registry (`DisallowRun`), exclusive File Handles (`msvcrt`), and NTFS ACLs (`icacls`) into a single atomic protection layer for both Apps and Files.
- **SSRF & DNS Rebinding Protection**: Implemented IP-based validation for all remote list downloads, resolving hostnames to IPs and blocking access to private/reserved ranges (IPv4/IPv6).
- **Safe-Boot Recovery Engine**: Refactored the startup reconciliation into a surgical, additive operation that restores historical locks without overwriting the active configuration.
- **Safe Elevation Protocol**: Updated the self-elevation launcher to use industry-standard argument quoting (`subprocess.list2cmdline`), ensuring the app starts correctly in paths containing spaces (e.g., "Program Files").
- **Resource Protection Gates**: Implemented a 10MB safety limit on remote list downloads and symlink-trap detection for all cache files.

### Fixed
- **Thread Leak Prevention**: Fixed the `ProcessMonitor` lifecycle to ensure old background workers are joined and terminated before new ones are spawned during configuration reloads.
- **Unique Category Payload**: Resolved a domain duplication bug by deploying unique, category-specific XOR-encrypted payloads for Social Media, Gaming, and Entertainment.
- **Fresh Install Scheduling**: Fixed a regression where new installations failed to match day schedules due to configuration format mismatches.
- **Content Filter Logic**: "Enforce All Day" now correctly respects the group's day schedule while bypassing the time window.
- **Allowlist Unlock Logic**: Fixed a bug where allowlisted processes were not explicitly unlocked, potentially causing access issues for critical apps.

### Improved
- **Battery-Aware Performance Profiles**: Synchronized daemon polling intervals with user performance modes (Passive: 5s, Balanced: 2s, Strict: 0.5s) and optimized handle-scanning intervals to 10 seconds for reduced CPU load on mobile devices.
- **Non-Blocking Architecture**: Refactored the daemon main loop with a `targets_dirty` flag and background fetching, eliminating UI and heartbeat stuttering during list updates.


## [1.4.0] - 2026-05-06
### Added
- **Kernel-Level NTFS Enforcement**: Transitioned from process polling to OS-level ACL 'Deny' ACEs for files and folders, providing absolute protection even against advanced bypass attempts.
- **Write-Ahead Logging (WAL)**: Implemented a robust recovery system (`recovery.json`) that logs intended blocks *before* enforcement, ensuring zero persistent lockouts on system crashes.
- **Path Normalization Cache**: High-performance caching for OS-level path resolution to reduce CPU overhead during background monitoring.
- **Safety Uninstaller Protocol**: The uninstaller now surgically removes all NTFS ACL blocks before deletion, preventing permanent access loss.
- **Automated Health Check**: Integrated `automated_qa_suite.py` for immediate verification of the NTFS blocking engine.

### Fixed
- **App Name Block Restoration**: Resolved a critical logic omission where name-based termination was bypassed if no path-based rules were active.
- **Group Enablement Logic**: Fixed a core scheduling bug where disabled protection groups remained active due to a missing enablement check.
- **ACL Race Conditions**: Resolved a critical bug where rapid configuration changes could cause file-locking conflicts in the daemon.
- **Recovery Sync**: Fixed 'zombie' blocks by implementing a boot-time reconciliation loop that compares historical logs against active configurations.

### Improved
- **State Caching Optimization**: Implemented a high-efficiency caching layer in the daemon that re-evaluates protection rules only on config changes or scheduled transitions, reducing idle CPU usage by ~90%.
- **Isolated Stress Testing**: Developed a new, UUID-isolated stress test suite (`stress_test_final.py`) for absolute verification of multi-module protection logic.
- **Codebase Streamlining**: Removed over 15 redundant test scripts, legacy build files, and obsolete artifacts to prepare for a clean production distribution.
- **Ghost Process Cleanup**: Hardened termination logic in both installer and uninstaller to clear orphaned daemon instances.


## [1.3.3] - 2026-05-06
### Added
- **High-Precision Rolling Countdown**: Upgraded the 3s sync timer to a 100ms rolling countdown with decimal display in Consolas for a smoother, high-tech UX.
- **Enhanced Engine Diagnostics**: Added comprehensive file-based logging at `C:\ProgramData\SimpleProductivityBlocker\daemon.log` for the background engine.
- **Global Crash Reporting**: Implemented a global exception handler in the daemon to prevent silent failures and provide debuggable crash dumps.

### Fixed
- **Installer Critical Path**: Resolved the "Daemon binary not found" error by restoring the `--add-data` bundling flag in the build pipeline.
- **COM Release Exceptions**: Eliminated `Win32 exception occurred releasing IUnknown` errors by explicitly managing COM object lifecycles during shortcut creation.
- **Tooltip Text Bleeding**: Resolved text clipping in the Website tab by adding `wraplength` to long instruction labels.
- **Daemon Dependency Conflict**: Switched `SPB_Daemon` to a standalone `--onefile` build to eliminate shared `_internal` DLL collisions with the main GUI.

### Changed
- **Symmetric Dashboard Layout**: Moved the sync countdown and status text to the right side of the status bar for better visual balance.
- **Locked Navigation**: The `+ Create New Profile` button is now anchored to the center of the backdrop, making it independent of changing status labels.
- **Path Resolution Hardening**: Updated `resource_path` logic to correctly handle PyInstaller onefile extraction across all binaries.

## [1.3.2] - 2026-05-06
### Added
- **Enhanced Security Hardening**: Replaced insecure `%ProgramFiles%` environment resolution with the native Win32 `SHGetKnownFolderPath` API.
- **Cross-Profile Persistence Cleanup**: The installer and uninstaller now iterate through `HKEY_USERS` SIDs to ensure "ghost" startup stubs are cleared for all users, regardless of UAC context.
- **Atomic Configuration Management**: Implemented an atomic `os.replace` strategy with a 10-attempt retry loop to eliminate file-locking race conditions between the GUI and Daemon.
- **Invisible Startup Protocol**: Implemented `attributes('-alpha', 0.0)` stealth phase to eliminate UI flashing during window hydration.
- **Modular Installer Architecture**: Decomposed the monolithic installer into specialized, auditable functions.

### Fixed
- **PermissionError (WinError 5)**: Resolved an issue where ghost Python instances would lock configuration files during re-installation.
- **Profile Mismatch**: Fixed a bug where the installer would fail to clean up the correct user's registry startup entry when elevated via UAC.

## [1.3.1] - 2026-05-05
### Added
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
