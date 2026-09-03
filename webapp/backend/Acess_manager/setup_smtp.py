from env_utils import read_env_lines, set_env, write_env


def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def main():
    print("\n=== OrchardEye SMTP Setup ===")
    print("Configure email delivery for approved API key requests.\n")

    server = prompt("SMTP server", "smtp.gmail.com")
    port = prompt("SMTP port", "587")
    username = prompt("SMTP username (email address)")
    password = prompt("SMTP password or app password")
    from_addr = prompt("From address", username)

    if not username or not password:
        print("\nSMTP username and password are required.")
        return

    lines = read_env_lines()
    lines = set_env("SMTP_SERVER", server, lines)
    lines = set_env("SMTP_PORT", port, lines)
    lines = set_env("SMTP_USERNAME", username, lines)
    lines = set_env("SMTP_PASSWORD", password, lines)
    lines = set_env("SMTP_FROM", from_addr, lines)
    write_env(lines)

    print("\nSMTP settings saved to backend/.env")
    print("Restart the FastAPI server before approving requests.")


if __name__ == "__main__":
    main()
