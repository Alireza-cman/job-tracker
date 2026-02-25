# Authentication Guide

This guide explains how to set up and manage authentication for the Job Application Tracker.

## Overview

The application uses:
- **Password hashing**: bcrypt via passlib
- **Session tokens**: HMAC-signed JWT-like tokens
- **Per-user data isolation**: All data is scoped to the logged-in user

## Setup

### 1. Generate SECRET_KEY

The `SECRET_KEY` is used to sign session tokens. Generate a secure one:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Set Environment Variables

Add to your `.env` file:

```bash
SECRET_KEY=your-64-character-hex-string-here
OPENAI_API_KEY=sk-your-openai-key
```

Or export directly:

```bash
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

### 3. On EC2/Production

Add to your systemd service file:

```ini
[Service]
EnvironmentFile=/home/ubuntu/JobApply/.env
```

Or in Docker:

```bash
docker run -e SECRET_KEY=your-key -e OPENAI_API_KEY=sk-xxx ...
```

## Creating Users

### Option 1: Self-Registration (Default)

Users can create accounts via the Sign Up tab on the login page.

### Option 2: CLI Script (Admin-Created)

For admin-controlled user creation:

```bash
cd /path/to/JobApply
source venv/bin/activate
python scripts/create_user.py admin@example.com
```

You'll be prompted to enter a password.

### Option 3: Disable Self-Registration

To disable self-registration, edit `core/session.py` and remove the Sign Up tab from `show_login_page()`.

## Password Requirements

Passwords must be at least 4 characters long.

## Security Features

### Rate Limiting

Login attempts are rate-limited:
- Maximum 5 failed attempts
- 60-second cooldown after max attempts
- Resets on successful login

### Token Expiry

Session tokens expire after 7 days. Users will need to log in again.

### Data Isolation

Each user can only:
- View their own applications
- Edit their own applications
- Export their own data
- Duplicate detection is per-user

## Migration from Pre-Auth Database

If you have existing applications from before authentication was added:

1. The migration automatically creates a default admin user:
   - Email: `admin@jobtracker.local`
   - Temporary random password

2. All existing applications are assigned to this admin user.

3. **Important**: Create a new admin account and update the default user's password:

```bash
# Create your actual admin account
python scripts/create_user.py your-email@example.com

# Then log in with your new account
```

## Testing Authentication

Run the auth tests:

```bash
cd /path/to/JobApply
source venv/bin/activate
pip install pytest
python -m pytest tests/test_auth.py -v
```

## Troubleshooting

### "SECRET_KEY not set" Error

Make sure `SECRET_KEY` is set in your environment:

```bash
echo $SECRET_KEY  # Should output your key
```

### "Invalid email or password" but credentials are correct

1. Check that the user exists in the database
2. Ensure you're using the correct email (case-insensitive)
3. Check for rate limiting (wait 60 seconds)

### Session expires too quickly

The default token expiry is 7 days. To change it, edit `core/auth.py`:

```python
TOKEN_EXPIRY = 7 * 24 * 60 * 60  # Change this value
```

### Database locked errors

If you see SQLite "database is locked" errors with multiple users:
- Consider switching to PostgreSQL for production
- Or use a connection pool

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  Streamlit UI   │────▶│  core/session   │
│   (Login Page)  │     │  (Auth State)   │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
┌─────────────────┐     ┌─────────────────┐
│   core/auth     │◀────│    SQLite DB    │
│ (Hash/Token)    │     │ (users table)   │
└─────────────────┘     └─────────────────┘
```

### Files

| File | Purpose |
|------|---------|
| `core/auth.py` | Password hashing, token signing, user CRUD |
| `core/session.py` | Streamlit session management, login UI |
| `scripts/create_user.py` | CLI for admin user creation |
| `tests/test_auth.py` | Unit tests for auth functions |

## API Reference

### `core.auth`

```python
hash_password(password: str) -> str
verify_password(password: str, hash: str) -> bool
create_user(email: str, password: str) -> Tuple[Optional[str], str]
authenticate(email: str, password: str) -> Tuple[Optional[str], str]
sign_token(user_id: str) -> str
verify_token(token: str) -> Optional[str]
```

### `core.session`

```python
require_login()  # Call at top of each page
is_logged_in() -> bool
get_current_user_id() -> Optional[str]
get_current_user_email() -> Optional[str]
login(email: str, password: str) -> Tuple[bool, str]
signup(email: str, password: str, confirm: str) -> Tuple[bool, str]
logout()
show_user_sidebar()  # Shows user email + logout button
```
