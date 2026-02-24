"""
Job Application Tracker - Main Streamlit Entry Point
"""
import streamlit as st

st.set_page_config(
    page_title="Job Application Tracker",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a polished look
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    
    h1, h2, h3 {
        color: #e94560 !important;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #e94560, #533483);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(233, 69, 96, 0.4);
    }
    
    .stSelectbox, .stTextInput, .stTextArea {
        border-radius: 8px;
    }
    
    div[data-testid="stSidebar"] {
        background: rgba(15, 52, 96, 0.8);
        backdrop-filter: blur(10px);
    }
    
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(233, 69, 96, 0.3);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("💼 Job Application Tracker")

st.markdown("""
Welcome to your personal job application tracker! This tool helps you:

- **Extract** job details from URLs or pasted text using AI
- **Organize** all your applications in one place
- **Track** your application status through the hiring pipeline
- **Export** your data for analysis

### Get Started

👈 Use the sidebar to navigate between pages:

1. **New Application** - Add a new job application
2. **Applications** - View and filter all your applications  
3. **Details** - View and edit individual applications
""")

# Show quick stats if database exists
from backend.database import get_stats

stats = get_stats()
if stats["total"] > 0:
    st.markdown("---")
    st.subheader("📊 Quick Stats")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Applications", stats["total"])
    with col2:
        st.metric("Applied", stats.get("Applied", 0))
    with col3:
        st.metric("Interviewing", stats.get("Interviewing", 0))
    with col4:
        st.metric("Offers", stats.get("Offer", 0))
