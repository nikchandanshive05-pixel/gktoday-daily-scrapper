import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.antigravity_bridge.action_state import ActionStateMachine
from tools.antigravity_bridge.telegram_relay import TelegramRelay

class TestTelegramRelay(unittest.TestCase):
    def test_telegram_action_callback(self):
        state = ActionStateMachine()
        state.register_action("act-test", "Run bash git status")
        relay = TelegramRelay(token="mock", chat_id="12345", action_state=state)
        
        result = relay.process_simulated_callback("approve:act-test")
        self.assertEqual(result, "Action approved")
        self.assertEqual(state.get_action("act-test")["status"], "approved")
        self.assertEqual(state.get_action("act-test")["resolved_by"], "telegram")

    def test_telegram_deny_callback(self):
        state = ActionStateMachine()
        state.register_action("act-deny", "Delete files")
        relay = TelegramRelay(token="mock", chat_id="12345", action_state=state)
        
        result = relay.process_simulated_callback("deny:act-deny")
        self.assertEqual(result, "Action denied")
        self.assertEqual(state.get_action("act-deny")["status"], "denied")
        self.assertEqual(state.get_action("act-deny")["resolved_by"], "telegram")

if __name__ == "__main__":
    unittest.main()
