import os
import sys
import unittest
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.antigravity_bridge.auth import PairingManager
from tools.antigravity_bridge.discovery import get_service_info_payload

class TestBridgeAuthAndDiscovery(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.secret_file = os.path.join(self.test_dir, "test_pin.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_pin_verification(self):
        mgr = PairingManager(secret_file=self.secret_file)
        pin = mgr.get_or_create_pin()
        self.assertEqual(len(pin), 4)
        self.assertTrue(pin.isdigit())
        self.assertTrue(mgr.verify_pin(pin))
        self.assertFalse(mgr.verify_pin("0000" if pin != "0000" else "1111"))

    def test_discovery_payload(self):
        payload = get_service_info_payload("Nikhil-PC", 8765)
        self.assertEqual(payload["type"], "_antigravity._tcp.local.")
        self.assertEqual(payload["port"], 8765)
        self.assertEqual(payload["name"], "Nikhil-PC")

if __name__ == "__main__":
    unittest.main()
