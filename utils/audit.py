from models import AuditLog
from database import SessionLocal
import json

def log_event(event: str, data: dict):
    db = SessionLocal()

    log = AuditLog(
        event=event,
        data=json.dumps(data)
    )

    db.add(log)
    db.commit()