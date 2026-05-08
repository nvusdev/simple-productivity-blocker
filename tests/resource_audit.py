import time
import psutil
import os
import sys
import threading

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from blockers.dns_server import DNSProxyServer

def monitor_resources(duration, interval=0.5):
    process = psutil.Process(os.getpid())
    samples = []
    print(f"Monitoring resources for {duration} seconds...")
    for _ in range(int(duration / interval)):
        cpu = process.cpu_percent(interval=interval)
        mem = process.memory_info().rss / (1024 * 1024)
        handles = process.num_handles()
        samples.append((cpu, mem, handles))
        # Use weight/influence check (Ghost Mode target: < 1% CPU)
        status = "PASS" if cpu < 5.0 else "HEAVY" # 5% threshold for burst
        print(f"  CPU: {cpu:4.1f}% | RAM: {mem:5.1f}MB | Handles: {handles:3} | [{status}]")
    return samples

def run_audit():
    print("--- Resource Usage Audit (Ghost Mode Validation) ---")
    
    # 1. Start DNS Server (Idle state)
    server = DNSProxyServer(manual_list=[], filter_list=[], port=53535)
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    time.sleep(1) # Bind
    
    # Audit Idle State (5 seconds)
    print("\n[IDLE AUDIT]")
    idle_samples = monitor_resources(5)
    avg_idle_cpu = sum(s[0] for s in idle_samples) / len(idle_samples)
    avg_idle_mem = sum(s[1] for s in idle_samples) / len(idle_samples)
    avg_idle_handles = sum(s[2] for s in idle_samples) / len(idle_samples)
    
    # 2. Simulate Active Redirection (Using a dummy query loop in background)
    print("\n[LOAD AUDIT - 200 queries/sec]")
    stop_load = False
    def blast():
        import socket
        from dnslib import DNSRecord
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while not stop_load:
            q = DNSRecord.question("test.com")
            sock.sendto(q.pack(), ("127.0.0.1", 53535))
            try:
                sock.recvfrom(1024)
            except: pass
            time.sleep(0.005) # ~200 qps

    load_thread = threading.Thread(target=blast)
    load_thread.start()
    
    load_samples = monitor_resources(5)
    stop_load = True
    load_thread.join()
    
    avg_load_cpu = sum(s[0] for s in load_samples) / len(load_samples)
    avg_load_mem = sum(s[1] for s in load_samples) / len(load_samples)
    avg_load_handles = sum(s[2] for s in load_samples) / len(load_samples)
    
    server.stop()
    
    print("\n--- FINAL REPORT ---")
    print(f"Idle CPU Influence: {avg_idle_cpu:.2f}% (Target: < 1%)")
    print(f"Idle RAM Weight: {avg_idle_mem:.2f} MB")
    print(f"Idle Handles: {avg_idle_handles:.0f}")
    print(f"Load CPU Influence: {avg_load_cpu:.2f}%")
    print(f"Load RAM Weight: {avg_load_mem:.2f} MB")
    print(f"Load Handles: {avg_load_handles:.0f}")
    
    # Ghost Mode Compliance
    ghost_pass = avg_idle_cpu < 1.0
    print(f"GHOST MODE COMPLIANCE: {'SUCCESS' if ghost_pass else 'FAILED'}")
    
    return ghost_pass

if __name__ == "__main__":
    success = run_audit()
    sys.exit(0 if success else 1)
