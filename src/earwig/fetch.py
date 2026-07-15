from __future__ import annotations

import os

from .models import FetchError, Metadata


def _metadata_from_info(info: dict) -> Metadata:
    return Metadata(
        title=info.get("title") or "Untitled",
        channel=info.get("uploader") or info.get("channel") or "Unknown",
        duration_seconds=int(info.get("duration") or 0),
        url=info.get("webpage_url") or info.get("original_url") or "",
        chapters=info.get("chapters") or [],
    )


def sanitize_filename(title: str) -> str:
    kept = "".join(c if (c.isalnum() or c in " -_") else "" for c in title)
    slug = "-".join(kept.split()).strip("-").lower()
    return slug[:100] or "transcript"


def fetch(url: str, workdir: str) -> tuple[str, Metadata]:
    import yt_dlp  # lazy import keeps unit tests and --help fast

    audio_path = os.path.join(workdir, "audio.wav")
    options = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(workdir, "audio.%(ext)s"),
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "wav"}
        ],
        "quiet": True,
        "noprogress": True,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as exc:  # yt-dlp raises many subtypes; surface one clean error
        raise FetchError(f"could not download {url}: {exc}") from exc

    if info is None:  # extract_info can return None rather than raising in rare cases
        raise FetchError(f"could not extract video info for {url}")
    if not os.path.exists(audio_path):
        raise FetchError("audio extraction failed (is ffmpeg installed?)")
    return audio_path, _metadata_from_info(info)
