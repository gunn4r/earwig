import earwig.cli as cli
from earwig.models import Metadata, Paragraph, Segment, FetchError


def test_parse_args_defaults():
    args = cli.parse_args(["https://youtu.be/x"])
    assert args.url == "https://youtu.be/x"
    assert args.auto is False
    assert args.model == "large-v3"
    assert args.namer is None


def test_parse_args_namer_choice():
    args = cli.parse_args(["u", "--namer", "off"])
    assert args.namer == "off"


def test_resolve_namer_defaults_to_heuristic(monkeypatch):
    monkeypatch.delenv("EARWIG_NAMER", raising=False)
    assert cli._resolve_namer(None) == "heuristic"


def test_resolve_namer_reads_env(monkeypatch):
    monkeypatch.setenv("EARWIG_NAMER", "local")
    assert cli._resolve_namer(None) == "local"


def test_resolve_namer_explicit_flag_beats_env(monkeypatch):
    monkeypatch.setenv("EARWIG_NAMER", "local")
    assert cli._resolve_namer("heuristic") == "heuristic"


def test_resolve_namer_auto_prefers_claude_when_present(monkeypatch):
    monkeypatch.delenv("EARWIG_NAMER", raising=False)
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/claude")
    assert cli._resolve_namer("auto") == "claude"


def test_resolve_namer_auto_falls_back_to_heuristic(monkeypatch):
    monkeypatch.delenv("EARWIG_NAMER", raising=False)
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    assert cli._resolve_namer("auto") == "heuristic"


def test_resolve_namer_invalid_env_falls_back_to_heuristic(monkeypatch):
    monkeypatch.setenv("EARWIG_NAMER", "bogus")
    assert cli._resolve_namer(None) == "heuristic"


def test_main_writes_transcript(tmp_path, monkeypatch, capsys):
    out = tmp_path / "episode.md"
    meta = Metadata(title="Ep", channel="Pod", duration_seconds=60, url="u")

    monkeypatch.setattr(cli, "fetch", lambda url, workdir: ("/fake/audio.wav", meta))
    monkeypatch.setattr(
        cli, "transcribe",
        lambda audio, model_size: [Segment("Hi there.", 0.0, 1.0, "SPEAKER_00")],
    )
    monkeypatch.setattr(cli, "resolve_names", lambda paras, **kw: {"SPEAKER_00": "Alice"})

    code = cli.main(["u", "--auto", "--output", str(out)])
    assert code == 0
    text = out.read_text()
    assert "**Alice** `[00:00]`" in text
    assert "Hi there." in text


def test_main_handles_fetch_error(monkeypatch, capsys):
    def boom(url, workdir):
        raise FetchError("video unavailable")
    monkeypatch.setattr(cli, "fetch", boom)

    code = cli.main(["u", "--auto"])
    assert code == 1
    assert "video unavailable" in capsys.readouterr().err


def test_main_namer_off_skips_confirm_prompt(tmp_path, monkeypatch, capsys):
    # With --namer off, `interactive` is False, so input() must never be
    # called -- verify by making input() raise if it's ever invoked.
    out = tmp_path / "e.md"
    meta = Metadata(title="Ep", channel="Pod", duration_seconds=60, url="u")

    monkeypatch.setattr(cli, "fetch", lambda url, workdir: ("/fake/audio.wav", meta))
    monkeypatch.setattr(
        cli, "transcribe",
        lambda audio, model_size: [Segment("Hi there.", 0.0, 1.0, "SPEAKER_00")],
    )
    monkeypatch.setattr(cli, "resolve_names", lambda paras, **kw: {"SPEAKER_00": "SPEAKER_00"})

    def no_prompt(prompt=""):
        raise AssertionError("input() must not be called when --namer off")

    monkeypatch.setattr("builtins.input", no_prompt)

    code = cli.main(["u", "--namer", "off", "--output", str(out)])
    assert code == 0
    assert out.exists()


def test_main_interactive_abort_writes_nothing(tmp_path, monkeypatch, capsys):
    # Interactive mode (no --auto): answering 'n' at the [Y/n] gate must abort
    # with exit 1 and never create the output file.
    out = tmp_path / "episode.md"
    meta = Metadata(title="Ep", channel="Pod", duration_seconds=60, url="u")

    monkeypatch.setattr(cli, "fetch", lambda url, workdir: ("/fake/audio.wav", meta))
    monkeypatch.setattr(
        cli, "transcribe",
        lambda audio, model_size: [Segment("Hi there.", 0.0, 1.0, "SPEAKER_00")],
    )
    monkeypatch.setattr(cli, "resolve_names", lambda paras, **kw: {"SPEAKER_00": "Alice"})
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")

    code = cli.main(["u", "--output", str(out)])
    assert code == 1
    assert not out.exists()
    assert "Aborted" in capsys.readouterr().err


def test_parse_setup_args_defaults():
    args = cli.parse_setup_args([])
    assert args.namer is None
    assert args.no_open_browser is False


def test_parse_setup_args_accepts_namer_and_browser_flag():
    args = cli.parse_setup_args(["--namer", "claude", "--no-open-browser"])
    assert args.namer == "claude"
    assert args.no_open_browser is True


def test_main_dispatches_setup(monkeypatch):
    seen = {}

    def fake_run_setup(**kwargs):
        seen.update(kwargs)
        return 0

    monkeypatch.setattr(cli, "run_setup", fake_run_setup)
    assert cli.main(["setup", "--namer", "local"]) == 0
    assert seen["namer"] == "local"
    assert seen["open_browser"] is True


def test_main_setup_honors_no_open_browser(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "run_setup", lambda **kw: seen.update(kw) or 0)
    cli.main(["setup", "--no-open-browser"])
    assert seen["open_browser"] is False


def test_main_setup_propagates_failure_code(monkeypatch):
    monkeypatch.setattr(cli, "run_setup", lambda **kw: 1)
    assert cli.main(["setup"]) == 1


def test_main_setup_does_not_transcribe(monkeypatch):
    monkeypatch.setattr(cli, "run_setup", lambda **kw: 0)

    def explode(*a, **kw):
        raise AssertionError("transcribe path must not run for `earwig setup`")

    monkeypatch.setattr(cli, "fetch", explode)
    assert cli.main(["setup"]) == 0


def test_main_setup_reports_unwritable_config(monkeypatch, capsys):
    def boom(**kwargs):
        raise OSError("read-only file system")

    monkeypatch.setattr(cli, "run_setup", boom)
    assert cli.main(["setup"]) == 1
    assert "read-only file system" in capsys.readouterr().err


def test_main_loads_config(monkeypatch):
    called = []
    monkeypatch.setattr(cli, "load_config", lambda: called.append(True))
    monkeypatch.setattr(cli, "run_setup", lambda **kw: 0)
    cli.main(["setup"])
    assert called == [True]
