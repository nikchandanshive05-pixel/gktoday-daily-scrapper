import os
import sys
import io
import json
import asyncio
from typing import Dict, Any, Set
from pathlib import Path

# Ensure UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from tools.antigravity_bridge.config import DEFAULT_PORT, DEFAULT_PIN_FILE, BRAIN_DIR
from tools.antigravity_bridge.auth import PairingManager
from tools.antigravity_bridge.discovery import DiscoveryService, get_local_ip

class BridgeServer:
    def __init__(self, port: int = DEFAULT_PORT, pin_file: str = DEFAULT_PIN_FILE):
        self.port = port
        self.auth_manager = PairingManager(secret_file=pin_file)
        self.discovery = DiscoveryService(name=f"Antigravity-{os.environ.get('USERNAME', 'PC')}", port=port)
        self.connected_clients: Set[Any] = set()

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "online",
            "host": os.environ.get("COMPUTERNAME", "localhost"),
            "ip": get_local_ip(),
            "port": self.port,
            "pin": self.auth_manager.get_or_create_pin(),
            "brain_dir": str(BRAIN_DIR),
            "clients_count": len(self.connected_clients)
        }

    def start_discovery(self):
        self.discovery.start()

    def stop_discovery(self):
        self.discovery.stop()
