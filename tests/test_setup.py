import urllib.error

import earwig.setup as setup_mod
from earwig.setup import (
    CheckResult,
    check_ffmpeg,
    check_gated_access,
    check_namer,
    check_token,
    run_setup,
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


def stub_all_checks(monkeypatch, ok=True):
    """Replace every check with a canned result so we test orchestration only."""
    monkeypatch.setattr(setup_mod, "check_ffmpeg",
                        lambda: CheckResult("ffmpeg", ok, "d"))
    monkeypatch.setattr(setup_mod, "check_token",
                        lambda token: CheckResult("Hugging Face token", ok, "d"))
    monkeypatch.setattr(setup_mod, "check_gated_access",
                        lambda repo, token: CheckResult(repo, ok, "d"))
    monkeypatch.setattr(setup_mod, "check_namer",
                        lambda namer: CheckResult(f"namer '{namer}'", ok, "d"))


def make_input(answers):
    """Return an input_fn that pops canned answers in order."""
    queue = list(answers)
    return lambda prompt="": queue.pop(0) if queue else ""


def test_run_setup_writes_token_and_namer(tmp_path, monkeypatch):
    stub_all_checks(monkeypatch)
    env = tmp_path / "env"
    code = run_setup(
        namer="heuristic",
        env_path=env,
        open_browser=False,
        input_fn=make_input([""]),
        getpass_fn=lambda prompt="": "hf_secret",
    )
    assert code == 0
    contents = env.read_text()
    assert "HF_TOKEN=hf_secret" in contents
    assert "EARWIG_NAMER=heuristic" in contents


def test_run_setup_defaults_to_user_config_path(tmp_path, monkeypatch):
    stub_all_checks(monkeypatch)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    run_setup(
        namer="heuristic",
        open_browser=False,
        input_fn=make_input([""]),
        getpass_fn=lambda prompt="": "hf_secret",
    )
    assert "HF_TOKEN=hf_secret" in (tmp_path / "earwig" / "env").read_text()


def test_run_setup_never_prints_the_token(tmp_path, monkeypatch, capsys):
    stub_all_checks(monkeypatch)
    run_setup(
        namer="heuristic",
        env_path=tmp_path / "env",
        open_browser=False,
        input_fn=make_input([""]),
        getpass_fn=lambda prompt="": "hf_supersecret",
    )
    assert "hf_supersecret" not in capsys.readouterr().out


def test_run_setup_returns_1_when_a_check_fails(tmp_path, monkeypatch):
    stub_all_checks(monkeypatch, ok=False)
    code = run_setup(
        namer="heuristic",
        env_path=tmp_path / "env",
        open_browser=False,
        input_fn=make_input([""]),
        getpass_fn=lambda prompt="": "hf_secret",
    )
    assert code == 1


def test_run_setup_prompts_for_namer_when_not_given(tmp_path, monkeypatch):
    stub_all_checks(monkeypatch)
    env = tmp_path / "env"
    # answers: press-enter after the links, then the namer choice
    run_setup(
        namer=None,
        env_path=env,
        open_browser=False,
        input_fn=make_input(["", "claude"]),
        getpass_fn=lambda prompt="": "hf_secret",
    )
    assert "EARWIG_NAMER=claude" in env.read_text()


def test_run_setup_invalid_namer_entry_falls_back_to_heuristic(tmp_path, monkeypatch):
    stub_all_checks(monkeypatch)
    env = tmp_path / "env"
    run_setup(
        namer=None,
        env_path=env,
        open_browser=False,
        input_fn=make_input(["", "bogus"]),
        getpass_fn=lambda prompt="": "hf_secret",
    )
    assert "EARWIG_NAMER=heuristic" in env.read_text()


def test_run_setup_empty_token_keeps_existing_env_token(tmp_path, monkeypatch):
    stub_all_checks(monkeypatch)
    monkeypatch.setenv("HF_TOKEN", "hf_existing")
    env = tmp_path / "env"
    code = run_setup(
        namer="heuristic",
        env_path=env,
        open_browser=False,
        input_fn=make_input([""]),
        getpass_fn=lambda prompt="": "",
    )
    assert code == 0
    assert "HF_TOKEN" not in env.read_text()  # nothing written; existing token kept


def test_run_setup_skips_gated_checks_when_token_check_fails(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(setup_mod, "check_ffmpeg",
                        lambda: CheckResult("ffmpeg", True, "d"))
    monkeypatch.setattr(setup_mod, "check_token",
                        lambda token: CheckResult("Hugging Face token", False, "bad"))
    monkeypatch.setattr(setup_mod, "check_namer",
                        lambda namer: CheckResult("namer", True, "d"))

    def spy_gated(repo, token):
        calls.append(repo)
        return CheckResult(repo, True, "d")

    monkeypatch.setattr(setup_mod, "check_gated_access", spy_gated)
    run_setup(
        namer="heuristic",
        env_path=tmp_path / "env",
        open_browser=False,
        input_fn=make_input([""]),
        getpass_fn=lambda prompt="": "hf_bad",
    )
    assert calls == []  # pointless to probe gating with a token we know is bad


def test_run_setup_warns_on_odd_token_prefix(tmp_path, monkeypatch, capsys):
    stub_all_checks(monkeypatch)
    run_setup(
        namer="heuristic",
        env_path=tmp_path / "env",
        open_browser=False,
        input_fn=make_input([""]),
        getpass_fn=lambda prompt="": "not_a_hf_token",
    )
    assert "doesn't look like" in capsys.readouterr().out


def test_run_setup_opens_browser_when_accepted(tmp_path, monkeypatch):
    stub_all_checks(monkeypatch)
    opened = []
    monkeypatch.setattr(setup_mod.webbrowser, "open", lambda url: opened.append(url))
    run_setup(
        namer="heuristic",
        env_path=tmp_path / "env",
        open_browser=True,
        input_fn=make_input(["y", ""]),
        getpass_fn=lambda prompt="": "hf_secret",
    )
    assert setup_mod.HF_TOKEN_URL in opened
    assert len(opened) == 1 + len(setup_mod.GATED_REPOS)


def test_run_setup_respects_browser_decline(tmp_path, monkeypatch):
    stub_all_checks(monkeypatch)
    opened = []
    monkeypatch.setattr(setup_mod.webbrowser, "open", lambda url: opened.append(url))
    run_setup(
        namer="heuristic",
        env_path=tmp_path / "env",
        open_browser=True,
        input_fn=make_input(["n", ""]),
        getpass_fn=lambda prompt="": "hf_secret",
    )
    assert opened == []
