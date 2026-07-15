from __future__ import annotations

from .models import Metadata, Paragraph


def format_timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def to_markdown(
    metadata: Metadata,
    paragraphs: list[Paragraph],
    speaker_map: dict[str, str],
) -> str:
    duration = format_timestamp(metadata.duration_seconds)
    lines: list[str] = [
        f"# {metadata.title}",
        "",
        f"*{metadata.channel} · {duration} · [source]({metadata.url})*",
        "",
        "---",
        "",
    ]
    for block in _merge_same_speaker(paragraphs, speaker_map):
        lines.append(f"**{block['name']}** `[{format_timestamp(block['start'])}]`")
        lines.append(block["text"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _merge_same_speaker(
    paragraphs: list[Paragraph],
    speaker_map: dict[str, str],
) -> list[dict]:
    """Group paragraphs into render blocks, coalescing consecutive paragraphs that
    resolve to the SAME name but came from DIFFERENT speaker IDs.

    This fixes diarization over-splitting one person into several IDs that the user
    (or Claude) then maps to a single name — they render as one block instead of
    repeated identical headers. A single ID's own paragraphs (split by pause or
    max-length in `build_paragraphs`) are left untouched, so that readability guard
    still holds.
    """
    blocks: list[dict] = []
    prev_id: str | None = None
    for para in paragraphs:
        name = speaker_map.get(para.speaker, para.speaker)
        if blocks and name == blocks[-1]["name"] and para.speaker != prev_id:
            blocks[-1]["text"] = f"{blocks[-1]['text']} {para.text}"
        else:
            blocks.append({"name": name, "start": para.start, "text": para.text})
        prev_id = para.speaker
    return blocks
