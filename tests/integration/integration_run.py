"""Integration runner for elevated end-to-end tests.

- Starts dummy binder to simulate Portmaster (binds TCP/UDP 53)
- Creates a temporary config and SPB_DATA_DIR for isolated artifacts
- Instantiates DaemonOrchestrator and runs one sync() to exercise detection and fallback
- Captures dns_health.signal and prints result
- Cleans up binder and temporary files

Run as administrator (PowerShell wrapper provided at tools/run_integration_elevated.ps1)
"""
import subprocess
import sys
import tempfile
import time
import os
import json
import signal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DUMMY = os.path.join(HERE, 'dummy_bind.py')

proc = None

def start_binder():
    global proc
    cmd = [sys.executable, '-u', DUMMY]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # Wait for binder to report bound sockets or timeout
    start = time.time()
    while time.time() - start < 10:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        print('[binder]', line.strip())
        if 'UDP bound' in line or 'TCP bound' in line:
            return True
    return False


def stop_binder():
    global proc
    if not proc:
        return
    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except: pass


def make_temp_config(tmpdir):
    cfg = {
        "schema_version": 2,
        "groups": {
            "Default Profile": {
                "websites": ["example.com"],
                "apps": [],
                "files": [],
                "folders": [],
                "adblocker": {"enabled": False},
                "schedule": {"enabled": False},
                "security": {"enabled": False}
            }
        },
        "settings": {"force_dns_proxy": False, "max_domains_cap": 1000}
    }
    path = os.path.join(tmpdir, 'config.json')
    with open(path, 'w') as f:
        json.dump(cfg, f)
    return path


def run():
    tmpdir = tempfile.mkdtemp(prefix='spb_integ_')
    # Ensure orchestrator writes artifacts here
    os.environ['SPB_DATA_DIR'] = tmpdir
    print('[integration] using SPB_DATA_DIR=', tmpdir)

    try:
        ok = start_binder()
        if not ok:
            print('[integration] binder did not report ready; aborting')
            stop_binder()
            return 2

        cfg_path = make_temp_config(tmpdir)
        print('[integration] config written:', cfg_path)

        # Import DaemonOrchestrator dynamically from repo root
        sys.path.insert(0, REPO_ROOT)
        try:
            from daemon import DaemonOrchestrator
        except Exception as e:
            print('[integration] failed to import daemon:', e)
            stop_binder()
            return 3

        orch = DaemonOrchestrator(cfg_path)
        # Run a single sync to exercise detection path
        orch.sync()

        # Wait briefly for any async health updates
        time.sleep(1)

        health_file = os.path.join(tmpdir, 'dns_health.signal')
        if os.path.exists(health_file):
            with open(health_file, 'r') as f:
                status = f.read().strip()
            print('[integration] dns_health.signal =', status)
        else:
            print('[integration] dns_health.signal not created')

        return 0
    finally:
        stop_binder()
        # Do not remove tmpdir to preserve logs; print location for inspection
        print('[integration] artifacts preserved at', tmpdir)

if __name__ == '__main__':
    sys.exit(run())
