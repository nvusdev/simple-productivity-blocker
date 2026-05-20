Integration harness

This directory contains an automated elevated integration harness to test SPB behaviour when another DNS/security appliance binds port 53 (e.g., Portmaster).

Files
- dummy_bind.py: Python script that binds TCP and UDP port 53 on localhost to simulate Portmaster.
- integration_run.py: Orchestrates binder, creates isolated SPB_DATA_DIR, runs DaemonOrchestrator.sync(), and records dns_health.signal.
- run_integration_elevated.ps1: PowerShell wrapper to run the harness as Administrator.

How to run
1. Open an elevated PowerShell prompt on a Windows test VM.
2. Run: powershell -NoProfile -ExecutionPolicy Bypass -File tests\integration\run_integration_elevated.ps1

Notes and safety
- Run only in an isolated test VM. The binder binds port 53 locally and can disrupt DNS if the system uses 127.0.0.1 for DNS.
- The harness sets SPB_DATA_DIR to a temporary directory to avoid touching ProgramData. Hosts file writes will still target the real hosts file and may require Administrator privileges.
- Artifacts (logs and dns_health.signal) are preserved in the temp directory printed at the end of the run.

Next steps
- Optionally add CI gating on a privileged test runner VM to execute this harness.
- Add cleanup verification to restore hosts file when testing hosts-write flows.
