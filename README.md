# Simple Productivity Blocker v1.4.0

A high-performance, kernel-enforced productivity suite for Windows designed to eliminate digital distractions through unbypassable filesystem locks, advanced DNS filtering, and hierarchical scheduling.

Simple Productivity Blocker (SPB) is a professional-grade tool for focus and time management. Unlike standard extensions or application-level blockers, SPB operates at the system level using native Windows security descriptors and a decoupled background engine. It provides absolute protection against distraction by combining NTFS-level access denial with a robust, schedule-aware enforcement daemon.

## 🛡️ The Nuclear Protection Engine

At the core of v1.4.0 is the **Nuclear Protection Engine**, a shift from passive process monitoring to active kernel-level enforcement:

*   **NTFS ACL Hardening**: SPB utilizes native Windows Access Control Lists (ACLs) to apply 'Deny' ACEs (Access Control Entries) to blocked files and folders. This makes blocks invisible to standard user-mode bypasses and resistant to process-suspension tricks.
*   **Write-Ahead Logging (WAL)**: Every protection state is logged to a recovery engine before enforcement. This ensures that even in the event of a system crash or power loss, the blocker can reconcile and restore the system to a safe, unlocked state upon reboot.
*   **Boot-Sweep Reconciliation**: The background daemon performs a full audit of the system security descriptors at every boot, ensuring that no "zombie" blocks persist and that the system state matches your active configuration.

## 🚀 Key Features

*   **Advanced DNS Interception**: Intercepts domain requests on Port 53 with a built-in micro-DNS proxy. Supports wildcards (`*.distraction.com`) and advanced pattern matching (prefixes, suffixes, and keywords).
*   **Absolute App Blocking**: Instantly terminates any process matching a blocked binary name or path, normalized for the Windows environment.
*   **Recursive Folder Shield**: Block entire directories. SPB intercepts File Explorer navigation and prevents any application—from IDEs to games—from accessing or executing files within the protected path.
*   **Curated Content Filters**: One-click protection across 10 categories, including Social Media, Adult Content, Gambling, Entertainment, and Gaming. Sensitive categories are XOR-encrypted within the binary to prevent tampering.
*   **State-Caching Optimization**: The engine utilizes an intelligent caching layer that re-evaluates rules only on configuration changes or scheduled minute transitions, reducing idle CPU overhead by over 90%.
*   **Custom Performance Tiers**:
    *   **Passive**: 5.0s polling for minimal system impact.
    *   **Balanced**: 2.0s polling for standard daily use.
    *   **Strict**: 0.5s polling for high-stakes focus sessions.
*   **Stealth Initialization**: All GUI components utilize alpha-channel stealth loading, eliminating window flicker and ensuring a perfectly positioned reveal for a professional, accessible experience.

## ⚖️ Enforcement Hierarchy

SPB follows a strict logic hierarchy to prevent rule conflicts:

1.  **System Allowlist**: Critical system processes (Windows Update, OneDrive, etc.) are always exempted.
2.  **Scheduling**: Protection only engages during your defined "Active" windows.
3.  **Manual Website Blocks**: Explicit domain blocks take absolute priority.
4.  **Website Exceptions**: Individual domains can be exempted from Category Filters.
5.  **Content Filters**: Broad categories are enforced last to capture remaining distractions.

## 📥 Installation

1.  Download the latest `SimpleProductivityBlocker_v1.4.0.zip` from the [Releases](https://github.com/nvusdev/simple-productivity-blocker/releases) page.
2.  Extract the archive and run `spb_installer.exe` as Administrator.
3.  Launch the application from the desktop shortcut to configure your profiles.

> [!IMPORTANT]
> **Administrator privileges are mandatory.** The application requires elevated access to modify the system `hosts` file, bind to DNS Port 53, and manage NTFS security descriptors.

## 🛠️ Uninstallation

Run `spb_uninstaller.exe` from the installation directory (`C:\Program Files\Simple Productivity Blocker`). The uninstaller will surgically restore all NTFS permissions, reset DNS settings, and flush the system cache before removing application data.

## 🏗️ Architecture

Simple Productivity Blocker utilizes a decoupled, two-part architecture:

1.  **Management Dashboard**: A CustomTkinter-based interface for rule configuration. It operates purely as a state editor, writing to a central, hardened `config.json`.
2.  **Hardened Daemon**: A background service that acts as the authoritative enforcement engine. It monitors configuration state, manages the DNS proxy, and enforces kernel-level filesystem locks.

## 📄 License & Disclaimer

Simple Productivity Blocker is open-source and provided "as is". It modifies critical system files (`hosts`) and security descriptors. While the WAL and Uninstaller protocols are designed for maximum safety, users should use the application responsibly.
