"""
Tests for authentication module.
"""
import os
import sys
import pytest

# Set test SECRET_KEY
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32chars"

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auth import (
    hash_password,
    verify_password,
    validate_email,
    validate_password,
    sign_token,
    verify_token,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""
    
    def test_hash_password_returns_string(self):
        """Hash should return a string."""
        hashed = hash_password("password123")
        assert isinstance(hashed, str)
        assert len(hashed) > 0
    
    def test_hash_password_different_each_time(self):
        """Same password should produce different hashes (due to salt)."""
        hash1 = hash_password("password123")
        hash2 = hash_password("password123")
        assert hash1 != hash2
    
    def test_verify_password_correct(self):
        """Correct password should verify."""
        password = "MySecureP@ssw0rd"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Incorrect password should not verify."""
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False
    
    def test_verify_password_invalid_hash(self):
        """Invalid hash should return False, not raise."""
        assert verify_password("password", "invalid_hash") is False
        assert verify_password("password", "") is False


class TestEmailValidation:
    """Tests for email validation."""
    
    def test_valid_emails(self):
        """Valid emails should pass."""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user@subdomain.example.com",
            "user123@example.co.uk",
        ]
        for email in valid_emails:
            assert validate_email(email), f"Should be valid: {email}"
    
    def test_invalid_emails(self):
        """Invalid emails should fail."""
        invalid_emails = [
            "invalid",
            "invalid@",
            "@example.com",
            "user@.com",
            "user@example",
            "",
            "user name@example.com",
        ]
        for email in invalid_emails:
            assert not validate_email(email), f"Should be invalid: {email}"


class TestPasswordValidation:
    """Tests for password strength validation."""
    
    def test_valid_password(self):
        """Valid password should pass."""
        is_valid, error = validate_password("123456")
        assert is_valid is True
        assert error == ""
    
    def test_simple_password_ok(self):
        """Simple passwords are allowed."""
        is_valid, error = validate_password("test")
        assert is_valid is True
        assert error == ""
    
    def test_password_too_short(self):
        """Very short password should fail."""
        is_valid, error = validate_password("123")
        assert is_valid is False
        assert "4 characters" in error


class TestTokenSigningVerification:
    """Tests for token signing and verification."""
    
    def test_sign_token_returns_string(self):
        """Sign should return a token string."""
        token = sign_token("user-123")
        assert isinstance(token, str)
        assert "." in token  # Format: payload.signature
    
    def test_verify_valid_token(self):
        """Valid token should return user_id."""
        user_id = "test-user-456"
        token = sign_token(user_id)
        verified_id = verify_token(token)
        assert verified_id == user_id
    
    def test_verify_invalid_token(self):
        """Invalid token should return None."""
        assert verify_token("invalid.token") is None
        assert verify_token("") is None
        assert verify_token("no-dot-here") is None
    
    def test_verify_tampered_token(self):
        """Tampered token should return None."""
        token = sign_token("user-123")
        # Tamper with the signature
        payload, _ = token.split(".")
        tampered = f"{payload}.invalidsignature"
        assert verify_token(tampered) is None
    
    def test_token_contains_user_id(self):
        """Different users should get different tokens."""
        token1 = sign_token("user-1")
        token2 = sign_token("user-2")
        assert token1 != token2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
