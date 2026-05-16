import time
import sys
import os
import random
import string

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from blockers.dns_server import DomainMatcher

def generate_random_domain():
    ext = [".com", ".net", ".org", ".io", ".tv"]
    name = "".join(random.choices(string.ascii_lowercase, k=10))
    return f"{name}{random.choice(ext)}"

def run_bench():
    print("--- Phase A: Logic Benchmark ---")
    # Generate 5,000 rules
    patterns = []
    for _ in range(2000): patterns.append(f"*{generate_random_domain()[:4]}*") # Keywords
    for _ in range(2000): patterns.append(f"*.{generate_random_domain()}")     # Wildcards
    for _ in range(1000): patterns.append(f"{generate_random_domain()[:5]}*")  # Prefixes
    
    matcher = DomainMatcher(patterns)
    
    # Test 50,000 queries
    domains = [generate_random_domain() for _ in range(50000)]
    start = time.perf_counter()
    for d in domains:
        matcher.matches(d)
    end = time.perf_counter()
    
    total_time = end - start
    avg_latency = (total_time / 50000) * 1000
    print(f"Total Rules: {len(patterns)}")
    print(f"Total Queries: 50,000")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Avg Latency: {avg_latency:.4f}ms")
    
    return avg_latency < 10.0

if __name__ == "__main__":
    success = run_bench()
    sys.exit(0 if success else 1)
