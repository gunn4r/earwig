from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Metadata:
    title: str
    channel: str
    duration_seconds: int
    url: str
    chapters: list[dict] = field(default_factory=list)


@dataclass
class Segment:
    """A phrase-level unit from whisperX: one speaker, timed, verbatim text."""
    text: str
    start: float
    end: float
    speaker: str


@dataclass
class Paragraph:
    """A merged, readable block. `speaker` holds the raw SPEAKER_xx id until naming."""
    speaker: str
    start: float
    text: str


class PipelineError(Exception):
    """Base class for expected, user-facing failures."""


class FetchError(PipelineError):
    pass


class TranscribeError(PipelineError):
    pass


class NamingError(PipelineError):
    pass
