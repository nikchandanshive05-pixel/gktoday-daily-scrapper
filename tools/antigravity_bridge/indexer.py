import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

class WorkspaceIndexer:
    def __init__(self, brain_dir: str):
        self.brain_dir = Path(brain_dir)

    def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        conversations = []
        if not self.brain_dir.exists():
            return conversations

        for item in self.brain_dir.iterdir():
            if not item.is_dir():
                continue
            conv_id = item.name
            transcript_path = item / ".system_generated" / "logs" / "transcript.jsonl"
            if not transcript_path.exists():
                # Check directly in item directory
                transcript_path = item / "transcript.jsonl"
                if not transcript_path.exists():
                    continue

            stat = transcript_path.stat()
            first_user_prompt = "New Conversation"
            last_agent_snippet = ""
            total_steps = 0

            try:
                with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        step = json.loads(line)
                        total_steps += 1
                        if step.get("type") == "USER_INPUT" and first_user_prompt == "New Conversation":
                            content = step.get("content", "")
                            # strip <USER_REQUEST> tags if present
                            if "<USER_REQUEST>" in content:
                                content = content.split("<USER_REQUEST>")[1].split("</USER_REQUEST>")[0].strip()
                            first_user_prompt = content[:120]
                        elif step.get("type") == "PLANNER_RESPONSE":
                            content = step.get("content", "")
                            if content:
                                last_agent_snippet = content[:150]
            except Exception:
                pass

            conversations.append({
                "id": conv_id,
                "first_user_prompt": first_user_prompt,
                "last_snippet": last_agent_snippet,
                "total_steps": total_steps,
                "updated_at": stat.st_mtime,
                "transcript_path": str(transcript_path)
            })

        # Sort newest first
        conversations.sort(key=lambda c: c["updated_at"], reverse=True)
        return conversations[:limit]

    def get_active_conversation_id(self) -> Optional[str]:
        convs = self.list_conversations(limit=1)
        return convs[0]["id"] if convs else None
