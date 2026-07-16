from __future__ import annotations

import os
import re
from pathlib import Path

# KEY=VALUE, tolerating a leading `export ` and surrounding whitespace. Comment
# lines never match: `#` is not a valid identifier start.
_PAIR = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")

# Detects the same leading `export ` that _PAIR tolerates, so a replaced line
# can preserve it instead of silently dropping it.
_EXPORT_PREFIX = re.compile(r"^\s*export\s+")


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


# earwig only needs these. Anything else in a .env belongs to some other tool —
# earwig runs from arbitrary directories, and injecting a stranger's keys into
# this process (and the subprocesses and native libs it loads) is not our
# business.
EARWIG_KEYS: tuple[str, ...] = ("HF_TOKEN", "EARWIG_NAMER")


def load_dotenv(path: str | Path, keys: tuple[str, ...] | None = None) -> None:
    """Load KEY=VALUE pairs from `path` into os.environ.

    Only fills in keys that are unset, so whatever is already in the real
    environment wins. A missing or unreadable file is a no-op — these files
    are optional. When `keys` is given, only those names are loaded; every
    other key present in the file is ignored.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    for key, value in parse_env_text(text).items():
        if keys is not None and key not in keys:
            continue
        os.environ.setdefault(key, value)


def load_config(cwd_env: str | Path = ".env") -> None:
    """Load earwig's settings into os.environ.

    Precedence, highest first: the real environment, ./.env (handy inside a
    checkout), then the per-user config written by `earwig setup`. load_dotenv
    only fills unset keys, so loading in this order produces exactly that.
    Only earwig's own keys (`EARWIG_KEYS`) are loaded — a `.env` in whatever
    directory earwig happens to be run from may belong to an unrelated
    project, and its other keys are not ours to import into the process (and
    from there into the subprocesses and native libraries earwig loads).
    """
    load_dotenv(cwd_env, keys=EARWIG_KEYS)
    load_dotenv(user_config_path(), keys=EARWIG_KEYS)


def upsert_env_var(path: str | Path, key: str, value: str) -> None:
    """Set `key` to `value` in the env file at `path`, preserving every other
    line.

    Creates the file and any missing parent directories. The file holds
    secrets, so it is always left mode 0600. The value is never printed.

    If `key` appears more than once, the first occurrence is replaced and any
    later duplicates are dropped. parse_env_text lets the *last* match win
    when loading, so leaving a stale duplicate in place would make the write
    appear to succeed while the old value kept silently winning on load.
    """
    file = Path(path)
    try:
        lines = file.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        lines = []

    replaced = False
    new_lines: list[str] = []
    for line in lines:
        match = _PAIR.match(line)
        if match and match.group(1) == key:
            if replaced:
                continue  # drop stale duplicate
            prefix = "export " if _EXPORT_PREFIX.match(line) else ""
            new_lines.append(f"{prefix}{key}={value}")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.append(f"{key}={value}")

    file.parent.mkdir(parents=True, exist_ok=True)
    # Create with 0600 from the start: this file holds a token, so it must never
    # exist, even briefly, at the umask's default permissions. O_CREAT's mode
    # only applies when the file is new, so keep the chmod for existing files.
    fd = os.open(file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(new_lines) + "\n")
    file.chmod(0o600)
