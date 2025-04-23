from flask import Blueprint, jsonify, request, current_app
import re, jwt
from sqlalchemy import exc
from app import db
from app.api.models.User import User
# Authentication
from functools import wraps
from auth_blacklist import is_token_blacklisted

user_blueprint = Blueprint('user', __name__)

@user_blueprint.route('/api/users', methods=['POST'], strict_slashes=False)
def post():
    post_data = request.get_json()
    if not post_data:
        return jsonify({ 'errors': ['Invalid request.']}), 400
    
    username = post_data.get('username')
    email = post_data.get('email')
    password = post_data.get('password')

    # Validate request data (v2)
    required_fields = {'username': username, 'email': email, 'password': password}
    missing_fields = [field for field, value in required_fields.items() if not value]

    if missing_fields:
        return jsonify({'errors': f"The following fields are required: {', '.join(missing_fields)}"}), 400

    # Validate request data
    #if not email or not username or not password:
    #    return jsonify({ 'errors': "All fields are requeriment"}), 400
    
    # Validate username
    # Sin espacios, guiones al principio o puntos al inicio o al final
    # Entre 3 y 20 caracteres  
    USER_REGEX = r'^[a-zA-Z][a-zA-Z0-9_]{2,15}$'
    #USER_REGEX = r'^(?!^[._-])(?!.*[._-]{2})(?!.*[._-]$)[a-zA-Z0-9._-]{3,20}$'
    if not re.match(USER_REGEX, username):
        return jsonify({'error': "Username is invalid"}), 400
    
    # User unicity
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({ 'error': "Username is already taken"}), 400
    
    # Validate email
    EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(EMAIL_REGEX, email):
        return jsonify({ 'error': "Email format is invalid"}), 400
    
    # Validate password
    
    # Email unicity
    existing_email = User.query.filter_by(email=email).first()
    if existing_email:
        return jsonify({"error": "Email has been used"}), 400
    
    # Create and save new user
    new_user = User(username=username, email=email)
    new_user.set_password(password) #Hash for the password
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered succesfully"}), 201


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Read token with format Bearer
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
        if not token:
            return jsonify({'error': 'A valid  token is missing'}), 401
        
        # Verified token in blacklist
        if is_token_blacklisted(token):
            return jsonify({'error': 'Token has been revoked'}), 401

        
        try:
            # Validate token and automatic expiration
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            from app.api.models.User import User
            current_user = User.query.get(payload['user_id'])
            if not current_user:
                return jsonify({'error': 'User not found.'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        # Pass the autenticate user to endpoint 
        return f(current_user, *args, **kwargs)
        '''
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token missing'}), 401
        '''
    return decorated

@user_blueprint.route('/api/users/<int:user_id>', methods=['GET'], strict_slashes=False)
@token_required
def get_user(current_user, user_id):
    record = User.query.get(user_id)
    if not record:
        return jsonify({
            'errors': [f'No record with id={user_id} found.']}), 404

    # Allow the user to view their own information
    if current_user.id != record.id:
        return jsonify({'error': 'Unauthorized access'}), 403

    return jsonify(record.to_json()), 200
