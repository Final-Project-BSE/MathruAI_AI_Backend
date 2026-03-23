"""JWT authentication utilities for linking Spring Boot users to chat sessions."""
import base64
import logging
from functools import wraps
from typing import Optional

import jwt
from flask import current_app, request

logger = logging.getLogger(__name__)


class AuthUtils:
    """Utilities for handling JWT authentication from Spring Boot."""
    def __init__(self, jwt_secret_key: str):
        self.original_key = jwt_secret_key or ""
        self.jwt_secret = self._process_jwt_secret(self.original_key)
        if self.jwt_secret:
            logger.info("JWT secret processed successfully")
        else:
            logger.warning("JWT secret is empty; authenticated endpoints will not work")

    def _process_jwt_secret(self, secret_key: str) -> bytes:
        if not secret_key:
            return b""
        try:
            decoded_secret = base64.b64decode(secret_key)
            if 0 < len(decoded_secret) < 32:
                logger.warning("Decoded secret is short (%s bytes), padding to 32 bytes", len(decoded_secret))
                return (decoded_secret * ((32 // len(decoded_secret)) + 1))[:32]
            return decoded_secret
        except Exception:
            utf8_secret = secret_key.encode("utf-8")
            if 0 < len(utf8_secret) < 32:
                logger.warning("UTF-8 secret is short (%s bytes), padding to 32 bytes", len(utf8_secret))
                return (utf8_secret * ((32 // len(utf8_secret)) + 1))[:32]
            return utf8_secret

    def extract_user_from_token(self, token: str) -> Optional[dict]:
        try:
            if token.startswith("Bearer "):
                token = token[7:]
            if not token or not self.jwt_secret:
                return None

            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "require_exp": False,
                    "require_iat": False,
                    "require_nbf": False,
                },
            )
            return self._extract_user_info_from_payload(payload)
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidSignatureError:
            logger.warning("JWT signature is invalid")
            return None
        except jwt.InvalidTokenError as exc:
            logger.warning("JWT token is invalid: %s", exc)
            return None
        except Exception as exc:
            logger.exception("Unexpected error extracting user from token: %s", exc)
            return None

    def _extract_user_info_from_payload(self, payload: dict) -> Optional[dict]:
        try:
            user_identifier = payload.get("sub")
            if not user_identifier:
                logger.warning("No 'sub' field found in JWT payload")
                return None
            return {
                "user_id": user_identifier,
                "username": user_identifier,
                "email": user_identifier,
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "raw_payload": payload,
            }
        except Exception as exc:
            logger.exception("Error extracting user info from payload: %s", exc)
            return None

    def get_current_user(self) -> Optional[dict]:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        return self.extract_user_from_token(auth_header)


def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from chatbot.utils.response_utils import create_error_response

        if not hasattr(current_app, "auth_utils"):
            logger.error("Authentication not configured - auth_utils missing from app")
            return create_error_response("Authentication not configured", 500)

        user = current_app.auth_utils.get_current_user()
        if not user:
            logger.warning("Authentication failed for endpoint: %s", request.endpoint)
            return create_error_response("Authentication required", 401)

        request.current_user = user
        return f(*args, **kwargs)

    return decorated_function
