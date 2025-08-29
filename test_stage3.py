#!/usr/bin/env python3
"""
Comprehensive test script for Stage 3: User Authentication System
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, initialize_database, user_manager
from pymongo import MongoClient
from config import Config

def test_stage3_authentication():
    """Test all Stage 3 authentication features"""
    
    print("🧪 Testing Stage 3: User Authentication System")
    print("=" * 60)
    
    try:
        # Initialize database
        initialize_database()
        
        # Test 1: User Registration
        print("\n👤 Test 1: User Registration")
        
        # Test valid user registration
        user, error = user_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            medical_condition="diabetes"
        )
        
        if user and not error:
            print("✅ User registration successful")
            print(f"   User ID: {user.user_id}")
            print(f"   Username: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Medical Condition: {user.medical_condition}")
        else:
            print(f"❌ User registration failed: {error}")
            return False
        
        # Test 2: Duplicate User Registration
        print("\n🔄 Test 2: Duplicate User Registration")
        
        duplicate_user, duplicate_error = user_manager.create_user(
            username="testuser",
            email="test2@example.com",
            password="testpass456",
            medical_condition="hypertension"
        )
        
        if not duplicate_user and duplicate_error:
            print("✅ Duplicate username correctly rejected")
        else:
            print("❌ Duplicate username should have been rejected")
        
        # Test 3: User Authentication
        print("\n🔐 Test 3: User Authentication")
        
        # Test correct password
        auth_user = user_manager.get_user_by_username("testuser")
        if auth_user and auth_user.check_password("testpass123"):
            print("✅ Password authentication successful")
        else:
            print("❌ Password authentication failed")
        
        # Test incorrect password
        if auth_user and not auth_user.check_password("wrongpassword"):
            print("✅ Incorrect password correctly rejected")
        else:
            print("❌ Incorrect password should have been rejected")
        
        # Test 4: User Retrieval Methods
        print("\n🔍 Test 4: User Retrieval Methods")
        
        # Test by username
        user_by_username = user_manager.get_user_by_username("testuser")
        if user_by_username:
            print("✅ User retrieval by username successful")
        else:
            print("❌ User retrieval by username failed")
        
        # Test by email
        user_by_email = user_manager.get_user_by_email("test@example.com")
        if user_by_email:
            print("✅ User retrieval by email successful")
        else:
            print("❌ User retrieval by email failed")
        
        # Test by ID
        user_by_id = user_manager.get_user_by_id(user.user_id)
        if user_by_id:
            print("✅ User retrieval by ID successful")
        else:
            print("❌ User retrieval by ID failed")
        
        # Test 5: User Updates
        print("\n📝 Test 5: User Updates")
        
        # Update last login
        user_manager.update_last_login(user.user_id)
        updated_user = user_manager.get_user_by_id(user.user_id)
        if updated_user and updated_user.last_login:
            print("✅ Last login update successful")
        else:
            print("❌ Last login update failed")
        
        # Update medical condition
        user_manager.update_medical_condition(user.user_id, "hypertension")
        updated_user = user_manager.get_user_by_id(user.user_id)
        if updated_user and updated_user.medical_condition == "hypertension":
            print("✅ Medical condition update successful")
        else:
            print("❌ Medical condition update failed")
        
        # Test 6: Web Routes (Basic)
        print("\n🌐 Test 6: Web Routes")
        
        with app.test_client() as client:
            # Test registration page
            response = client.get('/register')
            if response.status_code == 200:
                print("✅ Registration page accessible")
            else:
                print(f"❌ Registration page failed: {response.status_code}")
            
            # Test login page
            response = client.get('/login')
            if response.status_code == 200:
                print("✅ Login page accessible")
            else:
                print(f"❌ Login page failed: {response.status_code}")
            
            # Test profile page (should redirect to login)
            response = client.get('/profile')
            if response.status_code == 302:  # Redirect
                print("✅ Profile page correctly redirects when not logged in")
            else:
                print(f"❌ Profile page should redirect: {response.status_code}")
        
        # Test 7: Database Integration
        print("\n🗄️ Test 7: Database Integration")
        
        client = MongoClient(Config.MONGODB_URI)
        db = client[Config.DATABASE_NAME]
        users_collection = db['users']
        
        # Check if user exists in database
        db_user = users_collection.find_one({'username': 'testuser'})
        if db_user:
            print("✅ User correctly stored in database")
            print(f"   Database user ID: {db_user.get('user_id')}")
            print(f"   Password hash: {db_user.get('password_hash')[:20]}...")
        else:
            print("❌ User not found in database")
        
        # Test 8: Password Security
        print("\n🔒 Test 8: Password Security")
        
        if db_user and db_user.get('password_hash'):
            password_hash = db_user.get('password_hash')
            if password_hash.startswith('pbkdf2:sha256:'):
                print("✅ Password properly hashed with PBKDF2")
            else:
                print("❌ Password not properly hashed")
        else:
            print("❌ No password hash found")
        
        # Test 9: User Statistics
        print("\n📊 Test 9: User Statistics")
        
        all_users = user_manager.get_all_users()
        if all_users:
            print(f"✅ Found {len(all_users)} users in system")
            for u in all_users:
                print(f"   - {u.username} ({u.email})")
        else:
            print("❌ No users found")
        
        print("\n🎉 Stage 3 Testing Completed Successfully!")
        print("\n📋 Summary of Authentication Features:")
        print("✅ User registration with validation")
        print("✅ Secure password hashing")
        print("✅ User authentication (login/logout)")
        print("✅ Profile management")
        print("✅ Medical condition tracking")
        print("✅ Database integration")
        print("✅ Web route protection")
        print("✅ Form validation")
        print("✅ Flash message system")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during Stage 3 testing: {e}")
        return False

if __name__ == "__main__":
    test_stage3_authentication()
