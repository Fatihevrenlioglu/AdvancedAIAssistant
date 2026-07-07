"""JWT authentication and password hashing helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class AuthManager:
    """Manage JWT token creation and verification."""

    def __init__(self, secret_key: str, algorithm: str = "HS256", expiry_minutes: int = 60) -> None:
        """Initialize authentication configuration."""
        if not secret_key:
            raise ValueError("A secret key is required for authentication.")
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expiry_minutes = expiry_minutes
        self._password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def create_token(self, user_id: str, roles: Optional[List[str]] = None) -> str:
        """Create a signed JWT access token."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self.expiry_minutes)
        payload: Dict[str, Any] = {
            "sub": user_id,
            "roles": roles or [],
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT access token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise ValueError("Token has expired.") from exc
        except jwt.PyJWTError as exc:
            raise ValueError("Invalid token.") from exc
        if not payload.get("sub"):
            raise ValueError("Token payload is missing subject.")
        return payload

    def get_current_user(self, token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
        """FastAPI dependency that returns the current authenticated user."""
        return self.verify_token(token)

    def hash_password(self, plain: str) -> str:
        """Hash a plaintext password."""
        if not plain:
            raise ValueError("Password cannot be empty.")
        return self._password_context.hash(plain)

    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verify a plaintext password against a hash."""
        if not plain or not hashed:
            return False
        return self._password_context.verify(plain, hashed)
