import sqlite3
import secrets
import hashlib
import os
from datetime import datetime

# Resolve database path dynamically relative to script location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "traps.db")

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

while True:
    print("\n=== OrchardEye Trap Registration ===")
    print("Type 'exit' at any prompt to quit.\n")

    trap_id = input("Trap ID: ").strip()
    if trap_id.lower() == "exit":
        break

    district = input("District: ").strip()
    if district.lower() == "exit":
        break

    village = input("Village: ").strip()
    if village.lower() == "exit":
        break

    latitude = input("Latitude: ").strip()
    if latitude.lower() == "exit":
        break

    longitude = input("Longitude: ").strip()
    if longitude.lower() == "exit":
        break

    install_date = input(
        "Install Date (YYYY-MM-DD) [Leave blank for today]: "
    ).strip()

    if install_date.lower() == "exit":
        break

    if not install_date:
        install_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        latitude = float(latitude)
        longitude = float(longitude)

        api_key = secrets.token_hex(32)
        api_key_stored = f"sha256:{hash_api_key(api_key)}"

        cursor.execute(
            """
            INSERT INTO traps (
                trap_id,
                api_key,
                district,
                village,
                latitude,
                longitude,
                install_date,
                last_seen
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trap_id,
                api_key_stored,
                district,
                village,
                latitude,
                longitude,
                install_date,
                install_date
            )
        )

        connection.commit()

        print("\nTrap Registered Successfully")
        print(f"Trap ID : {trap_id}")
        print(f"API Key : {api_key}")

    except ValueError:
        print("Latitude and Longitude must be valid numbers.")

    except sqlite3.IntegrityError:
        print(f"Trap '{trap_id}' already exists.")

    except Exception as e:
        print(f"Unexpected Error: {e}")
print("\nDatabase connection closed.")
