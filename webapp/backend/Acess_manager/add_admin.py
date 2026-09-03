import secrets

from env_utils import read_env_lines, set_env, write_env


def main():
    username = input("Admin Login ID: ").strip()
    if not username:
        print("Username cannot be empty.")
        return

    admin_key = secrets.token_hex(32)
    lines = read_env_lines()
    lines = set_env("ADMIN_LOGIN_ID", username, lines)
    lines = set_env("ADMIN_API_KEY", admin_key, lines)
    write_env(lines)

    print("\n===================================")
    print("Admin credentials generated")
    print("===================================")
    print(f"Login ID : {username}")
    print(f"API Key  : {admin_key}")
    print("\nSaved to backend/.env")
    print("Restart the FastAPI server.")


if __name__ == "__main__":
    main()
