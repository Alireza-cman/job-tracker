"""
Authentication module for Job Application Tracker.
Handles password hashing, token signing, and user management.
"""
import os
import re
import uuid
import hmac
import hashlib
import base64
import json
import time
from datetime import datetime
from typing import Optional, Tuple
from pathlib import Path

# Use passlib with PBKDF2-SHA256 for secure password hashing (no length limit)
from passlib.hash import pbkdf2_sha256

# Database path (same as main database)
DB_PATH = Path(__file__).parent.parent / "data" / "applications.db"

# Token expiry: 7 days in seconds
TOKEN_EXPIRY = 7 * 24 * 60 * 60

# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def get_secret_key() -> str:
    """Get SECRET_KEY from environment. Raises if not set."""
    key = os.getenv("SECRET_KEY")
    if not key:
        raise ValueError(
            "SECRET_KEY environment variable is not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return key


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-SHA256."""
    return pbkdf2_sha256.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pbkdf2_sha256.verify(password, password_hash)
    except Exception:
        return False


def validate_email(email: str) -> bool:
    """Validate email format."""
    return bool(EMAIL_REGEX.match(email))


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password strength.
    Returns (is_valid, error_message).
    """
    if len(password) < 4:
        return False, "Password must be at least 4 characters"
    return True, ""


def sign_token(user_id: str) -> str:
    """
    Create a signed token for a user.
    Token format: base64(json(payload)).signature
    """
    secret = get_secret_key()
    
    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + TOKEN_EXPIRY,
        "iat": int(time.time()),
    }
    
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    
    # Create HMAC signature
    signature = hmac.new(
        secret.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{payload_b64}.{signature}"


def verify_token(token: str) -> Optional[str]:
    """
    Verify a token and return the user_id if valid.
    Returns None if invalid or expired.
    """
    try:
        secret = get_secret_key()
        
        parts = token.split('.')
        if len(parts) != 2:
            return None
        
        payload_b64, signature = parts
        
        # Verify signature
        expected_sig = hmac.new(
            secret.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return None
        
        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_json)
        
        # Check expiry
        if payload.get("exp", 0) < time.time():
            return None
        
        return payload.get("user_id")
        
    except Exception:
        return None


# ============ User Database Operations ============

import sqlite3


def _get_auth_connection() -> sqlite3.Connection:
    """Get database connection for auth operations, ensuring users table exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    # Ensure users table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    
    return conn


def create_user(email: str, password: str) -> Tuple[Optional[str], str]:
    """
    Create a new user.
    Returns (user_id, error_message). user_id is None if failed.
    """
    # Validate email
    email = email.lower().strip()
    if not validate_email(email):
        return None, "Invalid email format"
    
    # Validate password
    is_valid, error = validate_password(password)
    if not is_valid:
        return None, error
    
    # Hash password
    password_hash = hash_password(password)
    
    # Generate user ID
    user_id = str(uuid.uuid4())
    
    try:
        conn = _get_auth_connection()
        conn.execute(
            """
            INSERT INTO users (id, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, email, password_hash, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
        return user_id, ""
    except sqlite3.IntegrityError:
        return None, "Email already registered"
    except Exception as e:
        return None, f"Failed to create user: {str(e)}"


def authenticate(email: str, password: str) -> Tuple[Optional[str], str]:
    """
    Authenticate a user by email and password.
    Returns (user_id, error_message). user_id is None if failed.
    """
    email = email.lower().strip()
    
    try:
        conn = _get_auth_connection()
        cursor = conn.execute(
            "SELECT id, password_hash FROM users WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None, "Invalid email or password"
        
        if not verify_password(password, row["password_hash"]):
            return None, "Invalid email or password"
        
        return row["id"], ""
        
    except Exception as e:
        return None, f"Authentication error: {str(e)}"


def get_user_email(user_id: str) -> Optional[str]:
    """Get user email by ID."""
    try:
        conn = _get_auth_connection()
        cursor = conn.execute(
            "SELECT email FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row["email"]
        return None
    except Exception:
        return None


def user_exists(email: str) -> bool:
    """Check if a user with the given email exists."""
    email = email.lower().strip()
    try:
        conn = _get_auth_connection()
        cursor = conn.execute(
            "SELECT 1 FROM users WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()
        conn.close()
        return row is not None
    except Exception:
        return False


def get_user_count() -> int:
    """Get total number of users."""
    try:
        conn = _get_auth_connection()
        cursor = conn.execute("SELECT COUNT(*) as count FROM users")
        row = cursor.fetchone()
        conn.close()
        return row["count"] if row else 0
    except Exception:
        return 0
