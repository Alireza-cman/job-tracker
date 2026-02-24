"""
CSV export functionality for Job Application Tracker
"""
import csv
import io
from typing import List, Dict, Any

from .database import export_to_dict


def export_applications_csv() -> str:
    """Export all applications to CSV string."""
    data = export_to_dict()
    
    if not data:
        return ""
    
    output = io.StringIO()
    
    # Define column order for better readability
    fieldnames = [
        "id", "company", "title", "status", "location", 
        "salary_range", "job_type", "description", "requirements",
        "url", "job_id", "notes", "created_at", "updated_at"
    ]
    
    # Only include columns that exist in data
    available_fields = [f for f in fieldnames if f in data[0]]
    
    writer = csv.DictWriter(
        output, 
        fieldnames=available_fields, 
        extrasaction='ignore',
        quoting=csv.QUOTE_MINIMAL
    )
    writer.writeheader()
    writer.writerows(data)
    
    return output.getvalue()


def get_csv_bytes() -> bytes:
    """Get CSV as bytes for download."""
    csv_string = export_applications_csv()
    return csv_string.encode('utf-8')
