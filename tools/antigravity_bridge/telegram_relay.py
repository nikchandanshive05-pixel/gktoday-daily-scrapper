import json
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, Callable
from tools.antigravity_bridge.action_state import ActionStateMachine

class TelegramRelay:
    def __init__(self, token: str, chat_id: str, action_state: ActionStateMachine):
        self.token = token.strip()
        self.chat_id = chat_id.strip()
        self.action_state = action_state
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0
        self.on_user_prompt: Optional[Callable[[str], None]] = None

    def send_message(self, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> bool:
        if not self.token or self.token == "mock":
            return False
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[TelegramRelay] send_message error: {e}")
            return False

    def send_approval_request(self, action_id: str, description: str) -> bool:
        text = f"⚠️ *Action Requires Approval*\n\n`{description}`\n\nApprove or Deny execution:"
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve", "callback_data": f"approve:{action_id}"},
                    {"text": "❌ Deny", "callback_data": f"deny:{action_id}"}
                ]
            ]
        }
        return self.send_message(text, reply_markup=reply_markup)

    def process_simulated_callback(self, callback_data: str) -> str:
        """Processes a callback query string, e.g. 'approve:act-1' or 'deny:act-1'"""
        parts = callback_data.split(":", 1)
        if len(parts) != 2:
            return "Invalid callback format"
        action, action_id = parts[0], parts[1]
        
        target_status = "approved" if action == "approve" else "denied"
        success = self.action_state.resolve_action(action_id, target_status, resolved_by="telegram")
        if success:
            return f"Action {target_status}"
        else:
            return "Action already resolved or expired"

    def poll_updates(self):
        """Polls for new updates from Telegram (long polling)"""
        if not self.token or self.token == "mock":
            return
        try:
            url = f"{self.api_url}/getUpdates?offset={self.last_update_id + 1}&timeout=20"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for update in data.get("result", []):
                    self.last_update_id = max(self.last_update_id, update.get("update_id", 0))
                    
                    # Handle callback query
                    if "callback_query" in update:
                        cb = update["callback_query"]
                        cb_data = cb.get("data", "")
                        msg = self.process_simulated_callback(cb_data)
                        # Answer callback query
                        ans_url = f"{self.api_url}/answerCallbackQuery"
                        ans_payload = json.dumps({"callback_query_id": cb.get("id"), "text": msg}).encode("utf-8")
                        urllib.request.urlopen(urllib.request.Request(ans_url, data=ans_payload, headers={"Content-Type": "application/json"}))
                    
                    # Handle incoming message prompt
                    elif "message" in update:
                        msg = update["message"]
                        text = msg.get("text", "")
                        if text and str(msg.get("chat", {}).get("id")) == str(self.chat_id):
                            if self.on_user_prompt:
                                self.on_user_prompt(text)
        except Exception:
            pass
