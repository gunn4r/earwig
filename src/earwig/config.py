from __future__ import annotations

import os
import re
from pathlib import Path

# KEY=VALUE, tolerating a leading `export ` and surrounding whitespace. Comment
# lines never match: `#` is not a valid identifier start.
_PAIR = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_env_text(text: str) -> dict[str, str]:
    """Parse env-file content into a mapping. Blanks, comments, and lines that
    aren't KEY=VALUE are skipped rather than raising."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = _PAIR.match(line)
        if match:
            values[match.group(1)] = _unquote(match.group(2))
    return values


def user_config_path() -> Path:
    """Where `earwig setup` stores settings: $XDG_CONFIG_HOME/earwig/env, or
    ~/.config/earwig/env. Per-user rather than per-directory, so a globally
    installed earwig finds the token whatever the working directory is."""
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "earwig" / "env"


def load_dotenv(path: str | Path) -> None:
    """Load KEY=VALUE pairs from `path` into os.environ.

    Only fills in keys that are unset, so whatever is already in the real
    environment wins. A missing or unreadable file is a no-op — these files
    are optional.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    for key, value in parse_env_text(text).items():
        os.environ.setdefault(key, value)


def load_config(cwd_env: str | Path = ".env") -> None:
    """Load earwig's settings into os.environ.

    Precedence, highest first: the real environment, ./.env (handy inside a
    checkout), then the per-user config written by `earwig setup`. load_dotenv
    only fills unset keys, so loading in this order produces exactly that.
    """
    load_dotenv(cwd_env)
    load_dotenv(user_config_path())


def upsert_env_var(path: str | Path, key: str, value: str) -> None:
    """Set `key` to `value` in the env file at `path`, preserving every other
    line.

    Creates the file and any missing parent directories. The file holds
    secrets, so it is always left mode 0600. The value is never printed.
    """
    file = Path(path)
    try:
        lines = file.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        lines = []

    replaced = False
    for i, line in enumerate(lines):
        match = _PAIR.match(line)
        if match and match.group(1) == key and not replaced:
            lines[i] = f"{key}={value}"
            replaced = True
    if not replaced:
        lines.append(f"{key}={value}")

    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    file.chmod(0o600)
