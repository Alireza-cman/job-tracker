"""
Pydantic models for Job Application Tracker
"""
from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

import os
from dotenv import load_dotenv
load_dotenv()

class ApplicationStatus(str, Enum):
    """Status of a job application"""
    SAVED = "Saved"
    APPLIED = "Applied"
    RECRUITER_SCREEN = "Recruiter Screen"
    INTERVIEWING = "Interviewing"
    OFFER = "Offer"
    REJECTED = "Rejected"
    GHOSTED = "Ghosted"
    ARCHIVED = "Archived"


class JobApplication(BaseModel):
    """Extracted job application data from LLM"""
    company: str = Field(description="Company name")
    title: str = Field(description="Job title")
    location: Optional[str] = Field(default=None, description="Job location (city, state, remote, etc.)")
    salary_range: Optional[str] = Field(default=None, description="Salary range if mentioned")
    job_type: Optional[str] = Field(default=None, description="Full-time, Part-time, Contract, etc.")
    description: str = Field(description="Brief job description/summary")
    requirements: Optional[List[str]] = Field(default=None, description="Key requirements or qualifications")
    url: Optional[str] = Field(default=None, description="Original job posting URL")
    job_id: Optional[str] = Field(default=None, description="Job ID if present in posting")


class StoredApplication(BaseModel):
    """Full application record stored in database"""
    id: int
    company: str
    title: str
    location: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None
    description: str
    requirements: Optional[List[str]] = None
    raw_text: Optional[str] = None
    url: Optional[str] = None
    job_id: Optional[str] = None
    status: ApplicationStatus = ApplicationStatus.SAVED
    notes: Optional[str] = None
    fingerprint: str
    created_at: datetime
    updated_at: datetime


class InputMode(str, Enum):
    """Input mode for job application"""
    URL = "url"
    TEXT = "text"


class FetchError(BaseModel):
    """Error details when URL fetch fails"""
    code: Optional[int] = None
    message: str
    recoverable: bool = True


class PipelineState(BaseModel):
    """State passed through LangGraph pipeline"""
    # Input
    input_mode: InputMode
    input_url: Optional[str] = None
    input_text: Optional[str] = None
    
    # Processing
    fetched_text: Optional[str] = None
    cleaned_text: Optional[str] = None
    fetch_error: Optional[FetchError] = None
    
    # Output
    extracted: Optional[JobApplication] = None
    fingerprint: Optional[str] = None
    is_duplicate: bool = False
    existing_id: Optional[int] = None
    
    # Meta
    error: Optional[str] = None
