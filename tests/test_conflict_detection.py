import unittest
from unittest import mock

import blockers.dns_server as dns_server

class FakeConn:
    def __init__(self, laddr, pid):
        self.laddr = laddr
        self.pid = pid

class FakeProc:
    def __init__(self, name):
        self._name = name
    def name(self):
        return self._name

class DetectConflictTests(unittest.TestCase):
    def test_detect_by_port_listener(self):
        # Mock psutil.net_connections to report a listener on port 53
        with mock.patch('psutil.net_connections', return_value=[FakeConn(('0.0.0.0', 53), 4242)]), \
             mock.patch('psutil.Process', return_value=FakeProc('Portmaster')):
            res = dns_server.detect_conflicting_services()
            self.assertIn('Portmaster', res)

    def test_no_conflict(self):
        # Mock all psutil calls and platform detection to ensure deterministic result
        with mock.patch('psutil.net_connections', return_value=[]), \
             mock.patch('psutil.process_iter', return_value=[]), \
             mock.patch('core.platform_handler.detect_security_appliances', return_value=None):
            res = dns_server.detect_conflicting_services()
            self.assertIsNone(res)

if __name__ == '__main__':
    unittest.main()
