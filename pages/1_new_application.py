"""
New Application Page - Add job applications via URL or pasted text
"""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from backend.models import InputMode, ApplicationStatus, JobApplication
from backend.pipeline import run_extraction
from backend.database import save_application

st.set_page_config(page_title="New Application", page_icon="➕", layout="wide")

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
    .success-box {
        background: rgba(39, 174, 96, 0.2);
        border: 1px solid #27ae60;
        border-radius: 8px; padding: 1rem; margin: 1rem 0;
    }
    .warning-box {
        background: rgba(241, 196, 15, 0.2);
        border: 1px solid #f1c40f;
        border-radius: 8px; padding: 1rem; margin: 1rem 0;
    }
    .error-box {
        background: rgba(231, 76, 60, 0.2);
        border: 1px solid #e74c3c;
        border-radius: 8px; padding: 1rem; margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("➕ New Application")
st.markdown("Add a job application by providing a URL or pasting the job description text.")

# Initialize session state
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = None
if "raw_text" not in st.session_state:
    st.session_state.raw_text = None
if "fingerprint" not in st.session_state:
    st.session_state.fingerprint = None
if "fetch_failed" not in st.session_state:
    st.session_state.fetch_failed = False
if "is_duplicate" not in st.session_state:
    st.session_state.is_duplicate = False
if "existing_id" not in st.session_state:
    st.session_state.existing_id = None

# Input section
st.subheader("📥 Input")

input_mode = st.radio(
    "Choose input method:",
    options=["URL", "Paste Text"],
    horizontal=True,
    index=1 if st.session_state.fetch_failed else 0,
)

url_input = ""
text_input = ""

if input_mode == "URL":
    url_input = st.text_input(
        "Job posting URL:",
        placeholder="https://example.com/jobs/software-engineer",
    )
    if st.session_state.fetch_failed:
        st.markdown(
            '<div class="warning-box">⚠️ URL fetch failed. You can paste the job text below instead.</div>',
            unsafe_allow_html=True,
        )
else:
    text_input = st.text_area(
        "Paste job description:",
        height=200,
        placeholder="Paste the full job posting text here...",
    )

# Extract button
col1, col2 = st.columns([1, 4])
with col1:
    extract_clicked = st.button("🔍 Extract", type="primary", use_container_width=True)

if extract_clicked:
    # Validate input
    if input_mode == "URL" and not url_input:
        st.error("Please enter a URL")
    elif input_mode == "Paste Text" and not text_input:
        st.error("Please paste job description text")
    else:
        # Run extraction pipeline
        with st.spinner("Extracting job information..."):
            mode = InputMode.URL if input_mode == "URL" else InputMode.TEXT
            result = run_extraction(
                input_mode=mode,
                input_url=url_input if mode == InputMode.URL else None,
                input_text=text_input if mode == InputMode.TEXT else None,
            )
        
        # Check for errors
        if result.get("fetch_error"):
            error = result["fetch_error"]
            st.session_state.fetch_failed = True
            st.markdown(
                f'<div class="error-box">❌ {error.message}</div>',
                unsafe_allow_html=True,
            )
            st.rerun()
        elif result.get("error"):
            st.error(f"Extraction failed: {result['error']}")
        elif result.get("extracted"):
            st.session_state.extracted_data = result["extracted"]
            st.session_state.raw_text = result.get("cleaned_text", text_input or "")
            st.session_state.fingerprint = result.get("fingerprint")
            st.session_state.is_duplicate = result.get("is_duplicate", False)
            st.session_state.existing_id = result.get("existing_id")
            st.session_state.fetch_failed = False
            
            if st.session_state.is_duplicate:
                st.markdown(
                    f'<div class="warning-box">⚠️ This job may already exist in your tracker (ID: {st.session_state.existing_id})</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.success("✅ Job information extracted successfully!")

# Show edit form if we have extracted data
if st.session_state.extracted_data:
    st.markdown("---")
    st.subheader("📝 Review & Edit")
    
    data = st.session_state.extracted_data
    
    col1, col2 = st.columns(2)
    
    with col1:
        company = st.text_input("Company *", value=data.company or "")
        title = st.text_input("Job Title *", value=data.title or "")
        location = st.text_input("Location", value=data.location or "")
        salary = st.text_input("Salary Range", value=data.salary_range or "")
    
    with col2:
        job_type = st.selectbox(
            "Job Type",
            options=["", "Full-time", "Part-time", "Contract", "Internship", "Freelance"],
            index=["", "Full-time", "Part-time", "Contract", "Internship", "Freelance"].index(data.job_type) 
                if data.job_type in ["", "Full-time", "Part-time", "Contract", "Internship", "Freelance"] else 0,
        )
        job_id = st.text_input("Job ID", value=data.job_id or "")
        url = st.text_input("URL", value=data.url or url_input or "")
        status = st.selectbox(
            "Status",
            options=[s.value for s in ApplicationStatus],
            index=0,
        )
    
    description = st.text_area(
        "Description",
        value=data.description or "",
        height=100,
    )
    
    # Requirements as editable list
    requirements_text = st.text_area(
        "Requirements (one per line)",
        value="\n".join(data.requirements) if data.requirements else "",
        height=100,
    )
    
    # Save button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 3])
    
    with col1:
        save_clicked = st.button("💾 Save Application", type="primary", use_container_width=True)
    
    with col2:
        clear_clicked = st.button("🗑️ Clear", use_container_width=True)
    
    if clear_clicked:
        st.session_state.extracted_data = None
        st.session_state.raw_text = None
        st.session_state.fingerprint = None
        st.session_state.fetch_failed = False
        st.session_state.is_duplicate = False
        st.session_state.existing_id = None
        st.rerun()
    
    if save_clicked:
        # Validate required fields
        if not company or not title:
            st.error("Company and Job Title are required")
        else:
            # Build updated application
            requirements_list = [r.strip() for r in requirements_text.split("\n") if r.strip()]
            
            updated_app = JobApplication(
                company=company,
                title=title,
                location=location or None,
                salary_range=salary or None,
                job_type=job_type or None,
                description=description or "No description",
                requirements=requirements_list or None,
                url=url or None,
                job_id=job_id or None,
            )
            
            try:
                app_id = save_application(
                    application=updated_app,
                    raw_text=st.session_state.raw_text or "",
                    fingerprint=st.session_state.fingerprint or "",
                    status=ApplicationStatus(status),
                )
                
                st.markdown(
                    f'<div class="success-box">✅ Application saved successfully! (ID: {app_id})</div>',
                    unsafe_allow_html=True,
                )
                
                # Clear state for next entry
                st.session_state.extracted_data = None
                st.session_state.raw_text = None
                st.session_state.fingerprint = None
                st.session_state.is_duplicate = False
                st.session_state.existing_id = None
                
            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    st.error("This application already exists in your tracker!")
                else:
                    st.error(f"Failed to save: {str(e)}")
