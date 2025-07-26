from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from os import environ
import time
from sqlalchemy.exc import OperationalError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DB_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable modification tracking
db = SQLAlchemy(app)

def wait_for_db():
    """Attempt to connect to database with retries."""
    max_retries = 5
    retry_delay = 5
    for attempt in range(max_retries):
        try:
            db.engine.connect()
            print(f"Database connection established on attempt {attempt + 1}")
            return True
        except OperationalError as e:
            print(f"Database connection failed (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    return False

class User(db.Model):
    """
    Represents a user in the system.

    Attributes:
      id (int): Primary key, unique identifier for the user.
      username (str): Unique username for the user, cannot be null.
      email (str): Unique email address for the user, cannot be null.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def json(self):
        """Returns a dictionary representation of the user."""
        return {'id': self.id, 'username': self.username, 'email': self.email}

# Initialize database with retry logic
if wait_for_db():
    db.create_all()
else:
    print("Failed to connect to database after retries")

@app.route('/test', methods=['GET'])
def test():
    """Test endpoint to verify service availability."""
    return make_response(jsonify({'message': 'test route', 'db_status': 'connected' if db.engine else 'disconnected'}), 200)

@app.route('/users', methods=['POST'])
def create_user():
    """Create a new user."""
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'email' not in data:
            return make_response(jsonify({'message': 'Missing required fields'}), 400)
            
        new_user = User(username=data['username'], email=data['email'])
        db.session.add(new_user)
        db.session.commit()
        return make_response(jsonify({'message': 'user created', 'user': new_user.json()}), 201)
    except Exception as e:
        db.session.rollback()
        return make_response(jsonify({'message': 'error creating user', 'error': str(e)}), 500)

@app.route('/users', methods=['GET'])
def get_users():
    """Get all users."""
    try:
        users = User.query.all()
        return make_response(jsonify([user.json() for user in users]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'error getting users', 'error': str(e)}), 500)

@app.route('/users/<int:id>', methods=['GET'])
def get_user(id):
    """Get a specific user by ID."""
    try:
        user = User.query.filter_by(id=id).first()
        if user:
            return make_response(jsonify({'user': user.json()}), 200)
        return make_response(jsonify({'message': 'user not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'message': 'error getting user', 'error': str(e)}), 500)

@app.route('/users/<int:id>', methods=['PUT'])
def update_user(id):
    """Update an existing user."""
    try:
        user = User.query.filter_by(id=id).first()
        if not user:
            return make_response(jsonify({'message': 'user not found'}), 404)
            
        data = request.get_json()
        if not data or ('username' not in data and 'email' not in data):
            return make_response(jsonify({'message': 'No fields to update'}), 400)
            
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
            
        db.session.commit()
        return make_response(jsonify({'message': 'user updated', 'user': user.json()}), 200)
    except Exception as e:
        db.session.rollback()
        return make_response(jsonify({'message': 'error updating user', 'error': str(e)}), 500)

@app.route('/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    """Delete a user."""
    try:
        user = User.query.filter_by(id=id).first()
        if not user:
            return make_response(jsonify({'message': 'user not found'}), 404)
            
        db.session.delete(user)
        db.session.commit()
        return make_response(jsonify({'message': 'user deleted'}), 200)
    except Exception as e:
        db.session.rollback()
        return make_response(jsonify({'message': 'error deleting user', 'error': str(e)}), 500)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000)