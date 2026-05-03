# test_after_fix.py
from auth.jwt import create_token, decode_token, is_token_expired
from datetime import datetime

# Create token
token = create_token({"user_id": 1, "email": "test@example.com"})
print(f"Token created: {token[:50]}...")

# Decode and check expiration
decoded = decode_token(token)
exp_time = datetime.fromtimestamp(decoded['exp'])
now = datetime.utcnow()

print(f"Expires: {exp_time}")
print(f"Valid until: {(exp_time - now).total_seconds() / 60:.1f} minutes from now")
print(f"Is expired? {is_token_expired(token)}")