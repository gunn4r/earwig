import sys

from earwig.update import PKG_SPEC, detect_manager, run_update, upgrade_command


def _probe_map(mapping):
    # mapping: first token of cmd -> stdout string (or None). Default None.
    def probe(cmd):
        return mapping.get(cmd[0])
    return probe


def test_detect_manager_uv_owned():
    probe = _probe_map({"uv": "earwig v0.2.0"})
    assert detect_manager(probe, lambda: False) == "uv"


def test_detect_manager_pipx_owned():
    probe = _probe_map({"uv": None, "pipx": "earwig"})
    assert detect_manager(probe, lambda: False) == "pipx"


def test_detect_manager_editable():
    probe = _probe_map({"uv": None, "pipx": None})
    assert detect_manager(probe, lambda: True) == "editable"


def test_detect_manager_pip():
    probe = _probe_map({"uv": None, "pipx": None, sys.executable: "Name: earwig"})
    assert detect_manager(probe, lambda: False) == "pip"


def test_detect_manager_unknown():
    probe = _probe_map({})  # everything None
    assert detect_manager(probe, lambda: False) == "unknown"


def test_detect_manager_specific_manager_wins_over_editable():
    # uv-owned AND editable -> uv (specific manager wins).
    probe = _probe_map({"uv": "earwig v0.2.0"})
    assert detect_manager(probe, lambda: True) == "uv"


def test_detect_manager_ignores_unrelated_tool_output():
    # A uv/pipx listing that does not mention earwig must not match.
    probe = _probe_map({"uv": "ruff v0.1.0", "pipx": "black 24.0"})
    assert detect_manager(probe, lambda: False) == "unknown"


def test_upgrade_command_mapping():
    assert upgrade_command("uv") == ["uv", "tool", "upgrade", "earwig"]
    assert upgrade_command("pipx") == ["pipx", "upgrade", "earwig"]
    assert upgrade_command("pip") == [sys.executable, "-m", "pip", "install", "-U", PKG_SPEC]
    assert upgrade_command("editable") is None
    assert upgrade_command("unknown") is None


def test_run_update_uv_executes_and_returns_code():
    calls = []
    probe = _probe_map({"uv": "earwig v0.2.0"})
    out_lines = []
    code = run_update(
        probe=probe,
        execute=lambda cmd: calls.append(cmd) or 0,
        is_editable=lambda: False,
        out=out_lines.append,
    )
    assert code == 0
    assert calls == [["uv", "tool", "upgrade", "earwig"]]


def test_run_update_passes_through_nonzero_exit():
    probe = _probe_map({"uv": "earwig v0.2.0"})
    code = run_update(
        probe=probe,
        execute=lambda cmd: 7,
        is_editable=lambda: False,
        out=lambda _msg: None,
    )
    assert code == 7


def test_run_update_editable_prints_git_pull_and_returns_0():
    executed = []
    out_lines = []
    code = run_update(
        probe=_probe_map({"uv": None, "pipx": None}),
        execute=lambda cmd: executed.append(cmd) or 0,
        is_editable=lambda: True,
        out=out_lines.append,
    )
    assert code == 0
    assert executed == []                      # never shells out
    assert any("git pull" in line for line in out_lines)


def test_run_update_unknown_prints_manual_and_returns_1():
    executed = []
    out_lines = []
    code = run_update(
        probe=_probe_map({}),
        execute=lambda cmd: executed.append(cmd) or 0,
        is_editable=lambda: False,
        out=out_lines.append,
    )
    assert code == 1
    assert executed == []
    joined = "\n".join(out_lines)
    assert "uv tool upgrade earwig" in joined
    assert "pipx upgrade earwig" in joined
    assert PKG_SPEC in joined
