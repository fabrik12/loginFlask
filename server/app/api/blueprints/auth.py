
from flask import Blueprint, jsonify, request, current_app
import re, datetime, jwt
from sqlalchemy import exc
from app import db
from app.api.models.User import User

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