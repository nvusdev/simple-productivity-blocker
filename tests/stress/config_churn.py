import threading
import time
import sys
import os
import random

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from blockers.dns_server import DNSProxyServer

def churn_rules(server, duration):
    end_time = time.time() + duration
    updates = 0
    while time.time() < end_time:
        new_rules = [f"site{random.randint(1, 1000)}.com" for _ in range(100)]
        server.update_rules(new_rules, [], [])
        updates += 1
        time.sleep(0.01) # 100 updates/sec
    return updates

def run_churn_test():
    print("--- Phase C: Config Churn Test ---")
    server = DNSProxyServer(manual_list=[], filter_list=[], port=5354)
    
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    time.sleep(1)
    
    print("Churning rules for 10 seconds during server operation...")
    updates = churn_rules(server, 10)
    
    print(f"Total Config Updates: {updates}")
    
    is_alive = server.running
    server.stop()
    
    if not is_alive:
        print("FAILURE: Server crashed during config churn!")
        return False
        
    print("SUCCESS: Server survived rapid config updates.")
    return True

if __name__ == "__main__":
    success = run_churn_test()
    sys.exit(0 if success else 1)
