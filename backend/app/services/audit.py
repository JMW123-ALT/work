import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parents[2] / "data" / "audit_log.jsonl"


class AuditStore:
    def record(self, action: str, user_type: str, detail: dict) -> dict:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        item = {
            "trace_id": f"trace-{uuid.uuid4().hex[:10]}",
            "time": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "user_type": user_type,
            "detail": detail,
        }
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
        return item

    def recent(self, limit: int = 50) -> list[dict]:
        if not LOG_FILE.exists():
            return []
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(line) for line in reversed(lines) if line.strip()]


audit_store = AuditStore()
