import os
import sys
import io
import json
import asyncio
from typing import Dict, Any, Set, Optional, List
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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
        self.connected_websockets: Set[WebSocket] = set()

        # Load Telegram configuration if available
        self.telegram_config_file = CONFIG_DIR / "telegram_config.json"
        self.telegram_relay: Optional[TelegramRelay] = None
        self._init_telegram()

        # Auto-attach to latest active conversation if any
        latest_id = self.indexer.get_active_conversation_id()
        if latest_id:
            self.attach_conversation(latest_id)

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

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "online",
            "host": os.environ.get("COMPUTERNAME", "localhost"),
            "ip": get_local_ip(),
            "port": self.port,
            "pin": self.auth_manager.get_or_create_pin(),
            "brain_dir": str(self.indexer.brain_dir),
            "clients_count": len(self.connected_websockets),
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
        action = self.action_state.register_action(action_id, description)
        if self.telegram_relay:
            self.telegram_relay.send_approval_request(action_id, description)
        
        # Broadcast to all connected WebSockets
        asyncio.create_task(self.broadcast({
            "type": "action_pending",
            "action_id": action_id,
            "description": description
        }))
        return action

    def resolve_action(self, action_id: str, status: str, resolved_by: str = "android") -> bool:
        success = self.action_state.resolve_action(action_id, status, resolved_by)
        if success:
            if self.telegram_relay:
                emoji = "✅ Approved" if status == "approved" else "❌ Denied"
                self.telegram_relay.send_message(f"{emoji} action `{action_id}` via {resolved_by.capitalize()}.")
            
            # Broadcast resolution
            asyncio.create_task(self.broadcast({
                "type": "action_resolved",
                "action_id": action_id,
                "status": status,
                "resolved_by": resolved_by
            }))
        return success

    async def broadcast(self, message: Dict[str, Any]):
        dead = []
        payload = json.dumps(message)
        for ws in self.connected_websockets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connected_websockets.discard(ws)

    def start_discovery(self):
        self.discovery.start()

    def stop_discovery(self):
        self.discovery.stop()

def create_app(bridge: BridgeServer) -> FastAPI:
    app = FastAPI(title="Antigravity Mobile Bridge")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    @app.get("/api/status")
    def status():
        return bridge.get_status()

    @app.get("/api/conversations")
    def list_conversations():
        return {"items": bridge.indexer.list_conversations()}

    @app.post("/api/approve")
    def approve_action(payload: Dict[str, Any]):
        action_id = payload.get("action_id")
        status = payload.get("status", "approved")
        if not action_id:
            raise HTTPException(status_code=400, detail="Missing action_id")
        success = bridge.resolve_action(action_id, status, resolved_by="api")
        return {"success": success}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        bridge.connected_websockets.add(websocket)
        authenticated = False
        tail_task: Optional[asyncio.Task] = None

        async def tail_streamer():
            while True:
                if bridge.active_tailer:
                    new_steps = bridge.active_tailer.read_new_steps()
                    for step in new_steps:
                        content = step.get("content", "")
                        step_type = step.get("type", "")
                        if content and step_type == "PLANNER_RESPONSE":
                            await websocket.send_text(json.dumps({
                                "type": "token",
                                "delta": content
                            }))
                await asyncio.sleep(0.5)

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                except Exception:
                    continue

                msg_type = msg.get("type")
                if msg_type == "auth":
                    pin = msg.get("pin", "")
                    if bridge.auth_manager.verify_pin(pin):
                        authenticated = True
                        token = bridge.auth_manager.issue_auth_token()
                        await websocket.send_text(json.dumps({
                            "type": "auth_success",
                            "token": token
                        }))
                        if not tail_task:
                            tail_task = asyncio.create_task(tail_streamer())
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "auth_failed",
                            "reason": "Invalid 4-digit PIN"
                        }))

                elif msg_type == "list_conversations":
                    items = bridge.indexer.list_conversations()
                    await websocket.send_text(json.dumps({
                        "type": "conversations",
                        "items": items
                    }))

                elif msg_type == "attach_conversation":
                    conv_id = msg.get("conversation_id")
                    if conv_id:
                        bridge.attach_conversation(conv_id)
                        await websocket.send_text(json.dumps({
                            "type": "attached",
                            "conversation_id": conv_id
                        }))

                elif msg_type == "resolve_action":
                    act_id = msg.get("action_id")
                    st = msg.get("status", "approved")
                    if act_id:
                        bridge.resolve_action(act_id, st, resolved_by="android")

                elif msg_type == "user_input":
                    content = msg.get("content", "")
                    print(f"[Mobile Input] {content}")

        except WebSocketDisconnect:
            pass
        finally:
            if tail_task:
                tail_task.cancel()
            bridge.connected_websockets.discard(websocket)

    return app

def run_bridge_server(host: str = "0.0.0.0", port: int = DEFAULT_PORT):
    bridge = BridgeServer(port=port)
    bridge.start_discovery()
    app = create_app(bridge)

    status = bridge.get_status()
    print("==========================================================")
    print(f" Host IP      : {status['ip']}")
    print(f" Port         : {status['port']}")
    print(f" Pairing PIN  : \033[1;32m{status['pin']}\033[0m")
    print(f" Brain Dir    : {status['brain_dir']}")
    print(f" Telegram Sync: {'Active' if status['telegram_active'] else 'Not Configured'}")
    print("==========================================================")
    print("Listening for mobile connection... (Press Ctrl+C to stop)")

    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    finally:
        bridge.stop_discovery()
