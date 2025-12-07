import jwt
import requests
from functools import wraps
from flask import request, jsonify
import logging
from dailyrecommendationAI.config import Config

logger = logging.getLogger(__name__)

class JWTAuth:
    def __init__(self):
        self.jwt_secret = Config.JWT_SECRET
        self.spring_boot_auth_url = Config.SPRING_BOOT_AUTH_URL
        self.verify_mode = Config.JWT_VERIFY_MODE
    
    def extract_token(self, request):
        """Extract JWT token from Authorization header"""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove 'Bearer ' prefix
        return None
    
    def verify_token_local(self, token):
        """Verify JWT token locally using the shared secret"""
        try:
            # Decode and verify token using the same secret as Spring Boot
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=['HS256']
            )
            return {
                'valid': True,
                'email': payload.get('sub'),
                'payload': payload
            }
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return {'valid': False, 'error': 'Token has expired'}
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return {'valid': False, 'error': 'Invalid token'}
    
    def verify_token_remote(self, token):
        """Verify token"""
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                f"{self.spring_boot_auth_url}/validate-token",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'SUCCESS':
                    # Extract email from token locally for user info
                    try:
                        payload = jwt.decode(token, options={"verify_signature": False})
                        return {
                            'valid': True,
                            'email': payload.get('sub'),
                            'payload': payload
                        }
                    except:
                        return {'valid': True, 'email': None, 'payload': {}}
            
            return {'valid': False, 'error': 'Token validation failed'}
        
        except requests.RequestException as e:
            logger.error(f"Error connecting to Spring Boot auth service: {e}")
            # Fallback to local verification if remote service is unavailable
            return self.verify_token_local(token)
    
    def verify_token(self, token):
        """Verify token using configured mode"""
        if self.verify_mode == 'remote':
            return self.verify_token_remote(token)
        else:
            return self.verify_token_local(token)
    
    def get_user_email_from_token(self, token):
        """Extract user email from token"""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get('sub')
        except:
            return None

# Create global instance
jwt_auth = JWTAuth()

def token_required(f):
    """Decorator to protect routes with JWT"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = jwt_auth.extract_token(request)
        
        if not token:
            return jsonify({
                'error': 'Authentication token is missing',
                'message': 'Please provide a valid JWT token in the Authorization header'
            }), 401
        
        # Verify token
        verification_result = jwt_auth.verify_token(token)
        
        if not verification_result['valid']:
            return jsonify({
                'error': 'Invalid or expired token',
                'message': verification_result.get('error', 'Token verification failed')
            }), 401
        
        # Add user info to request context
        request.user_email = verification_result.get('email')
        request.token_payload = verification_result.get('payload', {})
        
        return f(*args, **kwargs)
    
    return decorated

def optional_token(f):
    """Decorator that extracts token info if present but doesn't require it"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = jwt_auth.extract_token(request)
        
        if token:
            verification_result = jwt_auth.verify_token(token)
            if verification_result['valid']:
                request.user_email = verification_result.get('email')
                request.token_payload = verification_result.get('payload', {})
            else:
                request.user_email = None
                request.token_payload = {}
        else:
            request.user_email = None
            request.token_payload = {}
        
        return f(*args, **kwargs)
    
    return decorated