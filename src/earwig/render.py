from __future__ import annotations

import unicodedata
from urllib.parse import quote

from .models import Metadata, Paragraph

# URL characters left untouched inside a `[source](...)` target. Everything else
# — notably `(`, `)`, `<`, `>`, `"`, whitespace and controls — is percent-encoded
# so a crafted metadata URL can't close the link early or inject markup.
_URL_SAFE = "/:?#[]@!$&'*+,;=~._-%"


def _escape_inline(text: str) -> str:
    """Neutralize untrusted text placed in Markdown inline/body context.

    title, channel, body text and speaker names are all attacker-influenced
    (yt-dlp metadata, the spoken transcript, LLM name guesses). Drop control
    characters (so terminal/OSC escapes can't survive into a rendered file) and
    neutralize the metacharacters that would otherwise inject raw HTML
    (`<`/`>`/`&` -> entities) or Markdown link/code structure (`\\`, `` ` ``,
    `[`, `]` -> backslash-escaped)."""
    out: list[str] = []
    for ch in text:
        if unicodedata.category(ch) == "Cc":
            continue
        if ch == "&":
            out.append("&amp;")
        elif ch == "<":
            out.append("&lt;")
        elif ch == ">":
            out.append("&gt;")
        elif ch in "\\`[]":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def _safe_url(url: str) -> str | None:
    """Return a percent-encoded http(s) URL safe to use as a Markdown link
    target, or None when `url` isn't a plain web URL (so it's rendered as text
    instead of an active — possibly `javascript:` — link)."""
    if not (url.startswith("https://") or url.startswith("http://")):
        return None
    return quote(url, safe=_URL_SAFE)


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
    url = _safe_url(metadata.url)
    source = f"[source]({url})" if url else "source"
    lines: list[str] = [
        f"# {_escape_inline(metadata.title)}",
        "",
        f"*{_escape_inline(metadata.channel)} · {duration} · {source}*",
        "",
        "---",
        "",
    ]
    for block in _merge_same_speaker(paragraphs, speaker_map):
        name = _escape_inline(block["name"])
        lines.append(f"**{name}** `[{format_timestamp(block['start'])}]`")
        lines.append(_escape_inline(block["text"]))
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
