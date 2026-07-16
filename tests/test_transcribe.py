import pytest

from earwig.models import TranscribeError
from earwig.transcribe import _segments_from_whisperx, transcribe


def test_segments_from_whisperx_maps_fields():
    result = {
        "segments": [
            {"text": " Hello there. ", "start": 0.0, "end": 1.5, "speaker": "SPEAKER_00"},
            {"text": "Hi.", "start": 1.6, "end": 2.0, "speaker": "SPEAKER_01"},
        ]
    }
    segs = _segments_from_whisperx(result)
    assert len(segs) == 2
    assert segs[0].text == "Hello there."
    assert segs[0].speaker == "SPEAKER_00"
    assert segs[1].start == 1.6


def test_segments_from_whisperx_skips_empty_and_defaults_speaker():
    result = {
        "segments": [
            {"text": "   ", "start": 0.0, "end": 0.5, "speaker": "SPEAKER_00"},
            {"text": "No speaker key.", "start": 0.6, "end": 1.0},
        ]
    }
    segs = _segments_from_whisperx(result)
    assert len(segs) == 1
    assert segs[0].speaker == "SPEAKER_UNKNOWN"


def test_transcribe_requires_hf_token(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with pytest.raises(TranscribeError, match="HF_TOKEN"):
        transcribe("/nonexistent/audio.wav")


def test_transcribe_hf_token_error_points_at_setup(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with pytest.raises(TranscribeError, match="earwig setup"):
        transcribe("/nonexistent/audio.wav")
