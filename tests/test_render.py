from earwig.models import Metadata, Paragraph
from earwig.render import format_timestamp, to_markdown


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


def _meta():
    return Metadata(title="T", channel="C", duration_seconds=60, url="u")


def test_merges_adjacent_different_ids_with_same_name():
    # Diarization split one person into two IDs; both map to "Chris" -> one block.
    paras = [
        Paragraph(speaker="SPEAKER_00", start=0.0, text="First part."),
        Paragraph(speaker="SPEAKER_02", start=5.0, text="Second part."),
    ]
    md = to_markdown(_meta(), paras, {"SPEAKER_00": "Chris", "SPEAKER_02": "Chris"})
    assert md.count("**Chris**") == 1
    assert "First part. Second part." in md
    assert "`[00:00]`" in md  # keeps the first paragraph's timestamp
    assert "`[00:05]`" not in md


def test_does_not_merge_same_id_pause_or_length_splits():
    # Same ID split by build_paragraphs (pause/length) -> stays two blocks so the
    # anti-wall-of-text guard still holds.
    paras = [
        Paragraph(speaker="SPEAKER_00", start=0.0, text="Long block one."),
        Paragraph(speaker="SPEAKER_00", start=95.0, text="Long block two."),
    ]
    md = to_markdown(_meta(), paras, {"SPEAKER_00": "Chris"})
    assert md.count("**Chris**") == 2
    assert "`[00:00]`" in md and "`[01:35]`" in md


def test_does_not_merge_different_names():
    paras = [
        Paragraph(speaker="SPEAKER_00", start=0.0, text="Question?"),
        Paragraph(speaker="SPEAKER_01", start=3.0, text="Answer."),
    ]
    md = to_markdown(_meta(), paras, {"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"})
    assert md.count("**Alice**") == 1 and md.count("**Bob**") == 1


def test_merges_interleaved_same_name_across_ids():
    # A, B, A all resolve to "Chris" -> single coalesced block.
    paras = [
        Paragraph(speaker="SPEAKER_00", start=0.0, text="One."),
        Paragraph(speaker="SPEAKER_01", start=2.0, text="Two."),
        Paragraph(speaker="SPEAKER_00", start=4.0, text="Three."),
    ]
    md = to_markdown(_meta(), paras, {"SPEAKER_00": "Chris", "SPEAKER_01": "Chris"})
    assert md.count("**Chris**") == 1
    assert "One. Two. Three." in md


# --- untrusted-input escaping (issue #15) -----------------------------------
# title/channel come verbatim from yt-dlp, body text from the spoken transcript,
# and names can come from an LLM whose input is that transcript. All are
# attacker-controlled and must be neutralized at the Markdown render boundary.


def test_escapes_html_in_title_and_channel():
    meta = Metadata(title='<img src=x onerror="alert(1)">', channel="A & B <b>",
                    duration_seconds=60, url="https://e/x")
    md = to_markdown(meta, [Paragraph("SPEAKER_00", 0.0, "hi")], {})
    assert "<img" not in md
    assert "&lt;img src=x onerror=" in md
    assert "A &amp; B &lt;b&gt;" in md


def test_escapes_link_and_code_syntax_in_body_and_name():
    paras = [Paragraph("SPEAKER_00", 0.0, "see [here](javascript:alert) and `code`")]
    md = to_markdown(_meta(), paras, {"SPEAKER_00": "[x](javascript:1)"})
    # javascript survives as literal text but never as an active link/code span
    assert "[here](" not in md
    assert "\\[here\\](javascript:alert)" in md
    assert "\\`code\\`" in md
    assert "**\\[x\\](javascript:1)**" in md


def test_url_breakout_is_neutralized():
    meta = Metadata(title="T", channel="C", duration_seconds=60,
                    url="https://e/x)evil")
    md = to_markdown(meta, [Paragraph("SPEAKER_00", 0.0, "hi")], {})
    # the ) is percent-encoded so it cannot close the [source](...) link early
    assert "https://e/x%29evil" in md
    assert "x)evil" not in md


def test_non_http_url_is_not_linked():
    meta = Metadata(title="T", channel="C", duration_seconds=60,
                    url="javascript:alert(1)")
    md = to_markdown(meta, [Paragraph("SPEAKER_00", 0.0, "hi")], {})
    assert "javascript:" not in md
    assert "· source*" in md  # rendered as plain text, no link target


def test_strips_control_chars_from_rendered_text():
    paras = [Paragraph("SPEAKER_00", 0.0, "a\x1b[31mred\x1b[0m")]
    md = to_markdown(_meta(), paras, {"SPEAKER_00": "N\x1bame"})
    assert "\x1b" not in md
