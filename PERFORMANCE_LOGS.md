# Simple Productivity Blocker v1.4.3 - Performance & Stability Referral

## 🚀 Performance Benchmarks (Logic Engine)
**Date:** 2026-05-08
**Suite:** `tests/stress/perf_bench.py`

| Metric | Result | Target | Status |
| :--- | :--- | :--- | :--- |
| **Total Rules** | 5,000 | - | - |
| **Total Queries** | 50,000 | - | - |
| **Avg Match Latency** | **1.6579 ms** | < 2.5 ms | ✅ PASS |
| **Total Duration** | 82.89 s | - | - |

## ⚡ Proxy Load & Throughput
**Date:** 2026-05-08
**Suite:** `tests/stress/proxy_load.py`

| Metric | Result | Target | Status |
| :--- | :--- | :--- | :--- |
| **Throughput** | **3,977 qps** | > 1,000 qps | ✅ PASS |
| **Success Rate** | 100% | > 99% | ✅ PASS |
| **Memory Growth** | 0.49 MB | < 10 MB | ✅ PASS |

## 👻 Resource Usage Audit (Ghost Mode)
**Date:** 2026-05-08
**Suite:** `tests/resource_audit.py`

| Mode | CPU Influence | RAM Weight | Handle Count |
| :--- | :--- | :--- | :--- |
| **Idle** | **0.00%** | 23.85 MB | **158** (Stable) |
| **Active Load** | 4.35% | 24.40 MB | 164 (Peak) |

**GHOST MODE COMPLIANCE:** **SUCCESS**

## ⚙️ Stability & Churn
**Date:** 2026-05-08
**Suite:** `tests/stress/config_churn.py`

- **Config Updates:** 739 updates in 10s.
- **Result:** Server survived rapid rule hot-reloading with zero port contention or crashes.

## 🔓 Uplift & Recovery Verification
**Date:** 2026-05-08
**Suite:** `tests/test_uplift_mechanics.py`

- **ACL Unlock:** Verified 100% restoration of file access after group deletion.
- **Uninstaller Safety:** Verified `icacls` reset sequence handles legacy orphaned paths.

---
*Verified by Antigravity Agent - 2026-05-08*

---
*Verified by Antigravity Agent - 2026-05-12*

## 🧪 Hierarchy & Logic Stress Test (`test_stress_logic.py`)
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
