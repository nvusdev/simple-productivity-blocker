import unittest
from unittest import mock

from blockers.dns_server import DNSProxyServer

class DNSProxyStartTests(unittest.TestCase):
    @mock.patch('blockers.dns_server.detect_conflicting_services', return_value='Portmaster (PID: 1234)')
    @mock.patch('blockers.dns_server.load_config', return_value={'settings': {'force_dns_proxy': False}})
    def test_start_aborts_when_conflict_and_not_forced(self, mock_load, mock_detect):
        server = DNSProxyServer([], [])
        res = server.start()
        self.assertFalse(res)

    @mock.patch('blockers.dns_server.detect_conflicting_services', return_value='Portmaster (PID: 1234)')
    @mock.patch('blockers.dns_server.load_config', return_value={'settings': {'force_dns_proxy': True}})
    @mock.patch('blockers.dns_server.flush_dns')
    def test_start_with_force_starts(self, mock_flush, mock_load, mock_detect):
        server = DNSProxyServer([], [], upstream_dns=None, port=53000)
        res = server.start()
        try:
            self.assertTrue(res)
        finally:
            server.stop()

if __name__ == '__main__':
    unittest.main()
