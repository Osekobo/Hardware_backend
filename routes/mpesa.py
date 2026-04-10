from fastapi import APIRouter, Request
from tasks.mpesa_tasks import process_mpesa_callback
from utils.redis_client import redis_client
import json
import hashlib

router = APIRouter()


# 🔐 Create unique identity key
def generate_identity_key(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


@router.post("/callback")
async def mpesa_callback(request: Request):

    # 1. Read raw body (important for hashing)
    raw_body = await request.body()

    # 2. Generate identity key
    identity_key = generate_identity_key(raw_body)

    # 3. CHECK REDIS (duplicate protection)
    if redis_client.get(identity_key):
        return {"status": "duplicate ignored"}

    # 4. Store key in Redis (expires in 1 hour)
    redis_client.set(identity_key, "1", ex=3600)

    # 5. Parse JSON safely
    try:
        data = json.loads(raw_body)
    except:
        return {"status": "invalid json"}

    # 6. Basic validation
    if "Body" not in data:
        return {"status": "invalid payload"}

    # 7. Push to Celery queue (async processing)
    process_mpesa_callback.delay(data)

    return {
        "status": "queued",
        "identity_key": identity_key
    }