"""
Applications List Page - View, filter, and export job applications
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from core.session import require_login, show_user_sidebar, get_current_user_id
from backend.models import ApplicationStatus
from backend.database import get_all_applications, get_stats, update_application
from backend.export import get_csv_bytes

st.set_page_config(page_title="Applications", page_icon="📋", layout="wide")

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
    .stat-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(233, 69, 96, 0.3);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }
    .stat-number { font-size: 2rem; font-weight: 700; color: #e94560; }
    .stat-label { font-size: 0.9rem; color: #aaa; }
</style>
""", unsafe_allow_html=True)

# Show user info in sidebar
show_user_sidebar()

# Get current user
user_id = get_current_user_id()

st.title("📋 Applications")

# Stats row (user-scoped)
stats = get_stats(user_id)

if stats["total"] > 0:
    cols = st.columns(6)
    
    stat_items = [
        ("Total", stats["total"]),
        ("Saved", stats.get("Saved", 0)),
        ("Applied", stats.get("Applied", 0)),
        ("Interviewing", stats.get("Interviewing", 0)),
        ("Offers", stats.get("Offer", 0)),
        ("Rejected", stats.get("Rejected", 0)),
    ]
    
    for col, (label, value) in zip(cols, stat_items):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{value}</div>
                <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

# Filters
st.subheader("🔍 Filters")

col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

with col1:
    status_filter = st.multiselect(
        "Status",
        options=[s.value for s in ApplicationStatus],
        default=[],
        placeholder="All statuses",
    )

with col2:
    company_search = st.text_input(
        "Company",
        placeholder="Search company...",
    )

with col3:
    keyword_search = st.text_input(
        "Keyword",
        placeholder="Search title, description...",
    )

with col4:
    st.markdown("<br>", unsafe_allow_html=True)
    clear_filters = st.button("Clear", use_container_width=True)

if clear_filters:
    st.rerun()

# Get filtered applications (user-scoped)
status_enum_filter = [ApplicationStatus(s) for s in status_filter] if status_filter else None

applications = get_all_applications(
    user_id=user_id,
    status_filter=status_enum_filter,
    company_search=company_search if company_search else None,
    keyword_search=keyword_search if keyword_search else None,
)

# Export button
st.markdown("---")

col1, col2 = st.columns([1, 5])
with col1:
    if applications:
        csv_data = get_csv_bytes(user_id)  # User-scoped export
        st.download_button(
            label="📥 Export CSV",
            data=csv_data,
            file_name=f"job_applications_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

# Applications table
st.subheader(f"📊 Applications ({len(applications)})")

if not applications:
    st.info("No applications found. Add your first application from the 'New Application' page!")
else:
    # Convert to dataframe for display
    df_data = []
    for app in applications:
        df_data.append({
            "ID": app.id,
            "Company": app.company,
            "Title": app.title,
            "Status": app.status.value,
            "Location": app.location or "-",
            "Salary": app.salary_range or "-",
            "Type": app.job_type or "-",
            "Applied": app.created_at.strftime("%Y-%m-%d"),
            "Updated": app.updated_at.strftime("%Y-%m-%d"),
        })
    
    df = pd.DataFrame(df_data)
    
    # Color-coded status
    def status_color(status):
        colors = {
            "Saved": "🔵",
            "Applied": "🟡",
            "Recruiter Screen": "🟠",
            "Interviewing": "🟣",
            "Offer": "🟢",
            "Rejected": "🔴",
            "Ghosted": "👻",
            "Archived": "⚫",
        }
        return f"{colors.get(status, '')} {status}"
    
    df["Status"] = df["Status"].apply(status_color)
    
    # Display table with selection
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Company": st.column_config.TextColumn("Company", width="medium"),
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Status": st.column_config.TextColumn("Status", width="medium"),
            "Location": st.column_config.TextColumn("Location", width="small"),
            "Salary": st.column_config.TextColumn("Salary", width="small"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Applied": st.column_config.TextColumn("Applied", width="small"),
            "Updated": st.column_config.TextColumn("Updated", width="small"),
        },
    )
    
    # Quick view section
    st.markdown("---")
    st.subheader("👁️ Quick View")
    
    # Select application to view
    app_ids = [app.id for app in applications]
    selected_id = st.selectbox(
        "Select application to view:",
        options=app_ids,
        format_func=lambda x: f"#{x} - {next(a.company for a in applications if a.id == x)} - {next(a.title for a in applications if a.id == x)}",
    )
    
    if selected_id:
        selected_app = next(a for a in applications if a.id == selected_id)
        
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            st.markdown(f"**Company:** {selected_app.company}")
            st.markdown(f"**Title:** {selected_app.title}")
            st.markdown(f"**Location:** {selected_app.location or 'Not specified'}")
            st.markdown(f"**Salary:** {selected_app.salary_range or 'Not specified'}")
        
        with col2:
            st.markdown(f"**Type:** {selected_app.job_type or 'Not specified'}")
            if selected_app.url:
                st.markdown(f"**URL:** [{selected_app.url[:50]}...]({selected_app.url})")
        
        with col3:
            # Inline status update
            st.markdown("**Update Status:**")
            current_status_idx = [s.value for s in ApplicationStatus].index(selected_app.status.value)
            new_status = st.selectbox(
                "Status",
                options=[s.value for s in ApplicationStatus],
                index=current_status_idx,
                key=f"status_{selected_id}",
                label_visibility="collapsed",
            )
            
            if new_status != selected_app.status.value:
                if st.button("💾 Save Status", key=f"save_{selected_id}", use_container_width=True):
                    update_application(user_id, selected_id, status=ApplicationStatus(new_status))
                    st.success(f"Status updated to {new_status}!")
                    st.rerun()
        
        st.markdown("**Description:**")
        st.markdown(selected_app.description)
        
        if selected_app.requirements:
            st.markdown("**Requirements:**")
            for req in selected_app.requirements:
                st.markdown(f"- {req}")
        
        # Link to full details
        st.markdown(f"[View full details →](/details?id={selected_id})")
