import pytest


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    """Keep the suite off the developer's real config, cwd, and secrets.

    cli.main() calls load_config(), which reads ./.env and the user config
    into os.environ. Without this, a test run would pull the checkout's real
    HF_TOKEN into the process and leave it there for every later test.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("EARWIG_NAMER", raising=False)
    monkeypatch.chdir(tmp_path)
