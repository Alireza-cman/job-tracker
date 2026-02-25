"""
SQLite database operations for Job Application Tracker.
All operations are user-scoped for data isolation.
"""
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from .models import JobApplication, StoredApplication, ApplicationStatus

DB_PATH = Path(__file__).parent.parent / "data" / "applications.db"

# Default admin user ID for migration
DEFAULT_ADMIN_ID = "admin-default-00000000"
DEFAULT_ADMIN_EMAIL = "admin@jobtracker.local"


def get_connection() -> sqlite3.Connection:
    """Get database connection, creating DB and tables if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_tables(conn)
    _run_migrations(conn)
    return conn


def _init_tables(conn: sqlite3.Connection) -> None:
    """Initialize database tables."""
    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    # Check if applications table exists
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='applications'"
    )
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        # Create new table with user_id
        conn.execute("""
            CREATE TABLE applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
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
                fingerprint TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, fingerprint)
            )
        """)
    
    conn.commit()


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Run database migrations for existing data."""
    # Check if applications table exists
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='applications'"
    )
    if cursor.fetchone() is None:
        return  # No table yet, nothing to migrate
    
    # Check if user_id column exists in applications
    cursor = conn.execute("PRAGMA table_info(applications)")
    columns = [row["name"] for row in cursor.fetchall()]
    
    if "user_id" not in columns:
        # Migration: Add user_id column
        print("[Migration] Adding user_id column to applications table...")
        
        # Create default admin user if not exists
        _ensure_default_admin(conn)
        
        # Add user_id column with default value
        conn.execute(f"""
            ALTER TABLE applications ADD COLUMN user_id TEXT DEFAULT '{DEFAULT_ADMIN_ID}'
        """)
        
        # Update existing rows to have the default admin user
        conn.execute(f"""
            UPDATE applications SET user_id = '{DEFAULT_ADMIN_ID}' WHERE user_id IS NULL OR user_id = ''
        """)
        
        print(f"[Migration] Assigned existing applications to default admin user: {DEFAULT_ADMIN_EMAIL}")
        conn.commit()
    
    # Create indexes (safe to run after migration)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_fingerprint ON applications(user_id, fingerprint)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_status ON applications(user_id, status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_company ON applications(user_id, company)
    """)
    conn.commit()


def _ensure_default_admin(conn: sqlite3.Connection) -> None:
    """Ensure default admin user exists for migration."""
    from core.auth import hash_password
    
    cursor = conn.execute("SELECT 1 FROM users WHERE id = ?", (DEFAULT_ADMIN_ID,))
    if cursor.fetchone() is None:
        # Create default admin with a random password (must be changed)
        temp_password = str(uuid.uuid4())[:12]
        password_hash = hash_password(temp_password)
        
        conn.execute(
            """
            INSERT INTO users (id, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (DEFAULT_ADMIN_ID, DEFAULT_ADMIN_EMAIL, password_hash, datetime.utcnow().isoformat())
        )
        print(f"[Migration] Created default admin user: {DEFAULT_ADMIN_EMAIL}")
        print(f"[Migration] IMPORTANT: Change the admin password after login!")


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
    user_id: str,
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
            user_id, company, title, location, salary_range, job_type,
            description, requirements, raw_text, url, job_id,
            status, fingerprint
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
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


def get_application(user_id: str, app_id: int) -> Optional[StoredApplication]:
    """Get a single application by ID (user-scoped)."""
    conn = get_connection()
    cursor = conn.execute(
        "SELECT * FROM applications WHERE id = ? AND user_id = ?",
        (app_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return _row_to_stored(row)
    return None


def get_all_applications(
    user_id: str,
    status_filter: Optional[List[ApplicationStatus]] = None,
    company_search: Optional[str] = None,
    keyword_search: Optional[str] = None,
) -> List[StoredApplication]:
    """Get all applications for a user with optional filters."""
    conn = get_connection()
    
    query = "SELECT * FROM applications WHERE user_id = ?"
    params: List[Any] = [user_id]
    
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
    user_id: str,
    app_id: int,
    status: Optional[ApplicationStatus] = None,
    notes: Optional[str] = None,
    **kwargs: Any,
) -> bool:
    """Update an application (user-scoped). Returns True if successful."""
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
    
    params.extend([app_id, user_id])
    query = f"UPDATE applications SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
    
    cursor = conn.execute(query, params)
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def delete_application(user_id: str, app_id: int) -> bool:
    """Delete an application (user-scoped). Returns True if successful."""
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM applications WHERE id = ? AND user_id = ?",
        (app_id, user_id)
    )
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def check_fingerprint(user_id: str, fingerprint: str) -> Optional[int]:
    """Check if fingerprint exists for user. Returns app ID if found."""
    conn = get_connection()
    cursor = conn.execute(
        "SELECT id FROM applications WHERE fingerprint = ? AND user_id = ?",
        (fingerprint, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return row["id"]
    return None


def get_stats(user_id: str) -> Dict[str, int]:
    """Get application statistics by status for a user."""
    conn = get_connection()
    cursor = conn.execute(
        "SELECT status, COUNT(*) as count FROM applications WHERE user_id = ? GROUP BY status",
        (user_id,)
    )
    rows = cursor.fetchall()
    
    # Get total
    total_cursor = conn.execute(
        "SELECT COUNT(*) as total FROM applications WHERE user_id = ?",
        (user_id,)
    )
    total = total_cursor.fetchone()["total"]
    conn.close()
    
    stats = {"total": total}
    for row in rows:
        stats[row["status"]] = row["count"]
    
    return stats


def export_to_dict(user_id: str) -> List[Dict[str, Any]]:
    """Export all applications for a user as list of dictionaries."""
    conn = get_connection()
    cursor = conn.execute(
        "SELECT * FROM applications WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        d = dict(row)
        # Remove user_id from export for privacy
        d.pop("user_id", None)
        # Flatten requirements for CSV
        if d.get("requirements"):
            try:
                reqs = json.loads(d["requirements"])
                d["requirements"] = "; ".join(reqs) if reqs else ""
            except json.JSONDecodeError:
                d["requirements"] = ""
        result.append(d)
    
    return result
