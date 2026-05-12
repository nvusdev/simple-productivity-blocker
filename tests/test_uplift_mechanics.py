import os
import json
import time
import shutil
import unittest
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from blockers.app_blocker import ProcessMonitor

class TestUpliftMechanics(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.abspath("test_uplift_dir")
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_file = os.path.join(self.test_dir, "lock_me.txt")
        with open(self.test_file, "w") as f:
            f.write("sensitive data")
        
        self.pm = ProcessMonitor()
        self.pm.start()

    def tearDown(self):
        self.pm.stop()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_acl_uplift_on_sync(self):
        print("\nTesting ACL Uplift on Synchronize...")
        # 1. Lock the file
        self.pm.set_blocked_files([self.test_file])
        time.sleep(1) # Wait for async ACL
        
        # Verify locked (can't open for writing)
        try:
            with open(self.test_file, "a") as f:
                f.write("try write")
            locked = False
        except PermissionError:
            locked = True
        
        self.assertTrue(locked, "File should be locked initially")
        print("  Confirmed: File is locked.")

        # 2. Unlock by syncing empty list
        self.pm.synchronize_all([], [], [])
        time.sleep(1) # Wait for async ACL
        
        # Verify unlocked
        try:
            with open(self.test_file, "a") as f:
                f.write(" restored")
            unlocked = True
        except PermissionError:
            unlocked = False
            
        self.assertTrue(unlocked, "File should be unlocked after sync")
        print("  Confirmed: File is unlocked after synchronization.")

if __name__ == "__main__":
    unittest.main()
