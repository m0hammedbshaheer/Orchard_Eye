import os
import sqlite3
import hashlib
import secrets
import contextlib
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

from env_utils import BACKEND_DIR, ENV_FILE

load_dotenv(ENV_FILE)

BASE_DIR = BACKEND_DIR.parent
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "database", "traps.db")
DB_PATH = os.getenv("DB_PATH", DEFAULT_DB_PATH)


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def store_api_key(plaintext: str) -> str:
    return f"sha256:{hash_api_key(plaintext)}"


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


def init_access_tables():
    with db_session() as conn:
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


def send_approval_email(to_email: str, user_id: str, api_key: str) -> bool:
    log_dir = os.path.join(BASE_DIR, "database")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "email_logs.txt")

    log_entry = (
        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"To: {to_email}\n"
        f"Subject: OrchardEye API Access Credentials\n"
        f"Body:\n"
        f"  User ID: {user_id}\n"
        f"  API Key: {api_key}\n"
        f"-----------------------------------------\n"
    )

    with open(log_path, "a") as f:
        f.write(log_entry)

    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_username)

    if not smtp_username or not smtp_password:
        print(f"SMTP not configured. Credentials logged to {log_path}")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = to_email
        msg["Subject"] = "OrchardEye API Access Credentials"

        body = (
            f"Hello,\n\n"
            f"Your request for OrchardEye API access has been approved.\n"
            f"Use the credentials below to log in to the map and view collected data:\n\n"
            f"User ID: {user_id}\n"
            f"API Key: {api_key}\n\n"
            f"Best regards,\n"
            f"OrchardEye Team"
        )
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

        print(f"Sent approval email to {to_email}")
        return True
    except Exception as exc:
        print(f"Failed to send email to {to_email}: {exc}")
        print(f"Credentials were saved to {log_path}")
        return False


def approve_request(request_id: int) -> dict:
    init_access_tables()

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email, status FROM api_requests WHERE id = ?", (request_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError("Request not found.")

        email, req_status = row
        if req_status != "PENDING":
            raise ValueError(f"Request is already {req_status}.")

        user_id = f"USER_{secrets.token_hex(4).upper()}"
        api_key_plaintext = f"user_{secrets.token_hex(16)}"
        api_key_stored = store_api_key(api_key_plaintext)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            cursor.execute(
                "INSERT INTO users (user_id, email, api_key, created_at) VALUES (?, ?, ?, ?)",
                (user_id, email, api_key_stored, current_time),
            )
        except sqlite3.IntegrityError:
            cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
            user_id = cursor.fetchone()[0]
            cursor.execute(
                "UPDATE users SET api_key = ?, active = 1 WHERE user_id = ?",
                (api_key_stored, user_id),
            )

        cursor.execute("UPDATE api_requests SET status = 'APPROVED' WHERE id = ?", (request_id,))

    emailed = send_approval_email(email, user_id, api_key_plaintext)
    return {
        "user_id": user_id,
        "api_key": api_key_plaintext,
        "email": email,
        "emailed": emailed,
    }


def reject_request(request_id: int) -> None:
    init_access_tables()

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM api_requests WHERE id = ?", (request_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError("Request not found.")
        if row[0] != "PENDING":
            raise ValueError(f"Request is already {row[0]}.")

        cursor.execute("UPDATE api_requests SET status = 'REJECTED' WHERE id = ?", (request_id,))


def list_pending_requests() -> list[dict]:
    init_access_tables()

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, status, created_at FROM api_requests ORDER BY id DESC"
        )
        rows = cursor.fetchall()

    return [
        {"id": row[0], "email": row[1], "status": row[2], "created_at": row[3]}
        for row in rows
    ]


def register_device(
    trap_id: str,
    district: str,
    village: str,
    latitude: float,
    longitude: float,
    active: bool = True,
) -> dict:
    api_key_plaintext = secrets.token_hex(32)
    api_key_stored = store_api_key(api_key_plaintext)
    install_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with db_session() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO traps (
                    trap_id, api_key, district, village,
                    latitude, longitude, install_date, last_seen, active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trap_id,
                    api_key_stored,
                    district,
                    village,
                    latitude,
                    longitude,
                    install_date,
                    install_date,
                    1 if active else 0,
                ),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"Trap ID '{trap_id}' already exists.")

    return {
        "trap_id": trap_id,
        "api_key": api_key_plaintext,
        "district": district,
        "village": village,
        "latitude": latitude,
        "longitude": longitude,
        "active": active,
    }
