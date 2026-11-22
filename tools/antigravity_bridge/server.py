import os
import sys
import io
import json
import asyncio
from typing import Dict, Any, Set, Optional
from pathlib import Path

# Ensure UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from tools.antigravity_bridge.config import DEFAULT_PORT, DEFAULT_PIN_FILE, BRAIN_DIR
from tools.antigravity_bridge.auth import PairingManager
from tools.antigravity_bridge.discovery import DiscoveryService, get_local_ip
from tools.antigravity_bridge.action_state import ActionStateMachine
from tools.antigravity_bridge.indexer import WorkspaceIndexer
from tools.antigravity_bridge.transcript_tailer import TranscriptTailer

class BridgeServer:
    def __init__(self, port: int = DEFAULT_PORT, pin_file: str = DEFAULT_PIN_FILE, brain_dir: str = str(BRAIN_DIR)):
        self.port = port
        self.auth_manager = PairingManager(secret_file=pin_file)
        self.discovery = DiscoveryService(name=f"Antigravity-{os.environ.get('USERNAME', 'PC')}", port=port)
        self.action_state = ActionStateMachine()
        self.indexer = WorkspaceIndexer(brain_dir=brain_dir)
        self.active_tailer: Optional[TranscriptTailer] = None
        self.active_conv_id: Optional[str] = None
        self.connected_clients: Set[Any] = set()

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "online",
            "host": os.environ.get("COMPUTERNAME", "localhost"),
            "ip": get_local_ip(),
            "port": self.port,
            "pin": self.auth_manager.get_or_create_pin(),
            "brain_dir": str(self.indexer.brain_dir),
            "clients_count": len(self.connected_clients),
            "pending_actions": len(self.action_state.list_pending_actions())
        }

    def attach_conversation(self, conv_id: str) -> Optional[TranscriptTailer]:
        conv_dir = self.indexer.brain_dir / conv_id
        transcript_path = conv_dir / ".system_generated" / "logs" / "transcript.jsonl"
        if not transcript_path.exists():
            transcript_path = conv_dir / "transcript.jsonl"
            if not transcript_path.exists():
                return None
        self.active_conv_id = conv_id
        self.active_tailer = TranscriptTailer(str(transcript_path))
        return self.active_tailer

    def start_discovery(self):
        self.discovery.start()

    def stop_discovery(self):
        self.discovery.stop()
