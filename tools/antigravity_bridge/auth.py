import os
import json
import random
import secrets
from pathlib import Path
from typing import Optional

class PairingManager:
    def __init__(self, secret_file: str):
        self.secret_file = Path(secret_file)
        self.secret_file.parent.mkdir(parents=True, exist_ok=True)
        self._current_pin: Optional[str] = None
        self._paired_tokens: set[str] = set()
        self._load()

    def _load(self):
        if self.secret_file.exists():
            try:
                data = json.loads(self.secret_file.read_text(encoding="utf-8"))
                self._current_pin = data.get("pin")
                self._paired_tokens = set(data.get("tokens", []))
            except Exception:
                self._current_pin = None
                self._paired_tokens = set()

    def _save(self):
        data = {
            "pin": self._current_pin,
            "tokens": list(self._paired_tokens)
        }
        self.secret_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_or_create_pin(self) -> str:
        if not self._current_pin or len(self._current_pin) != 4 or not self._current_pin.isdigit():
            self._current_pin = f"{random.randint(1000, 9999)}"
            self._save()
        return self._current_pin

    def verify_pin(self, pin: str) -> bool:
        if not self._current_pin:
            self.get_or_create_pin()
        return self._current_pin == pin.strip()

    def issue_auth_token(self) -> str:
        token = secrets.token_hex(16)
        self._paired_tokens.add(token)
        self._save()
        return token

    def verify_token(self, token: str) -> bool:
        return token in self._paired_tokens
