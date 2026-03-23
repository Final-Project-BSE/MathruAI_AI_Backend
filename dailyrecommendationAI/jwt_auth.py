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
        self.spring_boot_auth_url = Config.SPRING_BOOT_AUTH_URL.rstrip('/')
        self.verify_mode = Config.JWT_VERIFY_MODE

    def extract_token(self, flask_request):
        auth_header = flask_request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:].strip()
        return None

    def verify_token_local(self, token):
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return {
                'valid': True,
                'email': payload.get('sub'),
                'payload': payload,
            }
        except jwt.ExpiredSignatureError:
            logger.warning('Token has expired')
            return {'valid': False, 'error': 'Token has expired'}
        except jwt.InvalidTokenError as e:
            logger.warning('Invalid token: %s', e)
            return {'valid': False, 'error': 'Invalid token'}

    def verify_token_remote(self, token):
        try:
            response = requests.get(
                f'{self.spring_boot_auth_url}/validate-token',
                headers={'Authorization': f'Bearer {token}'},
                timeout=5,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'SUCCESS':
                    try:
                        payload = jwt.decode(token, options={'verify_signature': False})
                    except Exception:
                        payload = {}
                    return {
                        'valid': True,
                        'email': payload.get('sub'),
                        'payload': payload,
                    }

            return {'valid': False, 'error': 'Token validation failed'}
        except requests.RequestException as e:
            logger.error('Error connecting to Spring Boot auth service: %s', e)
            return self.verify_token_local(token)

    def verify_token(self, token):
        if self.verify_mode == 'remote':
            return self.verify_token_remote(token)
        return self.verify_token_local(token)


jwt_auth = JWTAuth()


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = jwt_auth.extract_token(request)

        if not token:
            return jsonify({
                'error': 'Authentication token is missing',
                'message': 'Please provide a valid JWT token in the Authorization header'
            }), 401

        verification_result = jwt_auth.verify_token(token)
        if not verification_result['valid']:
            return jsonify({
                'error': 'Invalid or expired token',
                'message': verification_result.get('error', 'Token verification failed')
            }), 401

        request.user_email = verification_result.get('email')
        request.token_payload = verification_result.get('payload', {})
        return f(*args, **kwargs)

    return decorated


def optional_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        request.user_email = None
        request.token_payload = {}

        token = jwt_auth.extract_token(request)
        if token:
            verification_result = jwt_auth.verify_token(token)
            if verification_result['valid']:
                request.user_email = verification_result.get('email')
                request.token_payload = verification_result.get('payload', {})

        return f(*args, **kwargs)

    return decorated
