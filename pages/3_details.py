"""
Details Page - View and edit individual job applications
"""
import streamlit as st

from core.session import require_login, show_user_sidebar, get_current_user_id
from backend.models import ApplicationStatus
from backend.database import get_application, get_all_applications, update_application, delete_application

st.set_page_config(page_title="Application Details", page_icon="📄", layout="wide")

# Require authentication
require_login()

# Apply consistent styling
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
    }
    .detail-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(233, 69, 96, 0.3);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background: rgba(39, 174, 96, 0.2);
        border: 1px solid #27ae60;
        border-radius: 8px; padding: 1rem; margin: 1rem 0;
    }
    .danger-btn button {
        background: linear-gradient(90deg, #e74c3c, #c0392b) !important;
    }
</style>
""", unsafe_allow_html=True)

# Show user info in sidebar
show_user_sidebar()

# Get current user
user_id = get_current_user_id()

st.title("📄 Application Details")

# Get all applications for current user
all_apps = get_all_applications(user_id)

if not all_apps:
    st.info("No applications found. Add your first application from the 'New Application' page!")
    st.stop()

# Application selector
app_options = {app.id: f"#{app.id} - {app.company} - {app.title}" for app in all_apps}

# Check for URL parameter
query_params = st.query_params
preselected_id = query_params.get("id")

if preselected_id:
    try:
        preselected_id = int(preselected_id)
        if preselected_id not in app_options:
            preselected_id = all_apps[0].id
    except (ValueError, TypeError):
        preselected_id = all_apps[0].id
else:
    preselected_id = all_apps[0].id

selected_id = st.selectbox(
    "Select Application:",
    options=list(app_options.keys()),
    format_func=lambda x: app_options[x],
    index=list(app_options.keys()).index(preselected_id) if preselected_id in app_options else 0,
)

# Get selected application (user-scoped)
app = get_application(user_id, selected_id)

if not app:
    st.error("Application not found!")
    st.stop()

# Status badge with color
status_colors = {
    "Saved": "🔵",
    "Applied": "🟡", 
    "Recruiter Screen": "🟠",
    "Interviewing": "🟣",
    "Offer": "🟢",
    "Rejected": "🔴",
    "Ghosted": "👻",
    "Archived": "⚫",
}

# Main info card
st.markdown("---")

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader(f"{app.title}")
    st.markdown(f"### {app.company}")

with col2:
    st.markdown(f"## {status_colors.get(app.status.value, '')} {app.status.value}")

# Details grid
st.markdown('<div class="detail-card">', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**📍 Location**")
    st.markdown(app.location or "Not specified")
    
    st.markdown("**💰 Salary**")
    st.markdown(app.salary_range or "Not specified")

with col2:
    st.markdown("**💼 Job Type**")
    st.markdown(app.job_type or "Not specified")
    
    st.markdown("**🔗 Job ID**")
    st.markdown(app.job_id or "Not specified")

with col3:
    st.markdown("**📅 Created**")
    st.markdown(app.created_at.strftime("%Y-%m-%d %H:%M"))
    
    st.markdown("**🔄 Updated**")
    st.markdown(app.updated_at.strftime("%Y-%m-%d %H:%M"))

st.markdown('</div>', unsafe_allow_html=True)

# URL
if app.url:
    st.markdown(f"**🌐 URL:** [{app.url}]({app.url})")

# Description
st.markdown("---")
st.subheader("📝 Description")
st.markdown(app.description)

# Requirements
if app.requirements:
    st.subheader("✅ Requirements")
    for req in app.requirements:
        st.markdown(f"- {req}")

# Raw text (collapsible)
if app.raw_text:
    with st.expander("📜 Raw Text (original posting)"):
        st.text(app.raw_text)

# Edit section
st.markdown("---")
st.subheader("✏️ Update Application")

col1, col2 = st.columns(2)

with col1:
    # Status update
    new_status = st.selectbox(
        "Update Status:",
        options=[s.value for s in ApplicationStatus],
        index=[s.value for s in ApplicationStatus].index(app.status.value),
    )

with col2:
    # Quick status buttons
    st.markdown("**Quick Status:**")
    quick_col1, quick_col2, quick_col3 = st.columns(3)
    
    with quick_col1:
        if st.button("✅ Applied", use_container_width=True):
            update_application(user_id, app.id, status=ApplicationStatus.APPLIED)
            st.rerun()
    
    with quick_col2:
        if st.button("🎤 Interview", use_container_width=True):
            update_application(user_id, app.id, status=ApplicationStatus.INTERVIEWING)
            st.rerun()
    
    with quick_col3:
        if st.button("❌ Rejected", use_container_width=True):
            update_application(user_id, app.id, status=ApplicationStatus.REJECTED)
            st.rerun()

# Notes
st.markdown("**Notes:**")
notes = st.text_area(
    "Notes",
    value=app.notes or "",
    height=150,
    label_visibility="collapsed",
    placeholder="Add notes about this application, interview feedback, follow-up reminders...",
)

# Save and Delete buttons
col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    if st.button("💾 Save Changes", type="primary", use_container_width=True):
        success = update_application(
            user_id,
            app.id,
            status=ApplicationStatus(new_status),
            notes=notes,
        )
        if success:
            st.markdown(
                '<div class="success-box">✅ Changes saved successfully!</div>',
                unsafe_allow_html=True,
            )
            st.rerun()
        else:
            st.error("Failed to save changes")

with col2:
    st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
    if st.button("🗑️ Delete", use_container_width=True):
        st.session_state.confirm_delete = True
    st.markdown('</div>', unsafe_allow_html=True)

# Confirm delete
if st.session_state.get("confirm_delete"):
    st.warning("⚠️ Are you sure you want to delete this application?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, delete", type="primary"):
            if delete_application(user_id, app.id):
                st.session_state.confirm_delete = False
                st.success("Application deleted!")
                st.rerun()
            else:
                st.error("Failed to delete")
    with col2:
        if st.button("Cancel"):
            st.session_state.confirm_delete = False
            st.rerun()

# Navigation
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.page_link("pages/1_new_application.py", label="➕ Add New Application")

with col2:
    st.page_link("pages/2_applications.py", label="📋 Back to List")
