import hashlib
import hmac

from fastapi import HTTPException, status

from core.config import get_settings


class WebhookSignatureVerifier:
    def __init__(self, secret_key: str | None = None) -> None:
        settings = get_settings()
        self.secret_key = (secret_key or settings.webhook_secret_key).encode()

    def verify(self, payload: bytes, signature: str | None) -> None:
        if not signature:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing webhook signature')

        expected_signature = hmac.new(self.secret_key, payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_signature, signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid webhook signature')
