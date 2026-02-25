#!/usr/bin/env python3
"""
CLI script to create users for Job Application Tracker.
Usage: python scripts/create_user.py <email> [--admin]
"""
import sys
import os
import getpass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.auth import create_user, user_exists, validate_email


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/create_user.py <email>")
        print("Example: python scripts/create_user.py admin@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    
    # Validate email
    if not validate_email(email):
        print(f"Error: Invalid email format: {email}")
        sys.exit(1)
    
    # Check if user already exists
    if user_exists(email):
        print(f"Error: User with email {email} already exists")
        sys.exit(1)
    
    # Get password securely
    print(f"Creating user: {email}")
    password = getpass.getpass("Enter password: ")
    confirm = getpass.getpass("Confirm password: ")
    
    if password != confirm:
        print("Error: Passwords do not match")
        sys.exit(1)
    
    # Create user
    user_id, error = create_user(email, password)
    
    if user_id:
        print(f"✅ User created successfully!")
        print(f"   Email: {email}")
        print(f"   User ID: {user_id}")
    else:
        print(f"❌ Failed to create user: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
