import earwig.cli as cli
from earwig.models import Metadata, Paragraph, Segment, FetchError


def test_parse_args_defaults():
    args = cli.parse_args(["https://youtu.be/x"])
    assert args.url == "https://youtu.be/x"
    assert args.auto is False
    assert args.model == "large-v3"
    assert args.no_naming is False


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
