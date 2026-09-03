import sqlite3
import os

# Resolve database path dynamically relative to script location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "traps.db")

connection = sqlite3.connect(DB_PATH)
c = connection.cursor()

c.execute("""
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
c.execute("""CREATE TABLE IF NOT EXISTS preprocessed(
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trap_id TEXT,

    image_path TEXT,

    timestamp TEXT,

    temperature REAL,
    humidity REAL,
    battery REAL,

    processing_status TEXT DEFAULT 'PENDING',

    FOREIGN KEY (trap_id)
    REFERENCES traps(trap_id)
);""")


c.execute("""CREATE TABLE IF NOT EXISTS processed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    preprocessed_id INTEGER,

    trap_id TEXT,

    pest_species TEXT,

    pest_count INTEGER,

    mean_age REAL,

    confidence REAL,

    timestamp TEXT,

    FOREIGN KEY (preprocessed_id)
    REFERENCES preprocessed(id)
);""")

connection.commit()
connection.close()

# Access-control tables used by the API request and user login flow
connection = sqlite3.connect(DB_PATH)
c = connection.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS api_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'PENDING',
    created_at TEXT NOT NULL
);
""")

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    api_key TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);
""")

connection.commit()
connection.close()