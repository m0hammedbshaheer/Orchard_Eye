import os
import sys
import sqlite3
import hashlib
import secrets
import contextlib
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Form, File, UploadFile, Depends, Header, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BACKEND_DIR, ".env")
ACCESS_MANAGER_DIR = os.path.join(BACKEND_DIR, "Acess_manager")

# Load environment variables from backend/.env
load_dotenv(ENV_FILE)

if ACCESS_MANAGER_DIR not in sys.path:
    sys.path.insert(0, ACCESS_MANAGER_DIR)

from access_core import (  # noqa: E402
    approve_request as approve_api_request,
    register_device,
    reject_request as reject_api_request,
)

# Determine paths with safe defaults
BASE_DIR = os.path.dirname(BACKEND_DIR)
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "database", "traps.db")
DEFAULT_UPLOAD_ROOT = os.path.join(BASE_DIR, "database", "uploads")

DB_PATH = os.getenv("DB_PATH", DEFAULT_DB_PATH)
UPLOAD_ROOT = os.getenv("UPLOAD_ROOT", DEFAULT_UPLOAD_ROOT)

ADMIN_LOGIN_ID = os.getenv("ADMIN_LOGIN_ID")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

# Ensure required directories exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(UPLOAD_ROOT, exist_ok=True)


# Database Initialization Function
def init_db_tables():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS traps (
            trap_id TEXT PRIMARY KEY,
            api_key TEXT NOT NULL,
            district TEXT,
            village TEXT,
            latitude REAL,
            longitude REAL,
            install_date TEXT,
            last_seen TEXT,
            active INTEGER DEFAULT 1);
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS preprocessed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trap_id TEXT,
            image_path TEXT,
            timestamp TEXT,
            temperature REAL,
            humidity REAL,
            battery REAL,
            processing_status TEXT DEFAULT 'PENDING',
            FOREIGN KEY (trap_id) REFERENCES traps(trap_id)
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS processed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preprocessed_id INTEGER,
            trap_id TEXT,
            pest_species TEXT,
            pest_count INTEGER,
            mean_age REAL,
            confidence REAL,
            timestamp TEXT,
            FOREIGN KEY (preprocessed_id) REFERENCES preprocessed(id)
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS api_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at TEXT NOT NULL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            api_key TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """)
        conn.commit()


# Run database setup immediately
init_db_tables()

app = FastAPI(title="OrchardEye API")

# Add CORS Middleware to support local files and frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database session manager context manager
@contextlib.contextmanager
def db_session():
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON;")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# API Key hashing helper
def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


# Verify the provided key against the database and perform lazy migration if needed
def verify_and_migrate_trap_key(cursor: sqlite3.Cursor, trap_id: str, provided_key: str) -> bool:
    cursor.execute("SELECT api_key, active FROM traps WHERE trap_id = ?", (trap_id,))
    row = cursor.fetchone()
    if not row:
        return False
    
    stored_key, active = row
    if not active:
        return False
        
    # Check if stored key is hashed
    if stored_key.startswith("sha256:"):
        actual_hash = stored_key.split(":", 1)[1]
        provided_hash = hash_api_key(provided_key)
        return secrets.compare_digest(actual_hash, provided_hash)
    else:
        # Plaintext verification for backward compatibility
        if secrets.compare_digest(stored_key, provided_key):
            # Migrate the key in the database to hashed format
            hashed_key = f"sha256:{hash_api_key(provided_key)}"
            cursor.execute("UPDATE traps SET api_key = ? WHERE trap_id = ?", (hashed_key, trap_id))
            return True
        return False


# Admin Authentication Dependency
def verify_admin(
    x_admin_login_id: Optional[str] = Header(None, alias="X-Admin-Login-ID"),
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key")
):
    if not ADMIN_LOGIN_ID or not ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Administrative credentials are not configured on the server."
        )
    
    if not x_admin_login_id or not x_admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing administrative authentication headers."
        )
        
    is_login_correct = secrets.compare_digest(x_admin_login_id, ADMIN_LOGIN_ID)
    is_key_correct = secrets.compare_digest(x_admin_api_key, ADMIN_API_KEY)
    
    if not (is_login_correct and is_key_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative credentials."
        )


# User Authentication Dependency (For Protected Frontend Pages)
def verify_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_user_api_key: Optional[str] = Header(None, alias="X-User-API-Key"),
    user_id: Optional[str] = Query(None),
    api_key: Optional[str] = Query(None),
):
    u_id = x_user_id or user_id
    u_key = x_user_api_key or api_key
    
    if not u_id or not u_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing User ID or API Key."
        )
        
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT api_key, active FROM users WHERE user_id = ?", (u_id,))
        row = cursor.fetchone()
        
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid User ID or API Key."
        )
        
    stored_key, active = row
    if not active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive."
        )
        
    # Check if stored key is hashed
    if stored_key.startswith("sha256:"):
        actual_hash = stored_key.split(":", 1)[1]
        provided_hash = hash_api_key(u_key)
        if not secrets.compare_digest(actual_hash, provided_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid User ID or API Key."
            )
    else:
        # Plaintext fallback
        if not secrets.compare_digest(stored_key, u_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid User ID or API Key."
            )


# Pydantic Schemas
class TrapCreate(BaseModel):
    trap_id: str = Field(..., min_length=1, max_length=50)
    district: str = Field(..., min_length=1, max_length=100)
    village: str = Field(..., min_length=1, max_length=100)
    latitude: float
    longitude: float
    active: bool = True

class TrapUpdate(BaseModel):
    district: Optional[str] = Field(None, min_length=1, max_length=100)
    village: Optional[str] = Field(None, min_length=1, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    active: Optional[bool] = None

class RawQueryRequest(BaseModel):
    query: str
    params: Optional[List[Any]] = None

class RequestEmail(BaseModel):
    email: str = Field(..., min_length=5, max_length=150)

class LoginRequest(BaseModel):
    user_id: str
    api_key: str

class AdminLoginRequest(BaseModel):
    admin_login_id: str
    admin_api_key: str


# Endpoints

@app.get("/")
def home():
    return {"status": "OrchardEye API is running"}


@app.get("/traps")
def get_traps():
    """Retrieve all traps that are active (Legacy Public Endpoint)."""
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                trap_id,
                district,
                village,
                latitude,
                longitude,
                install_date,
                last_seen,
                active
            FROM traps
            WHERE active = 1
        """)
        rows = cursor.fetchall()

    traps = []
    for row in rows:
        traps.append({
            "trap_id": row[0],
            "district": row[1],
            "village": row[2],
            "latitude": row[3],
            "longitude": row[4],
            "install_date": row[5],
            "last_seen": row[6],
            "active": bool(row[7])
        })

    return traps


def _get_capture_records(image_url_prefix: str) -> List[Dict[str, Any]]:
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                p.id,
                p.trap_id,
                p.image_path,
                p.timestamp
            FROM preprocessed p
            INNER JOIN traps t ON p.trap_id = t.trap_id
            WHERE t.active = 1 AND p.image_path IS NOT NULL AND p.image_path != ''
            ORDER BY p.timestamp DESC
        """)
        rows = cursor.fetchall()

    results = []
    for row in rows:
        abs_path = row[2]
        relative_url = ""
        if abs_path and UPLOAD_ROOT in abs_path:
            relative_url = abs_path.replace(UPLOAD_ROOT, "").lstrip(os.path.sep).replace(os.path.sep, "/")

        results.append({
            "id": row[0],
            "trap_id": row[1],
            "image_url": f"{image_url_prefix}/{relative_url}" if relative_url else "",
            "timestamp": row[3],
        })

    return results


def _serve_upload_image(path: str) -> FileResponse:
    normalized_path = os.path.normpath(path)
    if normalized_path.startswith("..") or os.path.isabs(normalized_path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    full_path = os.path.join(UPLOAD_ROOT, normalized_path)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        )

    return FileResponse(full_path)


@app.get("/map/captures")
def map_get_captures():
    """Public capture list for the live map."""
    return _get_capture_records("/map/images")


@app.get("/map/images/{path:path}")
def serve_map_image(path: str):
    """Public image access for the live map."""
    return _serve_upload_image(path)


@app.post("/upload")
async def upload_image(
    trap_id: str = Form(...),
    api_key: str = Form(...),
    temperature: Optional[float] = Form(None),
    humidity: Optional[float] = Form(None),
    battery: Optional[float] = Form(None),
    image: UploadFile = File(...)
):
    # Sanitize the file name to prevent path traversal
    safe_filename = os.path.basename(image.filename) if image.filename else "image.jpg"
    
    # Restrict allowed image extensions
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    _, ext = os.path.splitext(safe_filename.lower())
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed: {allowed_extensions}"
        )

    with db_session() as connection:
        cursor = connection.cursor()

        # Verify trap exists, is active, and matches API key (lazy upgrades to hashed)
        if not verify_and_migrate_trap_key(cursor, trap_id, api_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authentication failed, trap is inactive, or trap does not exist."
            )

        # Retrieve district and village to build path
        cursor.execute("SELECT district, village FROM traps WHERE trap_id = ?", (trap_id,))
        district, village = cursor.fetchone()

        # Sanitize folder path elements
        safe_district = os.path.basename(district)
        safe_village = os.path.basename(village)
        safe_trap_id = os.path.basename(trap_id)

        # Create folder structure
        trap_folder = os.path.join(
            UPLOAD_ROOT,
            safe_district,
            safe_village,
            safe_trap_id
        )
        os.makedirs(trap_folder, exist_ok=True)

        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{safe_filename}"
        filepath = os.path.join(trap_folder, filename)

        # Save image
        contents = await image.read()
        with open(filepath, "wb") as f:
            f.write(contents)

        # Insert into preprocessed table
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO preprocessed (
                trap_id,
                image_path,
                timestamp,
                temperature,
                humidity,
                battery,
                processing_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trap_id,
                filepath,
                current_time,
                temperature,
                humidity,
                battery,
                "PENDING"
            )
        )

        # Update last seen
        cursor.execute(
            """
            UPDATE traps
            SET last_seen = ?
            WHERE trap_id = ?
            """,
            (
                current_time,
                trap_id
            )
        )

    return {
        "status": "success",
        "trap_id": trap_id,
        "saved_to": filepath
    }


# Public / Client-Facing API Endpoints

@app.post("/api/request-api")
def request_api(req: RequestEmail):
    """Allows a user to request API access by entering their email address."""
    with db_session() as connection:
        cursor = connection.cursor()
        
        # Check if already requested
        cursor.execute("SELECT status FROM api_requests WHERE email = ?", (req.email,))
        row = cursor.fetchone()
        
        if row:
            status_value = row[0]
            if status_value == "PENDING":
                return {"status": "success", "message": "Your request has already been submitted and is pending approval."}
            elif status_value == "APPROVED":
                return {"status": "success", "message": "An API key has already been approved and emailed to this address."}
            else:
                # Allow requesting again if previously rejected
                cursor.execute("UPDATE api_requests SET status = 'PENDING', created_at = ? WHERE email = ?", 
                               (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), req.email))
                return {"status": "success", "message": "Your request has been resubmitted for approval."}
        
        # New request
        cursor.execute(
            "INSERT INTO api_requests (email, status, created_at) VALUES (?, ?, ?)",
            (req.email, "PENDING", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        
    return {"status": "success", "message": "API key request submitted successfully. It will be emailed upon approval."}


@app.post("/api/login")
def login_user(req: LoginRequest):
    """Validate User ID and API Key (used by Map/Data login overlays)."""
    try:
        verify_user(req.user_id, req.api_key)
        return {"status": "success", "message": "Credentials verified successfully."}
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid User ID or API Key.")


# User-Protected Endpoints (Requires User ID and API Key validation)

@app.get("/api/user/traps", dependencies=[Depends(verify_user)])
def user_get_traps():
    """Retrieve all traps that are active for authorized users."""
    return get_traps()


@app.get("/api/user/data", dependencies=[Depends(verify_user)])
def user_get_data():
    """Retrieve all collected preprocessed records."""
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT 
                p.id,
                p.trap_id,
                p.image_path,
                p.timestamp,
                p.temperature,
                p.humidity,
                p.battery,
                p.processing_status,
                t.district,
                t.village
            FROM preprocessed p
            LEFT JOIN traps t ON p.trap_id = t.trap_id
            ORDER BY p.timestamp DESC
        """)
        rows = cursor.fetchall()
        
    results = []
    for row in rows:
        abs_path = row[2]
        relative_url = ""
        if abs_path and UPLOAD_ROOT in abs_path:
            relative_url = abs_path.replace(UPLOAD_ROOT, "").lstrip(os.path.sep).replace(os.path.sep, "/")
            
        results.append({
            "id": row[0],
            "trap_id": row[1],
            "image_url": f"/api/user/images/{relative_url}" if relative_url else "",
            "timestamp": row[3],
            "temperature": row[4],
            "humidity": row[5],
            "battery": row[6],
            "processing_status": row[7],
            "district": row[8] or "Unknown",
            "village": row[9] or "Unknown"
        })
        
    return results


@app.get("/api/user/images/{path:path}", dependencies=[Depends(verify_user)])
def serve_user_image(path: str):
    """Retrieve the uploaded image securely. Prevents directory traversal."""
    return _serve_upload_image(path)


# Administrative Endpoints

@app.post("/admin/login")
def admin_login(req: AdminLoginRequest):
    """Validate admin credentials before storing them in the admin panel."""
    if not ADMIN_LOGIN_ID or not ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Administrative credentials are not configured on the server.",
        )

    is_login_correct = secrets.compare_digest(req.admin_login_id, ADMIN_LOGIN_ID)
    is_key_correct = secrets.compare_digest(req.admin_api_key, ADMIN_API_KEY)

    if not (is_login_correct and is_key_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative credentials.",
        )

    return {"status": "success", "message": "Admin credentials verified successfully."}


@app.get("/admin/requests", dependencies=[Depends(verify_admin)])
def admin_get_requests():
    """Retrieve all submitted API key requests."""
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT id, email, status, created_at FROM api_requests ORDER BY id DESC")
        rows = cursor.fetchall()
        
    requests = []
    for row in rows:
        requests.append({
            "id": row[0],
            "email": row[1],
            "status": row[2],
            "created_at": row[3]
        })
    return requests


@app.post("/admin/requests/{request_id}/approve", dependencies=[Depends(verify_admin)])
def admin_approve_request(request_id: int):
    """Approve an API key request, register the user, and notify them."""
    try:
        result = approve_api_request(request_id)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    delivery = "emailed" if result["emailed"] else "logged to database/email_logs.txt"
    return {
        "status": "success",
        "message": f"Request approved. Credentials {delivery} for {result['email']}.",
        "user_id": result["user_id"],
        "api_key": result["api_key"],
    }


@app.post("/admin/requests/{request_id}/reject", dependencies=[Depends(verify_admin)])
def admin_reject_request(request_id: int):
    """Reject an API key request."""
    try:
        reject_api_request(request_id)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return {"status": "success", "message": "Request rejected successfully."}


@app.get("/admin/traps", dependencies=[Depends(verify_admin)])
def admin_get_traps():
    """Retrieve all registered traps (both active and inactive) along with their stored credentials."""
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                trap_id,
                api_key,
                district,
                village,
                latitude,
                longitude,
                install_date,
                last_seen,
                active
            FROM traps
        """)
        rows = cursor.fetchall()

    traps = []
    for row in rows:
        traps.append({
            "trap_id": row[0],
            "api_key": row[1],
            "district": row[2],
            "village": row[3],
            "latitude": row[4],
            "longitude": row[5],
            "install_date": row[6],
            "last_seen": row[7],
            "active": bool(row[8])
        })

    return traps


@app.post("/admin/traps", dependencies=[Depends(verify_admin)])
def admin_create_trap(trap: TrapCreate):
    """Register a new trap and generate a secure API key."""
    try:
        result = register_device(
            trap_id=trap.trap_id,
            district=trap.district,
            village=trap.village,
            latitude=trap.latitude,
            longitude=trap.longitude,
            active=trap.active,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return {
        "status": "success",
        "message": "Trap registered successfully.",
        "trap_id": result["trap_id"],
        "api_key": result["api_key"],
    }


@app.put("/admin/traps/{trap_id}", dependencies=[Depends(verify_admin)])
def admin_update_trap(trap_id: str, update_data: TrapUpdate):
    """Update details of a registered trap. Null fields are skipped."""
    with db_session() as connection:
        cursor = connection.cursor()
        
        # Verify trap existence
        cursor.execute("SELECT 1 FROM traps WHERE trap_id = ?", (trap_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trap '{trap_id}' not found."
            )

        updates = []
        params = []

        if update_data.district is not None:
            updates.append("district = ?")
            params.append(update_data.district)
        if update_data.village is not None:
            updates.append("village = ?")
            params.append(update_data.village)
        if update_data.latitude is not None:
            updates.append("latitude = ?")
            params.append(update_data.latitude)
        if update_data.longitude is not None:
            updates.append("longitude = ?")
            params.append(update_data.longitude)
        if update_data.active is not None:
            updates.append("active = ?")
            params.append(1 if update_data.active else 0)

        if not updates:
            return {"status": "success", "message": "No fields to update were provided."}

        query = f"UPDATE traps SET {', '.join(updates)} WHERE trap_id = ?"
        params.append(trap_id)
        cursor.execute(query, tuple(params))

    return {"status": "success", "message": f"Trap '{trap_id}' updated successfully."}


@app.delete("/admin/traps/{trap_id}", dependencies=[Depends(verify_admin)])
def admin_delete_trap(trap_id: str):
    """Remove a trap and all its associated preprocessed and processed data from the database."""
    with db_session() as connection:
        cursor = connection.cursor()
        
        cursor.execute("SELECT 1 FROM traps WHERE trap_id = ?", (trap_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trap '{trap_id}' not found."
            )

        # Retrieve all preprocessed records for this trap
        cursor.execute("SELECT id FROM preprocessed WHERE trap_id = ?", (trap_id,))
        prep_ids = [row[0] for row in cursor.fetchall()]

        # Cascade delete dependent processed records
        if prep_ids:
            placeholders = ",".join("?" for _ in prep_ids)
            cursor.execute(f"DELETE FROM processed WHERE preprocessed_id IN ({placeholders})", tuple(prep_ids))

        # Cascade delete dependent preprocessed records
        cursor.execute("DELETE FROM preprocessed WHERE trap_id = ?", (trap_id,))

        # Delete the trap
        cursor.execute("DELETE FROM traps WHERE trap_id = ?", (trap_id,))

    return {"status": "success", "message": f"Trap '{trap_id}' and all associated records deleted successfully."}


@app.post("/admin/query", dependencies=[Depends(verify_admin)])
def admin_raw_query(req: RawQueryRequest):
    """Execute raw SQL statements against the database (full database access)."""
    params = req.params or []
    with db_session() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(req.query, tuple(params))
            
            # If query yielded a description, it is a SELECT/read operation
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    results.append(dict(zip(columns, row)))
                return {
                    "status": "success",
                    "type": "select",
                    "columns": columns,
                    "row_count": len(results),
                    "results": results
                }
            else:
                # INSERT/UPDATE/DELETE/CREATE
                return {
                    "status": "success",
                    "type": "non-select",
                    "row_count": cursor.rowcount,
                    "last_row_id": cursor.lastrowid
                }
        except sqlite3.Error as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Database execution failed: {str(e)}"
            )