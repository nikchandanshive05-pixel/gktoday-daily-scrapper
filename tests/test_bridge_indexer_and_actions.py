import os
import sys
import unittest
import tempfile
import json
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.antigravity_bridge.action_state import ActionStateMachine
from tools.antigravity_bridge.indexer import WorkspaceIndexer
from tools.antigravity_bridge.transcript_tailer import TranscriptTailer

class TestBridgeIndexerAndActions(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_atomic_action_resolution(self):
        state = ActionStateMachine()
        action = state.register_action(action_id="act-1", description="Run git commit")
        self.assertEqual(action["status"], "pending")
        self.assertTrue(state.resolve_action("act-1", "approved"))
        self.assertEqual(state.get_action("act-1")["status"], "approved")
        # Duplicate resolution must return False (atomic guard)
        self.assertFalse(state.resolve_action("act-1", "denied"))

    def test_workspace_indexer(self):
        # Create mock brain directory structure: <brain_dir>/<conv_id>/.system_generated/logs/transcript.jsonl
        conv_dir = os.path.join(self.test_dir, "conv-123", ".system_generated", "logs")
        os.makedirs(conv_dir, exist_ok=True)
        transcript_file = os.path.join(conv_dir, "transcript.jsonl")
        
        sample_step = {
            "step_index": 0,
            "type": "USER_INPUT",
            "content": "Hello Antigravity",
            "created_at": "2026-11-22T12:00:00Z"
        }
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(sample_step) + "\n")

        indexer = WorkspaceIndexer(brain_dir=self.test_dir)
        conversations = indexer.list_conversations()
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0]["id"], "conv-123")
        self.assertEqual(conversations[0]["first_user_prompt"], "Hello Antigravity")

    def test_transcript_tailer(self):
        transcript_file = os.path.join(self.test_dir, "stream.jsonl")
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"step_index": 0, "type": "USER_INPUT", "content": "Step 0"}) + "\n")

        tailer = TranscriptTailer(transcript_path=transcript_file)
        new_steps = tailer.read_new_steps()
        self.assertEqual(len(new_steps), 1)
        self.assertEqual(new_steps[0]["content"], "Step 0")

        # Append step 1
        with open(transcript_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({"step_index": 1, "type": "PLANNER_RESPONSE", "content": "Step 1"}) + "\n")

        subsequent_steps = tailer.read_new_steps()
        self.assertEqual(len(subsequent_steps), 1)
        self.assertEqual(subsequent_steps[0]["content"], "Step 1")

if __name__ == "__main__":
    unittest.main()
