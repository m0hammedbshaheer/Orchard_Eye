from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"


def read_env_lines():
    if ENV_FILE.exists():
        return ENV_FILE.read_text().splitlines(keepends=True)
    return []


def set_env(key: str, value: str, lines: list[str] | None = None) -> list[str]:
    lines = list(lines if lines is not None else read_env_lines())
    updated = False

    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            updated = True
            break

    if not updated:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"
        lines.append(f"{key}={value}\n")

    return lines


def write_env(lines: list[str]) -> None:
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    ENV_FILE.write_text("".join(lines))


def get_env_value(key: str, default: str | None = None) -> str | None:
    if not ENV_FILE.exists():
        return default

    for line in ENV_FILE.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    return default
