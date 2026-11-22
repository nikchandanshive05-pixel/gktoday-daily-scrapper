import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

class TranscriptTailer:
    def __init__(self, transcript_path: str):
        self.transcript_path = Path(transcript_path)
        self.last_byte_offset = 0

    def read_all_steps(self) -> List[Dict[str, Any]]:
        self.last_byte_offset = 0
        return self.read_new_steps()

    def read_new_steps(self) -> List[Dict[str, Any]]:
        steps = []
        if not self.transcript_path.exists():
            return steps

        try:
            with open(self.transcript_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self.last_byte_offset)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        step_data = json.loads(line)
                        steps.append(step_data)
                    except json.JSONDecodeError:
                        continue
                self.last_byte_offset = f.tell()
        except Exception:
            pass

        return steps
