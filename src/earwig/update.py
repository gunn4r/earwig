from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, distribution
from typing import Literal

PKG_SPEC = "git+https://github.com/gunn4r/earwig@main"

Manager = Literal["uv", "pipx", "pip", "editable", "unknown"]


def _default_probe(cmd: list[str]) -> str | None:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _is_editable() -> bool:
    try:
        raw = distribution("earwig").read_text("direct_url.json")
    except (PackageNotFoundError, OSError):
        return False
    if not raw:
        return False
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return bool(data.get("dir_info", {}).get("editable"))


def detect_manager(
    probe: Callable[[list[str]], str | None],
    is_editable: Callable[[], bool],
) -> Manager:
    out = probe(["uv", "tool", "list"])
    if out and "earwig" in out:
        return "uv"
    out = probe(["pipx", "list", "--short"])
    if out and "earwig" in out:
        return "pipx"
    if is_editable():
        return "editable"
    if probe([sys.executable, "-m", "pip", "show", "earwig"]):
        return "pip"
    return "unknown"


def upgrade_command(manager: Manager) -> list[str] | None:
    if manager == "uv":
        return ["uv", "tool", "upgrade", "earwig"]
    if manager == "pipx":
        return ["pipx", "upgrade", "earwig"]
    if manager == "pip":
        return [sys.executable, "-m", "pip", "install", "-U", PKG_SPEC]
    return None


def _default_execute(cmd: list[str]) -> int:
    try:
        return subprocess.run(cmd).returncode
    except OSError:
        return 1


def run_update(
    *,
    probe: Callable[[list[str]], str | None] = _default_probe,
    execute: Callable[[list[str]], int] = _default_execute,
    is_editable: Callable[[], bool] = _is_editable,
    out: Callable[[str], None] = print,
) -> int:
    manager = detect_manager(probe, is_editable)
    cmd = upgrade_command(manager)
    if cmd is not None:
        out(f"Updating earwig via {manager}...")
        return execute(cmd)
    if manager == "editable":
        out("earwig is running from a source checkout — update it with `git pull`.")
        return 0
    out(
        "Couldn't determine how earwig was installed. To update, run one of:\n"
        "  uv tool upgrade earwig\n"
        "  pipx upgrade earwig\n"
        f"  {sys.executable} -m pip install -U {PKG_SPEC}"
    )
    return 1
