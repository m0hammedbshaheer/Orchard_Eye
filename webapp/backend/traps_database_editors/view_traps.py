import sqlite3
import os

# Resolve database path dynamically relative to script location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "traps.db")

connection = sqlite3.connect(DB_PATH)
c = connection.cursor()
c.execute("SELECT * FROM traps;")
print("Traps Table:")
for row in c.fetchall():
    print(row)