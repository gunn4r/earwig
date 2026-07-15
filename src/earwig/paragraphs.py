from __future__ import annotations

from .models import Paragraph, Segment


def build_paragraphs(
    segments: list[Segment],
    *,
    pause_gap: float = 2.0,
    max_seconds: float = 90.0,
    max_words: int = 150,
) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    current: Paragraph | None = None
    prev_end: float | None = None

    for seg in segments:
        text = seg.text.strip()
        if not text:
            prev_end = seg.end
            continue

        should_split = (
            current is None
            or seg.speaker != current.speaker
            or (prev_end is not None and seg.start - prev_end > pause_gap)
            or (seg.start - current.start > max_seconds)
            or (len(current.text.split()) >= max_words)
        )

        if should_split:
            if current is not None:
                paragraphs.append(current)
            current = Paragraph(speaker=seg.speaker, start=seg.start, text=text)
        else:
            current.text = f"{current.text} {text}"

        prev_end = seg.end

    if current is not None:
        paragraphs.append(current)
    return paragraphs
