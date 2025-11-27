"""
JWT Authentication Middleware for Flask
Integrates with Spring Boot JWT tokens
"""
import jwt
import logging
import base64
from functools import wraps
from flask import request, jsonify
from datetime import datetime

logger = logging.getLogger(__name__)


class JWTAuthConfig:
    """JWT Configuration - must match Spring Boot settings"""
    # This is the Base64 encoded secret from application.properties
    JWT_SECRET_BASE64 = "U2VjdXJlSldUS2V5MTIzITIzITIzIUxvbmdFbm91hfshfjshfZ2gadsd"
    
    # Decode it to match what Spring Boot does with Decoders.BASE64.decode()
    JWT_SECRET = base64.b64decode(JWT_SECRET_BASE64)
    
    JWT_ALGORITHM = "HS256"


class JWTAuth:
    """JWT Authentication Handler"""
    
    @staticmethod
    def decode_token(token):
        """Decode and validate JWT token"""
        try:
            # Decode token using the same secret as Spring Boot
            payload = jwt.decode(
                token,
                JWTAuthConfig.JWT_SECRET,
                algorithms=[JWTAuthConfig.JWT_ALGORITHM]
            )
            
            # Check expiration
            exp = payload.get('exp')
            if exp and datetime.fromtimestamp(exp) < datetime.now():
                return None, "Token has expired"
            
            # Extract email from 'sub' claim (Spring Boot uses subject for email)
            email = payload.get('sub')
            if not email:
                return None, "Invalid token payload"
            
            return {
                'email': email,
                'exp': exp,
                'iat': payload.get('iat')
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
        
        # Expected format: "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
        
        return parts[1]


def token_required(f):
    """Decorator to protect routes with JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'status': 'error',
                'error': 'Authorization header is missing',
                'message': 'Please provide a valid authentication token'
            }), 401
        
        # Extract token
        token = JWTAuth.extract_token_from_header(auth_header)
        if not token:
            return jsonify({
                'status': 'error',
                'error': 'Invalid authorization header format',
                'message': 'Expected format: Bearer <token>'
            }), 401
        
        # Decode and validate token
        payload, error = JWTAuth.decode_token(token)
        if error:
            return jsonify({
                'status': 'error',
                'error': error,
                'message': 'Authentication failed'
            }), 401
        
        # Add user info to request context
        request.user_email = payload['email']
        request.user_payload = payload
        
        return f(*args, **kwargs)
    
    return decorated


def optional_token(f):
    """Decorator for routes where token is optional"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            token = JWTAuth.extract_token_from_header(auth_header)
            if token:
                payload, error = JWTAuth.decode_token(token)
                if not error:
                    request.user_email = payload['email']
                    request.user_payload = payload
        
        # If no token or invalid token, continue without user info
        if not hasattr(request, 'user_email'):
            request.user_email = None
            request.user_payload = None
        
        return f(*args, **kwargs)
    
    return decorated