from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass

from .naming import OLLAMA_BASE_URL

HF_TOKEN_URL = "https://huggingface.co/settings/tokens"
GATED_REPOS: tuple[str, ...] = (
    "pyannote/speaker-diarization-community-1",
    "pyannote/segmentation-3.0",
)

_WHOAMI_URL = "https://huggingface.co/api/whoami-v2"
_OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"
_TIMEOUT = 15


@dataclass
class CheckResult:
    """One prerequisite check: what was checked, whether it passed, and either
    a success note or an actionable fix hint."""
    name: str
    ok: bool
    detail: str


def _http(url: str, token: str | None = None, method: str = "GET") -> tuple[int, bytes]:
    """Make a request and return (status, body).

    An HTTP error status is a normal result here, not an exception — the status
    is the signal we check. Only genuine connection failures raise
    (URLError/OSError).
    """
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:  # subclass of URLError; carries a status
        return exc.code, b""


def check_ffmpeg() -> CheckResult:
    path = shutil.which("ffmpeg")
    if path:
        return CheckResult("ffmpeg", True, path)
    return CheckResult(
        "ffmpeg", False,
        "not on PATH — install it (macOS: brew install ffmpeg; "
        "Debian/Ubuntu: sudo apt install ffmpeg)",
    )


def check_token(token: str) -> CheckResult:
    name = "Hugging Face token"
    if not token:
        return CheckResult(
            name, False,
            f"no token set — create a free one at {HF_TOKEN_URL} and re-run earwig setup",
        )
    try:
        status, body = _http(_WHOAMI_URL, token)
    except (urllib.error.URLError, OSError):
        return CheckResult(name, False, "could not reach Hugging Face — are you offline?")
    if status == 200:
        try:
            user = json.loads(body).get("name")
        except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):
            user = None
        # The response is untrusted: only echo `name` when it's a plain, short
        # string, so a crafted body can't inject junk into our output.
        if not isinstance(user, str) or not user.strip() or len(user) > 64:
            user = None
        return CheckResult(name, True, f"authenticated as {user}" if user else "valid")
    if status == 401:
        return CheckResult(
            name, False,
            f"token is invalid or expired — create a new one at {HF_TOKEN_URL}",
        )
    return CheckResult(name, False, f"could not verify (HTTP {status})")


def check_gated_access(repo: str, token: str) -> CheckResult:
    # Probe the model card, which every HF repo has, so a 404 can't be confused
    # with a gating result. Gating rejects any file in the repo with a 403.
    url = f"https://huggingface.co/{repo}/resolve/main/README.md"
    try:
        status, _ = _http(url, token, method="HEAD")
    except (urllib.error.URLError, OSError):
        return CheckResult(repo, False, "could not reach Hugging Face — are you offline?")
    if status == 200:
        return CheckResult(repo, True, "license accepted")
    if status == 403:
        return CheckResult(
            repo, False,
            f"license not accepted — open https://huggingface.co/{repo} and click "
            "'Agree and access repository'",
        )
    if status == 401:
        return CheckResult(
            repo, False, f"token rejected — create a new one at {HF_TOKEN_URL}"
        )
    return CheckResult(repo, False, f"could not verify (HTTP {status})")


def check_namer(namer: str) -> CheckResult:
    name = f"namer '{namer}'"
    if namer == "claude":
        path = shutil.which("claude")
        if path:
            return CheckResult(name, True, path)
        return CheckResult(
            name, False,
            "the claude CLI is not on PATH — install it, or pick another namer "
            "(at runtime earwig degrades to raw speaker ids rather than failing)",
        )
    if namer == "local":
        try:
            status, _ = _http(_OLLAMA_TAGS_URL)
        except (urllib.error.URLError, OSError):
            return CheckResult(
                name, False,
                f"no Ollama server at {OLLAMA_BASE_URL} — start Ollama, or pick "
                "another namer",
            )
        if status == 200:
            return CheckResult(name, True, f"Ollama reachable at {OLLAMA_BASE_URL}")
        return CheckResult(name, False, f"Ollama responded with HTTP {status}")
    return CheckResult(name, True, "ready (no external dependency)")
