from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app.core.config import settings


class JWTHandler:
    def __init__(self):
        self._secret = settings.JWT_SECRET
        self._algorithm = "HS256"
        self._expire_minutes = settings.JWT_EXPIRE_MINUTES

    def create_access_token(self, subject: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=self._expire_minutes)
        payload = {"sub": subject, "exp": expire}
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_token(self, token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            return payload.get("sub")
        except jwt.PyJWTError:
            return None
