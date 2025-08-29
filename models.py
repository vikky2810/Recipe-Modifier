from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

class User(UserMixin):
    """User model for authentication and data storage"""
    
    def __init__(self, user_id, username, email, password_hash=None, medical_condition=None, 
                 created_at=None, last_login=None):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.password_hash = password_hash or ""
        self.medical_condition = medical_condition
        self.created_at = created_at or datetime.now()
        self.last_login = last_login
    
    def get_id(self):
        """Required by Flask-Login"""
        return str(self.user_id)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password is correct"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary for database storage"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'medical_condition': self.medical_condition,
            'created_at': self.created_at,
            'last_login': self.last_login
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create user from dictionary"""
        return cls(
            user_id=data.get('user_id'),
            username=data.get('username'),
            email=data.get('email'),
            password_hash=data.get('password_hash'),
            medical_condition=data.get('medical_condition'),
            created_at=data.get('created_at'),
            last_login=data.get('last_login')
        )

class UserManager:
    """Manages user operations with MongoDB"""
    
    def __init__(self, db):
        self.db = db
        self.users = db['users']
    
    def create_user(self, username, email, password, medical_condition=None):
        """Create a new user"""
        # Check if username or email already exists
        if self.users.find_one({'$or': [{'username': username}, {'email': email}]}):
            return None, "Username or email already exists"
        
        # Create new user
        user_id = str(uuid.uuid4())
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            medical_condition=medical_condition
        )
        user.set_password(password)
        
        # Save to database
        self.users.insert_one(user.to_dict())
        return user, None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        user_data = self.users.find_one({'user_id': user_id})
        if user_data:
            return User.from_dict(user_data)
        return None
    
    def get_user_by_username(self, username):
        """Get user by username"""
        user_data = self.users.find_one({'username': username})
        if user_data:
            return User.from_dict(user_data)
        return None
    
    def get_user_by_email(self, email):
        """Get user by email"""
        user_data = self.users.find_one({'email': email})
        if user_data:
            return User.from_dict(user_data)
        return None
    
    def update_last_login(self, user_id):
        """Update user's last login time"""
        self.users.update_one(
            {'user_id': user_id},
            {'$set': {'last_login': datetime.now()}}
        )
    
    def update_medical_condition(self, user_id, condition):
        """Update user's medical condition"""
        self.users.update_one(
            {'user_id': user_id},
            {'$set': {'medical_condition': condition}}
        )
    
    def get_all_users(self):
        """Get all users (for admin purposes)"""
        users_data = self.users.find({})
        return [User.from_dict(user_data) for user_data in users_data]
    
    def delete_user(self, user_id):
        """Delete user (for admin purposes)"""
        result = self.users.delete_one({'user_id': user_id})
        return result.deleted_count > 0
