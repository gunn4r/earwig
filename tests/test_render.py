from podscribe.models import Metadata, Paragraph
from podscribe.render import format_timestamp, to_markdown


def test_format_timestamp_under_hour():
    assert format_timestamp(0) == "00:00"
    assert format_timestamp(42) == "00:42"
    assert format_timestamp(605) == "10:05"


def test_format_timestamp_over_hour():
    assert format_timestamp(3723) == "1:02:03"


def test_to_markdown_uses_names_and_falls_back_to_raw_id():
    meta = Metadata(title="Ep 1", channel="The Pod", duration_seconds=3723,
                    url="https://youtu.be/x")
    paras = [
        Paragraph(speaker="SPEAKER_00", start=0.0, text="Welcome back."),
        Paragraph(speaker="SPEAKER_01", start=42.0, text="Glad to be here."),
    ]
    md = to_markdown(meta, paras, {"SPEAKER_00": "Alice"})
    assert "# Ep 1" in md
    assert "*The Pod · 1:02:03 · [source](https://youtu.be/x)*" in md
    assert "**Alice** `[00:00]`" in md
    assert "Welcome back." in md
    # SPEAKER_01 not in the map -> raw id preserved, never dropped
    assert "**SPEAKER_01** `[00:42]`" in md
    assert md.endswith("\n")
