"""
JWT Authentication Middleware for Flask
Integrates with Spring Boot JWT tokens
"""
import os
import jwt
import logging
import base64
from functools import wraps
from flask import request, jsonify
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class JWTAuthConfig:
    """JWT Configuration - must match Spring Boot settings"""
    JWT_SECRET_BASE64 = os.environ.get("JWT_SECRET_KEY", "")
    JWT_ALGORITHM = "HS256"

    @classmethod
    def get_secret(cls):
        if not cls.JWT_SECRET_BASE64:
            raise ValueError("JWT_SECRET_KEY environment variable is not set")
        return base64.b64decode(cls.JWT_SECRET_BASE64)


class JWTAuth:
    """JWT Authentication Handler"""

    @staticmethod
    def _extract_user_id(payload):
        for key in ("userId", "user_id", "id"):
            value = payload.get(key)
            if value is not None and str(value).strip() != "":
                return value
        return None

    @staticmethod
    def _extract_roles(payload):
        raw_roles = payload.get("roles") or payload.get("authorities") or payload.get("scope") or []
        if isinstance(raw_roles, str):
            if "," in raw_roles:
                roles = [role.strip() for role in raw_roles.split(",") if role.strip()]
            else:
                roles = [role.strip() for role in raw_roles.split() if role.strip()]
        elif isinstance(raw_roles, (list, tuple, set)):
            roles = [str(role).strip() for role in raw_roles if str(role).strip()]
        else:
            roles = []
        return roles

    @staticmethod
    def decode_token(token):
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(
                token,
                JWTAuthConfig.get_secret(),
                algorithms=[JWTAuthConfig.JWT_ALGORITHM]
            )

            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                return None, "Token has expired"

            email = payload.get("sub")
            if not email:
                return None, "Invalid token payload"

            return {
                "email": email,
                "user_id": JWTAuth._extract_user_id(payload),
                "roles": JWTAuth._extract_roles(payload),
                "exp": exp,
                "iat": payload.get("iat")
            }, None

        except jwt.ExpiredSignatureError:
            return None, "Token has expired"
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            return None, "Invalid token"
        except Exception as e:
            logger.error(f"Token decode error: {str(e)}")
            return None, "Token validation failed"

    @staticmethod
    def extract_token_from_header(auth_header):
        """Extract token from Authorization header"""
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]


def token_required(f):
    """Decorator to protect routes with JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({
                "status": "error",
                "error": "Authorization header is missing",
                "message": "Please provide a valid authentication token"
            }), 401

        token = JWTAuth.extract_token_from_header(auth_header)
        if not token:
            return jsonify({
                "status": "error",
                "error": "Invalid authorization header format",
                "message": "Expected format: Bearer <token>"
            }), 401

        payload, error = JWTAuth.decode_token(token)
        if error:
            return jsonify({
                "status": "error",
                "error": error,
                "message": "Authentication failed"
            }), 401

        request.user_email = payload["email"]
        request.user_payload = payload
        request.user_id = payload.get("user_id")
        request.user_roles = payload.get("roles", [])
        return f(*args, **kwargs)

    return decorated


def optional_token(f):
    """Decorator for routes where token is optional"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        request.user_email = None
        request.user_payload = None
        request.user_id = None
        request.user_roles = []

        if auth_header:
            token = JWTAuth.extract_token_from_header(auth_header)
            if token:
                payload, error = JWTAuth.decode_token(token)
                if not error:
                    request.user_email = payload["email"]
                    request.user_payload = payload
                    request.user_id = payload.get("user_id")
                    request.user_roles = payload.get("roles", [])

        return f(*args, **kwargs)

    return decorated
