import os
from pathlib import Path

DEFAULT_PORT = 8765
SERVICE_TYPE = "_antigravity._tcp.local."
SERVICE_NAME = "Antigravity Bridge"

HOME_DIR = Path.home()
ANTIGRAVITY_APP_DATA = HOME_DIR / ".gemini" / "antigravity"
BRAIN_DIR = ANTIGRAVITY_APP_DATA / "brain"
CONFIG_DIR = HOME_DIR / ".antigravity_bridge"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PIN_FILE = str(CONFIG_DIR / "pairing_pin.json")
DEFAULT_AUTH_TOKEN_FILE = str(CONFIG_DIR / "auth_tokens.json")
