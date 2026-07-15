import os
import stat
from pathlib import Path

from earwig.config import (
    load_config,
    load_dotenv,
    parse_env_text,
    upsert_env_var,
    user_config_path,
)


def test_parse_env_text_basic_pairs():
    parsed = parse_env_text("HF_TOKEN=hf_abc\nEARWIG_NAMER=heuristic\n")
    assert parsed == {"HF_TOKEN": "hf_abc", "EARWIG_NAMER": "heuristic"}


def test_parse_env_text_ignores_blanks_and_comments():
    parsed = parse_env_text("\n# a comment\n\nA=1\n#B=2\n")
    assert parsed == {"A": "1"}


def test_parse_env_text_strips_quotes_and_export():
    parsed = parse_env_text('A="quoted"\nB=\'single\'\nexport C=exported\n')
    assert parsed == {"A": "quoted", "B": "single", "C": "exported"}


def test_parse_env_text_skips_junk_lines():
    parsed = parse_env_text("not a pair\nA=1\n")
    assert parsed == {"A": "1"}


def test_user_config_path_respects_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert user_config_path() == tmp_path / "earwig" / "env"


def test_user_config_path_defaults_under_home(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert user_config_path() == tmp_path / ".config" / "earwig" / "env"


def test_load_dotenv_sets_missing_vars(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("EARWIG_TEST_KEY=from_file\n")
    monkeypatch.delenv("EARWIG_TEST_KEY", raising=False)
    load_dotenv(env)
    assert os.environ["EARWIG_TEST_KEY"] == "from_file"


def test_load_dotenv_real_env_wins(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("EARWIG_TEST_KEY=from_file\n")
    monkeypatch.setenv("EARWIG_TEST_KEY", "from_shell")
    load_dotenv(env)
    assert os.environ["EARWIG_TEST_KEY"] == "from_shell"


def test_load_dotenv_missing_file_is_noop(tmp_path):
    load_dotenv(tmp_path / "nope.env")  # must not raise


def test_load_config_prefers_cwd_env_over_user_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    user = tmp_path / "cfg" / "earwig" / "env"
    user.parent.mkdir(parents=True)
    user.write_text("EARWIG_TEST_KEY=from_user_config\n")
    cwd = tmp_path / ".env"
    cwd.write_text("EARWIG_TEST_KEY=from_cwd\n")
    monkeypatch.delenv("EARWIG_TEST_KEY", raising=False)
    load_config(cwd)
    assert os.environ["EARWIG_TEST_KEY"] == "from_cwd"


def test_load_config_falls_back_to_user_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    user = tmp_path / "cfg" / "earwig" / "env"
    user.parent.mkdir(parents=True)
    user.write_text("EARWIG_TEST_KEY=from_user_config\n")
    monkeypatch.delenv("EARWIG_TEST_KEY", raising=False)
    load_config(tmp_path / "missing.env")
    assert os.environ["EARWIG_TEST_KEY"] == "from_user_config"


def test_load_config_real_env_beats_both_files(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    user = tmp_path / "cfg" / "earwig" / "env"
    user.parent.mkdir(parents=True)
    user.write_text("EARWIG_TEST_KEY=from_user_config\n")
    cwd = tmp_path / ".env"
    cwd.write_text("EARWIG_TEST_KEY=from_cwd\n")
    monkeypatch.setenv("EARWIG_TEST_KEY", "from_shell")
    load_config(cwd)
    assert os.environ["EARWIG_TEST_KEY"] == "from_shell"


def test_upsert_env_var_creates_file_with_0600(tmp_path):
    env = tmp_path / ".env"
    upsert_env_var(env, "HF_TOKEN", "hf_abc")
    assert env.read_text() == "HF_TOKEN=hf_abc\n"
    assert stat.S_IMODE(env.stat().st_mode) == 0o600


def test_upsert_env_var_creates_parent_dirs(tmp_path):
    target = tmp_path / "cfg" / "earwig" / "env"
    upsert_env_var(target, "HF_TOKEN", "hf_abc")
    assert target.read_text() == "HF_TOKEN=hf_abc\n"


def test_upsert_env_var_replaces_existing_key_in_place(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# keep me\nHF_TOKEN=old\nEARWIG_NAMER=heuristic\n")
    upsert_env_var(env, "HF_TOKEN", "new")
    assert env.read_text() == "# keep me\nHF_TOKEN=new\nEARWIG_NAMER=heuristic\n"


def test_upsert_env_var_appends_new_key(tmp_path):
    env = tmp_path / ".env"
    env.write_text("HF_TOKEN=hf_abc\n")
    upsert_env_var(env, "EARWIG_NAMER", "claude")
    assert env.read_text() == "HF_TOKEN=hf_abc\nEARWIG_NAMER=claude\n"
