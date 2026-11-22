import os
import sys
import io
import json
import asyncio
import threading
from typing import Dict, Any, Set, Optional
from pathlib import Path

# Ensure UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from tools.antigravity_bridge.config import DEFAULT_PORT, DEFAULT_PIN_FILE, BRAIN_DIR, CONFIG_DIR
from tools.antigravity_bridge.auth import PairingManager
from tools.antigravity_bridge.discovery import DiscoveryService, get_local_ip
from tools.antigravity_bridge.action_state import ActionStateMachine
from tools.antigravity_bridge.indexer import WorkspaceIndexer
from tools.antigravity_bridge.transcript_tailer import TranscriptTailer
from tools.antigravity_bridge.telegram_relay import TelegramRelay

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

        # Load Telegram configuration if available
        self.telegram_config_file = CONFIG_DIR / "telegram_config.json"
        self.telegram_relay: Optional[TelegramRelay] = None
        self._init_telegram()

    def _init_telegram(self):
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if not token and self.telegram_config_file.exists():
            try:
                cfg = json.loads(self.telegram_config_file.read_text(encoding="utf-8"))
                token = cfg.get("token")
                chat_id = cfg.get("chat_id")
            except Exception:
                pass
        
        if token and chat_id:
            self.telegram_relay = TelegramRelay(token=token, chat_id=chat_id, action_state=self.action_state)
            self.telegram_relay.on_user_prompt = self._handle_telegram_prompt
            print("[BridgeServer] Telegram relay initialized.")

    def _handle_telegram_prompt(self, prompt: str):
        print(f"[BridgeServer] Received prompt from Telegram: {prompt}")
        # Broadcast to connected clients
        # In full CLI supervision, this writes to stdin / user_input queue

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "online",
            "host": os.environ.get("COMPUTERNAME", "localhost"),
            "ip": get_local_ip(),
            "port": self.port,
            "pin": self.auth_manager.get_or_create_pin(),
            "brain_dir": str(self.indexer.brain_dir),
            "clients_count": len(self.connected_clients),
            "pending_actions": len(self.action_state.list_pending_actions()),
            "telegram_active": self.telegram_relay is not None and self.telegram_relay.token != "mock"
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

    def request_approval(self, action_id: str, description: str) -> Dict[str, Any]:
        """Registers a pending action and notifies both connected Android apps and Telegram"""
        action = self.action_state.register_action(action_id, description)
        if self.telegram_relay:
            self.telegram_relay.send_approval_request(action_id, description)
        return action

    def resolve_action(self, action_id: str, status: str, resolved_by: str = "android") -> bool:
        success = self.action_state.resolve_action(action_id, status, resolved_by)
        if success and self.telegram_relay:
            # Update Telegram message
            emoji = "✅ Approved" if status == "approved" else "❌ Denied"
            self.telegram_relay.send_message(f"{emoji} action `{action_id}` via {resolved_by.capitalize()}.")
        return success

    def start_discovery(self):
        self.discovery.start()

    def stop_discovery(self):
        self.discovery.stop()
