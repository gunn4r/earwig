import sys

from earwig.update import PKG_SPEC, detect_manager, upgrade_command


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
