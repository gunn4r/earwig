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
    for para in paragraphs:
        name = speaker_map.get(para.speaker, para.speaker)
        lines.append(f"**{name}** `[{format_timestamp(para.start)}]`")
        lines.append(para.text)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
