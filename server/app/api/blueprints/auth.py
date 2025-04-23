
from flask import Blueprint, jsonify, request, current_app
import re, datetime, jwt
from sqlalchemy import exc
from app import db
from app.api.models.User import User
# Authentication
from users import token_required
from auth_blacklist import add_token

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/api/auth/login', methods=['POST'], strict_slashes=False)
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing credentials'}), 400
    
    # Search user by username
    user = User.query.filter_by(username=data.get('username')).first()
    if not user or not user.check_password(data.get('password')):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Create token, expires at 1 hour
    payload = {
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    return jsonify({'token': token}), 200

@auth_blueprint.route('/api/auth/logout', methods=['POST'], strict_slashes=False)
@token_required
def logout(current_user):
    auth_header = request.headers.get('Authorization')
    token = auth_header.split()[1] if auth_header else None

    if token:
        try:
            # Decode token and extract its expiration datetime
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms='HS256')
            
            expires_at = datetime.utcfromtimestamp(payload['exp'])
            # Add token to blacklist next to its expiration datetime
            add_token(token, expires_at)
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 400

        return jsonify({"message": "Logout successful"}), 200
    else:
            return jsonify({"error": "Token not provided"}), 400