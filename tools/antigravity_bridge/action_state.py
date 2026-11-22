import threading
import time
from typing import Dict, Any, Optional

class ActionStateMachine:
    def __init__(self):
        self._lock = threading.Lock()
        self._actions: Dict[str, Dict[str, Any]] = {}

    def register_action(self, action_id: str, description: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            action = {
                "id": action_id,
                "description": description,
                "metadata": metadata or {},
                "status": "pending",  # pending, approved, denied
                "resolved_by": None,  # android, telegram, desktop
                "created_at": time.time(),
                "resolved_at": None
            }
            self._actions[action_id] = action
            return action

    def get_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._actions.get(action_id)

    def resolve_action(self, action_id: str, status: str, resolved_by: str = "android") -> bool:
        """
        Atomically resolves a pending action.
        Returns True if the action was successfully transitioned from 'pending'.
        Returns False if the action was not found or was already resolved (guarding against races).
        """
        with self._lock:
            action = self._actions.get(action_id)
            if not action or action["status"] != "pending":
                return False
            
            action["status"] = status
            action["resolved_by"] = resolved_by
            action["resolved_at"] = time.time()
            return True

    def list_pending_actions(self) -> list[Dict[str, Any]]:
        with self._lock:
            return [act for act in self._actions.values() if act["status"] == "pending"]
