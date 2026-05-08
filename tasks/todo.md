# SPB v1.4.2 Stabilization Todo

- [x] Tiered DNS Hierarchy
    - [x] Modify `blockers/dns_server.py`:
        - [x] Update `DNSProxyServer` constructor to accept `cloud_list` and `filter_exception_list`.
        - [x] Update `update_rules` method.
        - [x] Refactor `_handle_packet` to implement the 4-tier priority:
            1. `cloud_matcher` -> Forward
            2. `manual_matcher` -> Block
            3. `filter_exception_matcher` -> Forward
            4. `filter_matcher` -> Block
    - [x] Modify `daemon.py`:
        - [x] Update `BlockingContext` dataclass.
        - [x] Update `_compute_targets` to populate `filter_exceptions` separately from manual exceptions if needed.
        - [x] Update `SubsystemOrchestrator.sync_dns` to pass the new lists.

- [x] Safety Fallback & Ghost Mode
    - [x] Modify `daemon.py`:
        - [x] Make Admin elevation optional or quieter.
        - [x] Ensure that if DNS Proxy binding fails (e.g. Port 53 taken by Office/PortBlocker), it gracefully shifts to Hosts-file mode.
        - [x] Add a "Ghost Mode" check to skip UAC if requested via environment or settings.

- [x] Verification
    - [x] Run `kluster_code_review_auto` after changes.
    - [x] Manual verification of hierarchy (Manual Block should override Adblock Exception).
