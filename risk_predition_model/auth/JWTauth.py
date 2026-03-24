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
        return f(*args, **kwargs)

    return decorated


def optional_token(f):
    """Decorator for routes where token is optional"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        request.user_email = None
        request.user_payload = None

        if auth_header:
            token = JWTAuth.extract_token_from_header(auth_header)
            if token:
                payload, error = JWTAuth.decode_token(token)
                if not error:
                    request.user_email = payload["email"]
                    request.user_payload = payload

        return f(*args, **kwargs)

    return decorated