Integration harness added

Progress:
- Added an automated elevated integration harness under tests/integration:
  - dummy_bind.py: binds TCP/UDP port 53 to simulate Portmaster
  - integration_run.py: creates isolated SPB_DATA_DIR, starts binder, runs DaemonOrchestrator sync, captures dns_health.signal
  - run_integration_elevated.ps1: PowerShell wrapper that elevates and runs the harness
  - README.md: usage and safety notes

Why:
- Allows repeatable, privileged E2E tests that verify detection, DNS proxy abort, and hosts-fallback behavior without manual steps.

Next steps (recommended):
1. Run the harness in an isolated, elevated Windows VM: Open an elevated PowerShell and run tests\integration\run_integration_elevated.ps1. Inspect printed artifact path for dns_health.signal and logs.
2. Stabilize unit tests by ensuring detect_conflicting_services is mockable to avoid psutil race with the binder.
3. (Optional) Add CI runner image with admin VM to gate regressions using this harness.
4. If hosts-file write flows must be fully validated, run the harness on an administrator VM and verify hosts changes and restoration.

Notes:
- The harness uses a temporary SPB_DATA_DIR to avoid touching ProgramData and to collect artifacts.
- Hosts modifications still target the real hosts file and may require elevated runs to succeed. The harness preserves artifacts for manual inspection.
