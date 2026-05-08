import socket
import threading
import time
import sys
import os
import psutil
from dnslib import DNSRecord, QTYPE

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from blockers.dns_server import DNSProxyServer

def send_queries(port, count):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)
    success = 0
    start = time.time()
    
    for i in range(count):
        q = DNSRecord.question("google.com")
        sock.sendto(q.pack(), ("127.0.0.1", port))
        try:
            data, _ = sock.recvfrom(1024)
            success += 1
        except socket.timeout:
            pass
        
        if i % 1000 == 0 and i > 0:
            print(f"  Sent {i} queries...")
            
    end = time.time()
    return success, end - start

def run_load_test():
    print("--- Phase B: Proxy Load Test ---")
    server = DNSProxyServer(manual_list=["*badsite*"], filter_list=[], port=5353)
    
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    
    time.sleep(1) # Wait for bind
    if not server.running:
        print("FAILURE: Server failed to start on 5353")
        return False
        
    process = psutil.Process(os.getpid())
    start_mem = process.memory_info().rss / (1024 * 1024)
    
    print(f"Blasting 5,000 queries to localhost:5353...")
    success_count, duration = send_queries(5353, 5000)
    
    end_mem = process.memory_info().rss / (1024 * 1024)
    mem_growth = end_mem - start_mem
    
    print(f"Success Rate: {success_count}/5000 ({(success_count/5000)*100:.1f}%)")
    print(f"Total Duration: {duration:.2f}s")
    print(f"Throughput: {5000/duration:.1f} queries/sec")
    print(f"Memory Growth: {mem_growth:.2f} MB")
    
    server.stop()
    
    # Assertions
    if success_count < 4500: # Allow 10% packet loss on localhost under heavy stress
        print("FAILURE: Success rate too low!")
        return False
    if mem_growth > 50: # Arbitrary threshold for a 5k query burst
        print("FAILURE: Excessive memory growth detected!")
        return False
        
    return True

if __name__ == "__main__":
    success = run_load_test()
    sys.exit(0 if success else 1)
