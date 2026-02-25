"""
LangGraph pipeline nodes for job extraction
"""
import os
import re
import hashlib
import unicodedata
from typing import Dict, Any

import httpx
import trafilatura
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .models import (
    PipelineState, 
    InputMode, 
    JobApplication, 
    FetchError
)
from .database import check_fingerprint


# Node 1: Route input based on mode
def route_input(state: Dict[str, Any]) -> Dict[str, Any]:
    """Determine processing path based on input mode."""
    input_mode = state.get("input_mode")
    
    # Handle both enum and string comparison
    is_url_mode = (input_mode == InputMode.URL or 
                   input_mode == "url" or 
                   str(input_mode).lower() == "url" or
                   (hasattr(input_mode, 'value') and input_mode.value == "url"))
    
    if is_url_mode:
        return {"input_mode": "url"}  # Use string for consistent state
    else:
        # For text mode, set fetched_text directly from input
        return {
            "input_mode": "text",
            "fetched_text": state.get("input_text", ""),
        }


# Node 2: Fetch URL content
def fetch_url(state: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch and extract text from URL using httpx and trafilatura."""
    url = state.get("input_url")
    
    print(f"[fetch_url] Starting fetch for URL: {url}")  # Debug
    
    if not url:
        print("[fetch_url] No URL provided in state")  # Debug
        return {"fetch_error": FetchError(message="No URL provided")}
    
    try:
        # Fetch with realistic headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        print(f"[fetch_url] Fetching with httpx...")  # Debug
        
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            response = client.get(url, headers=headers)
        
        print(f"[fetch_url] Response status: {response.status_code}")  # Debug
        
        # Check for error status codes
        if response.status_code in (401, 403):
            return {
                "fetch_error": FetchError(
                    code=response.status_code,
                    message=f"Access denied ({response.status_code}). Try pasting the job text instead.",
                    recoverable=True,
                )
            }
        
        if response.status_code == 429:
            return {
                "fetch_error": FetchError(
                    code=429,
                    message="Rate limited. Please try again later or paste the job text.",
                    recoverable=True,
                )
            }
        
        response.raise_for_status()
        
        html_content = response.text
        print(f"[fetch_url] HTML content length: {len(html_content)} chars")  # Debug
        
        # Extract readable text using trafilatura
        extracted = trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_recall=True,  # Get more content
        )
        
        print(f"[fetch_url] Extracted text length: {len(extracted) if extracted else 0} chars")  # Debug
        
        if not extracted or len(extracted.strip()) < 100:
            # Try fallback extraction
            print("[fetch_url] Primary extraction failed, trying fallback...")  # Debug
            extracted = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=False,
                include_formatting=True,
            )
            
            if not extracted or len(extracted.strip()) < 100:
                return {
                    "fetch_error": FetchError(
                        message="Could not extract enough text from page. The page may require JavaScript or login. Try pasting the job text instead.",
                        recoverable=True,
                    )
                }
        
        print(f"[fetch_url] Successfully extracted {len(extracted)} chars")  # Debug
        print(f"[fetch_url] First 500 chars: {extracted[:500]}")  # Debug
        
        return {"fetched_text": extracted, "fetch_error": None}
        
    except httpx.TimeoutException:
        print("[fetch_url] Request timed out")  # Debug
        return {
            "fetch_error": FetchError(
                message="Request timed out. Try pasting the job text instead.",
                recoverable=True,
            )
        }
    except httpx.HTTPStatusError as e:
        print(f"[fetch_url] HTTP error: {e.response.status_code}")  # Debug
        return {
            "fetch_error": FetchError(
                code=e.response.status_code,
                message=f"HTTP error {e.response.status_code}. Try pasting the job text instead.",
                recoverable=True,
            )
        }
    except Exception as e:
        print(f"[fetch_url] Exception: {str(e)}")  # Debug
        return {
            "fetch_error": FetchError(
                message=f"Failed to fetch URL: {str(e)}",
                recoverable=True,
            )
        }


# Node 3: Clean and normalize text
def clean_text(state: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and normalize the extracted text."""
    fetched = state.get("fetched_text")
    input_txt = state.get("input_text", "")
    
    print(f"[clean_text] fetched_text present: {bool(fetched)}, length: {len(fetched) if fetched else 0}")  # Debug
    print(f"[clean_text] input_text present: {bool(input_txt)}, length: {len(input_txt) if input_txt else 0}")  # Debug
    
    text = fetched or input_txt
    
    if not text:
        print("[clean_text] No text to process!")  # Debug
        return {"error": "No text to process"}
    
    # Normalize unicode
    text = unicodedata.normalize("NFKC", text)
    
    # Remove excessive whitespace while preserving paragraphs
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r' +\n', '\n', text)
    
    # Remove common noise patterns
    text = re.sub(r'Share this job.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Apply now.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Similar jobs.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
    
    # Truncate if too long (keep first ~8000 chars for LLM context)
    if len(text) > 8000:
        text = text[:8000] + "\n\n[Text truncated...]"
    
    text = text.strip()
    
    print(f"[clean_text] Cleaned text length: {len(text)} chars")  # Debug
    
    return {"cleaned_text": text}


# Node 4: LLM extraction
def llm_extract(state: Dict[str, Any]) -> Dict[str, Any]:
    """Use OpenAI to extract structured job data."""
    text = state.get("cleaned_text", "")
    url = state.get("input_url")
    
    print(f"[llm_extract] Received text length: {len(text)} chars")  # Debug
    print(f"[llm_extract] URL: {url}")  # Debug
    
    if not text:
        print("[llm_extract] No cleaned text!")  # Debug
        return {"error": "No cleaned text to extract from"}
    
    print(f"[llm_extract] Text preview: {text[:500]}...")  # Debug
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[llm_extract] OPENAI_API_KEY not set!")  # Debug
        return {"error": "OPENAI_API_KEY not set in environment"}
    
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=api_key,
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a job posting parser. Extract structured information from job postings.
Return a JSON object with these fields:
- company: Company name (required)
- title: Job title (required)
- location: Job location (city/state/country or "Remote")
- salary_range: Salary range if mentioned (e.g., "$120,000 - $150,000")
- job_type: Employment type (Full-time, Part-time, Contract, Internship)
- description: A 2-3 sentence summary of the role
- requirements: Array of key requirements/qualifications (max 5 items)
- job_id: Job ID/reference number if present

Be concise. If information is not found, use null."""),
        ("human", "Extract job information from this posting:\n\n{text}")
    ])
    
    try:
        print("[llm_extract] Calling OpenAI API...")  # Debug
        chain = prompt | llm.with_structured_output(JobApplication)
        result = chain.invoke({"text": text})
        
        print(f"[llm_extract] Extraction result: {result}")  # Debug
        
        # Add URL if provided
        if url and result:
            result.url = url
        
        return {"extracted": result}
        
    except Exception as e:
        print(f"[llm_extract] Error: {str(e)}")  # Debug
        return {"error": f"LLM extraction failed: {str(e)}"}


# Node 5: Normalize and validate
def normalize_validate(state: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize and validate extracted data."""
    extracted = state.get("extracted")
    
    if not extracted:
        return {"error": "No extracted data to validate"}
    
    # Ensure required fields have values
    if not extracted.company:
        extracted.company = "Unknown Company"
    if not extracted.title:
        extracted.title = "Unknown Position"
    if not extracted.description:
        extracted.description = "No description available"
    
    # Normalize company name (basic cleaning)
    extracted.company = extracted.company.strip()
    extracted.title = extracted.title.strip()
    
    # Ensure requirements is a list
    if extracted.requirements and not isinstance(extracted.requirements, list):
        extracted.requirements = [str(extracted.requirements)]
    
    return {"extracted": extracted}


# Node 6: Deduplication check
def dedupe_check(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate fingerprint and check for duplicates (user-scoped)."""
    extracted = state.get("extracted")
    user_id = state.get("user_id")
    
    if not extracted:
        return {"error": "No data to check for duplicates"}
    
    # Generate fingerprint from company + title + (job_id or url)
    components = [
        extracted.company.lower().strip(),
        extracted.title.lower().strip(),
    ]
    
    # Prefer job_id, fall back to url
    if extracted.job_id:
        components.append(extracted.job_id.lower().strip())
    elif extracted.url:
        components.append(extracted.url.lower().strip())
    
    fingerprint_input = "|".join(components)
    fingerprint = hashlib.sha256(fingerprint_input.encode()).hexdigest()[:32]
    
    # Check database for existing (user-scoped if user_id provided)
    existing_id = None
    if user_id:
        existing_id = check_fingerprint(user_id, fingerprint)
    
    return {
        "fingerprint": fingerprint,
        "is_duplicate": existing_id is not None,
        "existing_id": existing_id,
    }


# Routing function for conditional edges
def should_fetch(state: Dict[str, Any]) -> str:
    """Determine if we need to fetch URL or skip to cleaning."""
    input_mode = state.get("input_mode")
    
    print(f"[should_fetch] input_mode = {input_mode}, type = {type(input_mode)}")  # Debug
    
    # Handle both enum and string comparison
    is_url_mode = (input_mode == InputMode.URL or 
                   input_mode == "url" or 
                   str(input_mode).lower() == "url" or
                   (hasattr(input_mode, 'value') and input_mode.value == "url"))
    
    print(f"[should_fetch] is_url_mode = {is_url_mode}")  # Debug
    
    if is_url_mode:
        return "fetch"
    return "clean"


def check_fetch_error(state: Dict[str, Any]) -> str:
    """Check if fetch had an error."""
    if state.get("fetch_error"):
        return "error"
    return "continue"
