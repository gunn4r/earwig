import urllib.error

import earwig.setup as setup_mod
from earwig.setup import (
    CheckResult,
    check_ffmpeg,
    check_gated_access,
    check_namer,
    check_token,
)

REPO = "pyannote/speaker-diarization-community-1"


def fake_http(status, body=b""):
    def _http(url, token=None, method="GET"):
        return status, body
    return _http


def raising_http(exc):
    def _http(url, token=None, method="GET"):
        raise exc
    return _http


def test_check_ffmpeg_found(monkeypatch):
    monkeypatch.setattr(setup_mod.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    result = check_ffmpeg()
    assert result.ok is True
    assert "/usr/bin/ffmpeg" in result.detail


def test_check_ffmpeg_missing(monkeypatch):
    monkeypatch.setattr(setup_mod.shutil, "which", lambda name: None)
    result = check_ffmpeg()
    assert result.ok is False
    assert "PATH" in result.detail


def test_check_token_empty_is_actionable():
    result = check_token("")
    assert result.ok is False
    assert "huggingface.co/settings/tokens" in result.detail


def test_check_token_valid_reports_username(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", fake_http(200, b'{"name": "gunn4r"}'))
    result = check_token("hf_abc")
    assert result.ok is True
    assert "gunn4r" in result.detail


def test_check_token_valid_with_unparsable_body(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", fake_http(200, b"not json"))
    result = check_token("hf_abc")
    assert result.ok is True


def test_check_token_401_is_actionable(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", fake_http(401))
    result = check_token("hf_bad")
    assert result.ok is False
    assert "invalid or expired" in result.detail


def test_check_token_offline_degrades(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", raising_http(urllib.error.URLError("down")))
    result = check_token("hf_abc")
    assert result.ok is False
    assert "could not reach" in result.detail


def test_check_token_never_echoes_the_token(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", fake_http(401))
    result = check_token("hf_supersecret")
    assert "hf_supersecret" not in result.detail


def test_check_token_unexpected_status(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", fake_http(500))
    result = check_token("hf_abc")
    assert result.ok is False
    assert "500" in result.detail


def test_check_token_valid_json_wrong_shape(monkeypatch):
    # A 200 whose body is valid JSON but not an object: .get() raises
    # AttributeError, which must degrade to a plain "valid", not crash.
    monkeypatch.setattr(setup_mod, "_http", fake_http(200, b"[1, 2]"))
    result = check_token("hf_abc")
    assert result.ok is True


def test_check_token_ignores_junk_username(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", fake_http(200, b'{"name": {"nested": 1}}'))
    result = check_token("hf_abc")
    assert result.ok is True
    assert "nested" not in result.detail


def test_check_gated_access_granted(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", fake_http(200))
    result = check_gated_access(REPO, "hf_abc")
    assert result.ok is True
    assert result.name == REPO


def test_check_gated_access_403_names_the_repo_url(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", fake_http(403))
    result = check_gated_access(REPO, "hf_abc")
    assert result.ok is False
    assert f"https://huggingface.co/{REPO}" in result.detail
    assert "Agree and access repository" in result.detail


def test_check_gated_access_unexpected_status(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", fake_http(500))
    result = check_gated_access(REPO, "hf_abc")
    assert result.ok is False
    assert "500" in result.detail


def test_check_gated_access_401_is_actionable(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", fake_http(401))
    result = check_gated_access(REPO, "hf_abc")
    assert result.ok is False
    assert "huggingface.co/settings/tokens" in result.detail


def test_check_gated_access_offline_degrades(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", raising_http(urllib.error.URLError("down")))
    result = check_gated_access(REPO, "hf_abc")
    assert result.ok is False
    assert "could not reach" in result.detail


def test_check_gated_access_uses_head(monkeypatch):
    seen = {}

    def spy(url, token=None, method="GET"):
        seen["method"] = method
        seen["url"] = url
        return 200, b""

    monkeypatch.setattr(setup_mod, "_http", spy)
    check_gated_access(REPO, "hf_abc")
    assert seen["method"] == "HEAD"  # a body would be a pointless download
    assert REPO in seen["url"]


def test_check_namer_heuristic_always_ok():
    assert check_namer("heuristic").ok is True


def test_check_namer_off_always_ok():
    assert check_namer("off").ok is True


def test_check_namer_claude_present(monkeypatch):
    monkeypatch.setattr(setup_mod.shutil, "which", lambda name: "/usr/bin/claude")
    assert check_namer("claude").ok is True


def test_check_namer_claude_missing_is_actionable(monkeypatch):
    monkeypatch.setattr(setup_mod.shutil, "which", lambda name: None)
    result = check_namer("claude")
    assert result.ok is False
    assert "not on PATH" in result.detail


def test_check_namer_local_reachable(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", fake_http(200))
    assert check_namer("local").ok is True


def test_check_namer_local_unreachable(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", raising_http(urllib.error.URLError("down")))
    result = check_namer("local")
    assert result.ok is False
    assert "Ollama" in result.detail


def test_check_namer_local_non_200(monkeypatch):
    monkeypatch.setattr(setup_mod, "_http", fake_http(503))
    result = check_namer("local")
    assert result.ok is False
    assert "503" in result.detail
