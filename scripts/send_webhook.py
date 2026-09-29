import hashlib
import hmac
import json
import sys

import httpx

from app.config import settings

booking_id, status, event_id, provider_ref = sys.argv[1:5]
body = json.dumps(
    {"event_id": event_id, "booking_id": int(booking_id), "provider_ref": provider_ref, "status": status}
).encode()
signature = hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()

response = httpx.post(
    "http://127.0.0.1:8000/payments/webhook/",
    content=body,
    headers={"X-Signature": signature, "Content-Type": "application/json"},
)
print(response.status_code, response.json())