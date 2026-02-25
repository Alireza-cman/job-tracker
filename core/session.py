"""
Streamlit session management for authentication.
Provides helpers to manage login state across pages.
"""
import streamlit as st
from typing import Optional
import time

from .auth import verify_token, sign_token, get_user_email, authenticate, create_user

# Session state keys
USER_ID_KEY = "auth_user_id"
USER_EMAIL_KEY = "auth_user_email"
AUTH_TOKEN_KEY = "auth_token"
LOGIN_ATTEMPTS_KEY = "login_attempts"
LAST_ATTEMPT_KEY = "last_login_attempt"

# Rate limiting
MAX_LOGIN_ATTEMPTS = 5
COOLDOWN_SECONDS = 60


def init_session():
    """Initialize session state for auth."""
    if USER_ID_KEY not in st.session_state:
        st.session_state[USER_ID_KEY] = None
    if USER_EMAIL_KEY not in st.session_state:
        st.session_state[USER_EMAIL_KEY] = None
    if AUTH_TOKEN_KEY not in st.session_state:
        st.session_state[AUTH_TOKEN_KEY] = None
    if LOGIN_ATTEMPTS_KEY not in st.session_state:
        st.session_state[LOGIN_ATTEMPTS_KEY] = 0
    if LAST_ATTEMPT_KEY not in st.session_state:
        st.session_state[LAST_ATTEMPT_KEY] = 0


def is_logged_in() -> bool:
    """Check if user is currently logged in."""
    init_session()
    
    # First check session state
    if st.session_state[USER_ID_KEY]:
        return True
    
    # Check for stored token (cookie persistence)
    token = st.session_state.get(AUTH_TOKEN_KEY)
    if token:
        user_id = verify_token(token)
        if user_id:
            email = get_user_email(user_id)
            if email:
                st.session_state[USER_ID_KEY] = user_id
                st.session_state[USER_EMAIL_KEY] = email
                return True
        # Token invalid, clear it
        st.session_state[AUTH_TOKEN_KEY] = None
    
    return False


def get_current_user_id() -> Optional[str]:
    """Get the current logged-in user's ID."""
    init_session()
    return st.session_state.get(USER_ID_KEY)


def get_current_user_email() -> Optional[str]:
    """Get the current logged-in user's email."""
    init_session()
    return st.session_state.get(USER_EMAIL_KEY)


def is_rate_limited() -> tuple[bool, int]:
    """
    Check if login is rate limited.
    Returns (is_limited, seconds_remaining).
    """
    init_session()
    
    attempts = st.session_state.get(LOGIN_ATTEMPTS_KEY, 0)
    last_attempt = st.session_state.get(LAST_ATTEMPT_KEY, 0)
    
    if attempts >= MAX_LOGIN_ATTEMPTS:
        elapsed = time.time() - last_attempt
        if elapsed < COOLDOWN_SECONDS:
            return True, int(COOLDOWN_SECONDS - elapsed)
        # Cooldown passed, reset attempts
        st.session_state[LOGIN_ATTEMPTS_KEY] = 0
    
    return False, 0


def record_login_attempt():
    """Record a failed login attempt."""
    init_session()
    st.session_state[LOGIN_ATTEMPTS_KEY] = st.session_state.get(LOGIN_ATTEMPTS_KEY, 0) + 1
    st.session_state[LAST_ATTEMPT_KEY] = time.time()


def reset_login_attempts():
    """Reset login attempts after successful login."""
    init_session()
    st.session_state[LOGIN_ATTEMPTS_KEY] = 0


def login(email: str, password: str) -> tuple[bool, str]:
    """
    Attempt to log in a user.
    Returns (success, error_message).
    """
    init_session()
    
    # Check rate limiting
    is_limited, remaining = is_rate_limited()
    if is_limited:
        return False, f"Too many login attempts. Please wait {remaining} seconds."
    
    # Authenticate
    user_id, error = authenticate(email, password)
    
    if user_id:
        # Success - set session state
        st.session_state[USER_ID_KEY] = user_id
        st.session_state[USER_EMAIL_KEY] = email.lower().strip()
        
        # Create token for persistence
        token = sign_token(user_id)
        st.session_state[AUTH_TOKEN_KEY] = token
        
        reset_login_attempts()
        return True, ""
    else:
        record_login_attempt()
        return False, error


def signup(email: str, password: str, confirm_password: str) -> tuple[bool, str]:
    """
    Create a new user account.
    Returns (success, error_message).
    """
    init_session()
    
    # Validate passwords match
    if password != confirm_password:
        return False, "Passwords do not match"
    
    # Create user
    user_id, error = create_user(email, password)
    
    if user_id:
        # Auto-login after signup
        st.session_state[USER_ID_KEY] = user_id
        st.session_state[USER_EMAIL_KEY] = email.lower().strip()
        
        token = sign_token(user_id)
        st.session_state[AUTH_TOKEN_KEY] = token
        
        return True, ""
    else:
        return False, error


def logout():
    """Log out the current user."""
    init_session()
    st.session_state[USER_ID_KEY] = None
    st.session_state[USER_EMAIL_KEY] = None
    st.session_state[AUTH_TOKEN_KEY] = None


def require_login():
    """
    Require login to access a page.
    If not logged in, shows login form and stops execution.
    """
    if not is_logged_in():
        show_login_page()
        st.stop()


def show_login_page():
    """Display the login page."""
    st.set_page_config(page_title="Login - Job Tracker", page_icon="🔐", layout="centered")
    
    # Custom CSS
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
        html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
        .stApp { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
        h1, h2, h3 { color: #e94560 !important; }
        .stButton > button {
            background: linear-gradient(90deg, #e94560, #533483);
            color: white; border: none; border-radius: 8px;
            padding: 0.5rem 1.5rem; font-weight: 500;
            width: 100%;
        }
        .auth-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            border: 1px solid rgba(233, 69, 96, 0.3);
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🔐 Job Application Tracker")
    
    # Tab selection
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            st.subheader("Welcome Back")
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            
            submitted = st.form_submit_button("Login", use_container_width=True)
            
            if submitted:
                if not email or not password:
                    st.error("Please fill in all fields")
                else:
                    success, error = login(email, password)
                    if success:
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(error)
    
    with tab2:
        with st.form("signup_form"):
            st.subheader("Create Account")
            new_email = st.text_input("Email", placeholder="you@example.com", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_password",
                                          help="Minimum 4 characters")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            submitted = st.form_submit_button("Sign Up", use_container_width=True)
            
            if submitted:
                if not new_email or not new_password or not confirm_password:
                    st.error("Please fill in all fields")
                else:
                    success, error = signup(new_email, new_password, confirm_password)
                    if success:
                        st.success("Account created! Redirecting...")
                        st.rerun()
                    else:
                        st.error(error)


def show_user_sidebar():
    """Show current user info and logout in sidebar."""
    if is_logged_in():
        with st.sidebar:
            st.markdown("---")
            email = get_current_user_email()
            st.markdown(f"👤 **{email}**")
            if st.button("🚪 Logout", use_container_width=True):
                logout()
                st.rerun()
