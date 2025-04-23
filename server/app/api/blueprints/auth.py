
from flask import Blueprint, jsonify, request, current_app
import re, datetime, jwt
from sqlalchemy import exc
from app import db
from app.api.models.User import User
# Authentication
from app.api.blueprints.users import token_required
from app.api.auth_blacklist import add_token

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

            expires_at = datetime.datetime.utcfromtimestamp(payload['exp'])
            # Add token to blacklist next to its expiration datetime
            add_token(token, expires_at)
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 400

        return jsonify({"message": "Logout successful"}), 200
    else:
            return jsonify({"error": "Token not provided"}), 400
    
@auth_blueprint.route('/api/auth/forgot-password', methods=['POST'], strict_slashes=False)
def forgot_password():
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({'error': 'Missing credentials'}), 400
    
    # Search user by email
    user = User.query.filter_by(email=data.get('email')).first()
    if not user:
        return jsonify({'error': 'No user was found with that email address'}), 404
    
    # Create token, expires at 0.5 hour
    exp_date = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
    payload = {
        'user_id': user.id,
        'exp': exp_date
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

    if isinstance(token, bytes):
        token = token.decode('utf-8')

    # Save tokens
    user.reset_token = token
    user.reset_token_expires = exp_date
    db.session.commit()

    #implement send token via email

    #para pruebas
    return jsonify({'token': token}), 200


@auth_blueprint.route('/api/auth/reset-password', methods=['POST'], strict_slashes=False)
def reset_password():
    data = request.get_json()
    
    if not data or not data.get('token') or not data.get('new_password'):
        return jsonify({'error': 'Missing credentials'}), 400

    # Search user by token
    user = User.query.filter_by(reset_token=data.get('token')).first()
    if not user:
        return jsonify({'error': 'The token was not validated or user not found'}), 404
    
    now = datetime.datetime.utcnow()
    if now > user.reset_token_expires:
        return jsonify({'error': 'The token has expired. Please request a new password reset link.'}), 401


    new_password = data.get('new_password')
    user.set_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.session.commit()

    return jsonify({"message": "Password has been successfully reestablished."}), 200