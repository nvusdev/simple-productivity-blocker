# Implementation Plan

## Goal
Provide a focused set of bug fixes, optimizations, and reliability improvements for Simple Productivity Blocker, with minimal behavior regressions and clear test steps.

## Key Findings
1. Content filter exceptions are stored at the group top-level, but the defaults place them inside the adblocker block. This is inconsistent and can confuse migration logic.
2. `load_config()` only merges top-level keys and does not deep-merge nested structures, so new adblocker keys can be missing in older configs.
3. Daemon detection in the UI is unreliable on Windows for the non-frozen case, which can spawn duplicate daemons.
4. Hosts file IPv6 entries use "::" which is not the typical loopback address and may be ignored.
5. File and folder path matching in `ProcessMonitor` can produce false positives due to substring matching and path prefix checks.
6. Sensitive list encryption is not actually hiding plaintext domains because the encryption helper is called with plaintext strings in source.
7. Schedule input is not validated; invalid times silently disable blocks.
8. The security challenge screen has no back/return path to the dashboard.
9. Hosts file handling does not use a bounded SPB block, and uninstall relies on a backup that might not exist.
10. Dashboard status layout and the "Add New Group" button alignment are inconsistent with the group editor status bar.

## Proposed Changes

### Bug Fixes (High Priority)
1. **Unify exceptions storage**
   - Store exceptions in `groups[*].adblocker.exceptions`.
   - Update the UI list to read/write from `adblocker.exceptions`.
   - Update the daemon to read exceptions from `adblocker.exceptions`.
   - Add migration: if top-level `exceptions` exists, move it into `adblocker.exceptions` on load.

2. **Deep-merge nested config defaults**
   - Merge nested dicts for `adblocker`, `schedule`, and `security` so new keys are always present.
   - Ensure custom lists and new categories are always initialized.

3. **Fix daemon detection in UI**
   - Use `psutil` to detect running daemon process by executable name or command line on Windows and Linux.
   - Avoid launching a new daemon if one is already running.

4. **Correct IPv6 hosts entries**
   - Use `::1` instead of `::` for IPv6 loopback entries.

5. **Add a back/return action on the security challenge**
   - Provide a clear "Back to Dashboard" button so users can exit without completing the challenge.

### Reliability and Correctness
5. **Harden file/folder matching**
   - Normalize blocked folders to include a trailing separator or use `os.path.commonpath` to avoid prefix collisions.
   - For blocked files, compare normalized absolute paths to each cmdline argument instead of substring checks.
   - Keep a fast path for basename-only app blocks but use normalized sets for comparisons.

6. **Schedule input validation**
   - Validate `HH:MM` format in the UI and show feedback instead of silently disabling.
   - Optionally clamp invalid values back to last known valid value.

7. **Hosts file block markers and preservation**
   - Wrap SPB entries in a single bounded block (e.g., `# SPB BEGIN` / `# SPB END`).
   - Replace only the SPB block to preserve other app entries (Tailscale, Portmaster, etc.).
   - Keep per-line comments minimal (`# SPB`) only if needed for diagnostics.

### Security and Privacy
7. **Keep sensitive lists encrypted while ensuring clean uninstall**
   - Replace `_enc("...")` calls with precomputed encrypted payloads stored as constants.
   - Keep a separate offline script (not shipped) to regenerate encrypted strings.
   - Ensure uninstall removes SPB host entries even if no backup exists.

### Performance
8. **Reduce per-loop overhead**
   - Use sets for blocked apps/files/folders to avoid repeated lowercase conversions in every process iteration.
   - Throttle Explorer window checks separately (e.g., every 2-3 seconds) to reduce COM calls.

### UX / Layout
9. **Align dashboard status bar and actions**
   - Match the dashboard status bar layout with the group editor status bar.
   - Align the "Add New Group" button on the same baseline as the status text.

### Optional Enhancements
10. **Improve custom list parsing**
   - Support Adblock-style lines like `||example.com^` by normalizing to domains.

11. **Graceful hosts recovery**
   - If `hosts.backup` is missing, remove only SPB lines on uninstall instead of failing to restore.

## Implementation Steps

### Phase 1: Config and Exceptions Consistency
1. Update `core/config_manager.py` to deep-merge nested defaults.
2. Add migration: move top-level `exceptions` into `adblocker.exceptions`.
3. Update `main.py` Content Filter tab to read/write exceptions from `adblocker.exceptions`.
4. Update `daemon.py` to read exceptions from `adblocker.exceptions`.

### Phase 2: Daemon Detection and Host Fixes
1. Replace `tasklist` checks in `main.py` with a `psutil`-based daemon check.
2. Update `blockers/website_blocker.py` to write IPv6 entries as `::1`.
3. Update `blockers/website_blocker.py` to use a single SPB block and preserve non-SPB lines.
4. Update `spb_uninstaller.py` to remove the SPB block when no backup exists.

### Phase 3: UI Navigation and Layout
1. Add a "Back to Dashboard" button on the security challenge screen.
2. Align dashboard status bar and "Add New Group" button with the group editor layout.

### Phase 4: Matching and Validation
1. Normalize and validate path matching in `blockers/app_blocker.py`.
2. Add schedule input validation feedback in `main.py`.

### Phase 5: Sensitive List Handling
1. Precompute encrypted lists and replace plaintext `_enc("...")` usage in `daemon.py`.
2. Add a small developer-only helper script or comment block with regeneration steps.

### Phase 6: Optional Improvements
1. Improve custom list parsing in `daemon.py`.
2. Improve uninstaller hosts recovery flow in `spb_uninstaller.py`.

## Testing Plan
- **Manual**
   1. Verify security challenge "Back to Dashboard" returns without changes.
   2. Verify schedule UI: invalid input shows feedback and does not silently disable blocking.
   3. Verify exceptions: add allowlist domain; it should bypass content filter but remain blocked if in explicit websites list.
   4. Verify daemon detection: open app twice; ensure only one daemon instance runs.
   5. Verify hosts entries: inspect `hosts` for `0.0.0.0` and `::1` entries, bounded by SPB markers.
   6. Verify other apps' hosts entries remain intact (e.g., Tailscale, Portmaster).
   7. Verify uninstall removes SPB block even if no backup exists.
   8. Verify folder blocking: blocked folder should close Explorer windows without false positives (e.g., `C:\Games` should not kill `C:\GamesArchive`).
   9. Verify dashboard status bar and "Add New Group" alignment match the editor layout.

- **Regression**
  1. Existing groups with old config should load and auto-migrate without data loss.
  2. Custom list URLs should still resolve and cache.

## Risks / Notes
- Config migration must preserve user data; keep a backup before overwrite.
- Any change to process-kill logic can risk false positives; validate carefully.

## Estimated Effort
- Phase 1-2: ~2-4 hours
- Phase 3: ~1-2 hours
- Phase 4: ~2-3 hours
- Phase 5: ~1-2 hours
- Phase 6 (optional): ~1-2 hours
