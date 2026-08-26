#!/usr/bin/env python3
"""
Password Reset Tool for Liara
Usage: python reset_password.py <username> <new_password>
"""

import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from core.database import SessionLocal
from api.models.base_models import User
from core.security import hash_password, invalidate_sessions

def reset_password(username: str, new_password: str):
    """Reset user password"""
    db = SessionLocal()
    
    try:
        # Find user (case-insensitive)
        user = db.query(User).filter(User.username == username.lower().strip()).first()
        
        if not user:
            print(f"❌ User '{username}' not found!")
            return False
        
        # Hash new password
        hashed_pw = hash_password(new_password)
        
        # Update password - also ends every existing session (issue #11
        # item 3), same reasoning as the API's password-change paths.
        user.hashed_password = hashed_pw
        invalidate_sessions(db, user)
        db.commit()
        
        print(f"✅ Password updated for user '{user.username}'")
        print(f"   Role: {user.role}")
        print(f"   Active: {user.is_active}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reset_password.py <username> <new_password>")
        print("\nExample:")
        print("  python reset_password.py admin MyNewPassword123")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    if len(password) < 6:
        print("❌ Password must be at least 6 characters!")
        sys.exit(1)
    
    success = reset_password(username, password)
    sys.exit(0 if success else 1)
