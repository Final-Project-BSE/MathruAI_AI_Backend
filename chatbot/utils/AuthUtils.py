"""
JWT authentication utilities for linking Spring Boot users to chat sessions - COMPLETELY FIXED VERSION.
"""
import base64
import jwt
from flask import request
from functools import wraps
import logging
import json

logger = logging.getLogger(__name__)


class AuthUtils:
    """Utilities for handling JWT authentication from Spring Boot - COMPLETELY FIXED VERSION."""
    
    def __init__(self, jwt_secret_key):
        """
        Initialize AuthUtils with proper key handling for Spring Boot compatibility.
        
        Args:
            jwt_secret_key (str): JWT secret key (Base64 encoded string from Spring Boot)
        """
        self.original_key = jwt_secret_key
        self.jwt_secret = self._process_jwt_secret(jwt_secret_key)
        logger.info(f"JWT secret processed successfully")
        logger.info(f"Original key length: {len(self.original_key)}")
        logger.info(f"Processed key length: {len(self.jwt_secret)} bytes")
    
    def _process_jwt_secret(self, secret_key):
        """
        Process JWT secret to match Spring Boot's key format exactly.
        
        Spring Boot uses Keys.hmacShaKeyFor(Decoders.BASE64.decode(jwtSecret))
        which means the secret is Base64-decoded bytes.
        
        Args:
            secret_key (str): The Base64-encoded secret key from application.properties
            
        Returns:
            bytes: Decoded secret key ready for PyJWT
        """
        try:
            # Spring Boot decodes the Base64 secret, so we need to do the same
            decoded_secret = base64.b64decode(secret_key)
            logger.info(f"Base64 decoded secret: {len(decoded_secret)} bytes")
            
            # Ensure minimum length for HS256 (32 bytes)
            if len(decoded_secret) < 32:
                logger.warning(f"Decoded secret is short ({len(decoded_secret)} bytes), padding to 32 bytes")
                # Repeat the secret to reach 32 bytes
                repeated = (decoded_secret * ((32 // len(decoded_secret)) + 1))[:32]
                return repeated
            
            return decoded_secret
            
        except Exception as e:
            logger.error(f"Failed to decode Base64 secret: {e}")
            logger.info("Falling back to UTF-8 encoding of original string")
            
            # Fallback: treat as plain text and ensure minimum length
            utf8_secret = secret_key.encode('utf-8')
            if len(utf8_secret) < 32:
                # Pad to 32 bytes
                padded = (utf8_secret * ((32 // len(utf8_secret)) + 1))[:32]
                return padded
            return utf8_secret
    
    def extract_user_from_token(self, token):
        """
        Extract user information from JWT token with Spring Boot compatibility.
        
        Args:
            token (str): JWT token
            
        Returns:
            dict: User information or None if invalid
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            logger.debug(f"Attempting to decode token: {token[:20]}...")
            
            # First, check token structure without verification
            try:
                unverified = jwt.decode(token, options={"verify_signature": False})
                logger.debug(f"Token payload (unverified): {json.dumps(unverified, indent=2, default=str)}")
            except Exception as e:
                logger.error(f"Failed to decode token structure: {e}")
                return None
            
            # Try to decode with HS256 (most common with Spring Boot HMAC)
            try:
                payload = jwt.decode(
                    token, 
                    self.jwt_secret, 
                    algorithms=['HS256'],
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_nbf": True,
                        "verify_iat": True,
                        "require_exp": False,  # Make expiration optional for testing
                        "require_iat": False,  # Make issued-at optional
                        "require_nbf": False   # Make not-before optional
                    }
                )
                
                logger.info("Successfully decoded token with HS256")
                logger.debug(f"Verified payload: {json.dumps(payload, indent=2, default=str)}")
                
                # Extract user information
                user_info = self._extract_user_info_from_payload(payload)
                if user_info:
                    logger.info(f"Extracted user: {user_info['user_id']}")
                    return user_info
                else:
                    logger.warning("Could not extract user info from payload")
                    return None
                    
            except jwt.ExpiredSignatureError:
                logger.warning("JWT token has expired")
                return None
            except jwt.InvalidSignatureError:
                logger.error("JWT signature is invalid - check secret key configuration")
                logger.error(f"Expected secret preview: {self.jwt_secret[:10].hex()}...")
                return None
            except jwt.InvalidTokenError as e:
                logger.error(f"JWT token is invalid: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error extracting user from token: {str(e)}")
            return None
    
    def _extract_user_info_from_payload(self, payload):
        """
        Extract user information from JWT payload.
        
        Spring Boot typically uses 'sub' for the user identifier (email).
        
        Args:
            payload (dict): JWT payload
            
        Returns:
            dict: Standardized user information
        """
        try:
            # Get the subject (user identifier) - Spring Boot uses email as subject
            user_identifier = payload.get('sub')
            if not user_identifier:
                logger.warning("No 'sub' field found in JWT payload")
                return None
            
            # Additional fields that might be present
            issued_at = payload.get('iat')
            expires_at = payload.get('exp')
            
            user_info = {
                'user_id': user_identifier,  # Use email as user_id
                'username': user_identifier,  # Use email as username
                'email': user_identifier,     # Email is the subject
                'issued_at': issued_at,
                'expires_at': expires_at,
                'raw_payload': payload
            }
            
            logger.info(f"Extracted user info: user_id={user_identifier}")
            return user_info
            
        except Exception as e:
            logger.error(f"Error extracting user info from payload: {e}")
            return None
    
    def get_current_user(self):
        """
        Get current user from request headers.
        
        Returns:
            dict: User information or None
        """
        # Check for Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            logger.debug("No Authorization header found")
            return None
        
        if not auth_header.startswith('Bearer '):
            logger.debug("Authorization header doesn't start with 'Bearer '")
            return None
        
        logger.debug("Authorization header found, extracting token...")
        return self.extract_user_from_token(auth_header)
    
    def debug_token_info(self, token=None):
        """
        Debug method to analyze token and key compatibility.
        
        Args:
            token (str, optional): Token to analyze
            
        Returns:
            dict: Debug information
        """
        if not token:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return {"error": "No token provided"}
            
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
            else:
                token = auth_header
        
        debug_info = {
            "token_length": len(token),
            "token_parts": len(token.split('.')),
            "secret_info": {
                "original_key_length": len(self.original_key),
                "processed_key_length": len(self.jwt_secret),
                "processed_key_hex": self.jwt_secret[:16].hex() if len(self.jwt_secret) >= 16 else self.jwt_secret.hex(),
                "key_type": type(self.jwt_secret).__name__
            }
        }
        
        try:
            # Decode header without verification
            header = jwt.get_unverified_header(token)
            debug_info["token_header"] = header
            
            # Decode payload without verification
            payload = jwt.decode(token, options={"verify_signature": False})
            debug_info["token_payload"] = payload
            
            # Try verification with our secret
            try:
                verified_payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
                debug_info["verification_status"] = "SUCCESS"
                debug_info["verified_payload"] = verified_payload
            except Exception as verify_error:
                debug_info["verification_status"] = "FAILED"
                debug_info["verification_error"] = str(verify_error)
            
        except Exception as e:
            debug_info["decode_error"] = str(e)
        
        return debug_info


def require_auth(f):
    """
    Authentication decorator that requires valid JWT token.
    
    Usage: @require_auth
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import current_app
        from chatbot.utils.response_utils import create_error_response
        
        # Get auth_utils from current app
        if not hasattr(current_app, 'auth_utils'):
            logger.error("Authentication not configured - auth_utils missing from app")
            return create_error_response("Authentication not configured", 500)
        
        user = current_app.auth_utils.get_current_user()
        if not user:
            logger.warning(f"Authentication failed for endpoint: {request.endpoint}")
            # Log the authorization header for debugging (first 20 chars only)
            auth_header = request.headers.get('Authorization', 'None')
            logger.debug(f"Auth header: {auth_header[:20]}..." if len(auth_header) > 20 else auth_header)
            return create_error_response("Authentication required", 401)
        
        logger.info(f"User authenticated: {user['user_id']} accessing {request.endpoint}")
        
        # Add user to request context
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function


def create_debug_auth_endpoints(app):
    """
    Create debug endpoints for JWT troubleshooting.
    Only use in development!
    
    Args:
        app: Flask application instance
    """
    from flask import Blueprint, jsonify, request
    
    debug_bp = Blueprint('debug_auth', __name__)
    
    @debug_bp.route('/jwt-info', methods=['POST'])
    def debug_jwt_info():
        """Debug endpoint to analyze JWT token structure."""
        try:
            data = request.get_json() or {}
            token = data.get('token')
            
            if not hasattr(app, 'auth_utils'):
                return jsonify({"error": "AuthUtils not configured"}), 500
            
            debug_info = app.auth_utils.debug_token_info(token)
            return jsonify(debug_info)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @debug_bp.route('/auth-headers', methods=['GET', 'POST'])
    def debug_auth_headers():
        """Debug endpoint to check request headers."""
        return jsonify({
            "method": request.method,
            "headers": dict(request.headers),
            "auth_header": request.headers.get('Authorization', 'Not present'),
            "user": app.auth_utils.get_current_user() if hasattr(app, 'auth_utils') else None
        })
    
    @debug_bp.route('/test-decode', methods=['POST'])
    def test_token_decode():
        """Test decoding a specific token."""
        try:
            data = request.get_json() or {}
            token = data.get('token')
            
            if not token:
                return jsonify({"error": "No token provided"}), 400
            
            if not hasattr(app, 'auth_utils'):
                return jsonify({"error": "AuthUtils not configured"}), 500
            
            # Test extraction
            user = app.auth_utils.extract_user_from_token(token)
            
            return jsonify({
                "extraction_success": user is not None,
                "user_info": user,
                "debug_info": app.auth_utils.debug_token_info(token)
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # Register debug blueprint
    app.register_blueprint(debug_bp, url_prefix='/api/debug')
    logger.info("Debug authentication endpoints registered at /api/debug/")