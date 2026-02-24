"""
SQLite database operations for Job Application Tracker
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from .models import JobApplication, StoredApplication, ApplicationStatus

DB_PATH = Path(__file__).parent.parent / "data" / "applications.db"


def get_connection() -> sqlite3.Connection:
    """Get database connection, creating DB and tables if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_tables(conn)
    return conn


def _init_tables(conn: sqlite3.Connection) -> None:
    """Initialize database tables."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT,
            salary_range TEXT,
            job_type TEXT,
            description TEXT NOT NULL,
            requirements TEXT,
            raw_text TEXT,
            url TEXT,
            job_id TEXT,
            status TEXT DEFAULT 'Saved',
            notes TEXT,
            fingerprint TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_fingerprint ON applications(fingerprint)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_status ON applications(status)
    """)
    conn.commit()


def _row_to_stored(row: sqlite3.Row) -> StoredApplication:
    """Convert database row to StoredApplication model."""
    requirements = None
    if row["requirements"]:
        try:
            requirements = json.loads(row["requirements"])
        except json.JSONDecodeError:
            requirements = None
    
    return StoredApplication(
        id=row["id"],
        company=row["company"],
        title=row["title"],
        location=row["location"],
        salary_range=row["salary_range"],
        job_type=row["job_type"],
        description=row["description"],
        requirements=requirements,
        raw_text=row["raw_text"],
        url=row["url"],
        job_id=row["job_id"],
        status=ApplicationStatus(row["status"]),
        notes=row["notes"],
        fingerprint=row["fingerprint"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
    )


def save_application(
    application: JobApplication,
    raw_text: str,
    fingerprint: str,
    status: ApplicationStatus = ApplicationStatus.SAVED,
) -> int:
    """Save a new application to the database. Returns the new ID."""
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO applications (
            company, title, location, salary_range, job_type,
            description, requirements, raw_text, url, job_id,
            status, fingerprint
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            application.company,
            application.title,
            application.location,
            application.salary_range,
            application.job_type,
            application.description,
            json.dumps(application.requirements) if application.requirements else None,
            raw_text,
            application.url,
            application.job_id,
            status.value,
            fingerprint,
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_application(app_id: int) -> Optional[StoredApplication]:
    """Get a single application by ID."""
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return _row_to_stored(row)
    return None


def get_all_applications(
    status_filter: Optional[List[ApplicationStatus]] = None,
    company_search: Optional[str] = None,
    keyword_search: Optional[str] = None,
) -> List[StoredApplication]:
    """Get all applications with optional filters."""
    conn = get_connection()
    
    query = "SELECT * FROM applications WHERE 1=1"
    params: List[Any] = []
    
    if status_filter:
        placeholders = ",".join("?" * len(status_filter))
        query += f" AND status IN ({placeholders})"
        params.extend([s.value for s in status_filter])
    
    if company_search:
        query += " AND company LIKE ?"
        params.append(f"%{company_search}%")
    
    if keyword_search:
        query += " AND (title LIKE ? OR description LIKE ? OR company LIKE ?)"
        params.extend([f"%{keyword_search}%"] * 3)
    
    query += " ORDER BY updated_at DESC"
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [_row_to_stored(row) for row in rows]


def update_application(
    app_id: int,
    status: Optional[ApplicationStatus] = None,
    notes: Optional[str] = None,
    **kwargs: Any,
) -> bool:
    """Update an application. Returns True if successful."""
    conn = get_connection()
    
    updates = ["updated_at = CURRENT_TIMESTAMP"]
    params: List[Any] = []
    
    if status is not None:
        updates.append("status = ?")
        params.append(status.value)
    
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    
    # Allow updating other fields
    for key, value in kwargs.items():
        if key in ("company", "title", "location", "salary_range", "job_type", "description"):
            updates.append(f"{key} = ?")
            params.append(value)
    
    if len(params) == 0:
        conn.close()
        return False
    
    params.append(app_id)
    query = f"UPDATE applications SET {', '.join(updates)} WHERE id = ?"
    
    cursor = conn.execute(query, params)
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def delete_application(app_id: int) -> bool:
    """Delete an application. Returns True if successful."""
    conn = get_connection()
    cursor = conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def check_fingerprint(fingerprint: str) -> Optional[int]:
    """Check if fingerprint exists. Returns app ID if found, None otherwise."""
    conn = get_connection()
    cursor = conn.execute(
        "SELECT id FROM applications WHERE fingerprint = ?",
        (fingerprint,),
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return row["id"]
    return None


def get_stats() -> Dict[str, int]:
    """Get application statistics by status."""
    conn = get_connection()
    cursor = conn.execute(
        "SELECT status, COUNT(*) as count FROM applications GROUP BY status"
    )
    rows = cursor.fetchall()
    
    # Get total
    total_cursor = conn.execute("SELECT COUNT(*) as total FROM applications")
    total = total_cursor.fetchone()["total"]
    conn.close()
    
    stats = {"total": total}
    for row in rows:
        stats[row["status"]] = row["count"]
    
    return stats


def export_to_dict() -> List[Dict[str, Any]]:
    """Export all applications as list of dictionaries for CSV export."""
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM applications ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        d = dict(row)
        # Flatten requirements for CSV
        if d.get("requirements"):
            try:
                reqs = json.loads(d["requirements"])
                d["requirements"] = "; ".join(reqs) if reqs else ""
            except json.JSONDecodeError:
                d["requirements"] = ""
        result.append(d)
    
    return result
