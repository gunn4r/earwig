from __future__ import annotations

import os

from .models import Segment, TranscribeError


def _segments_from_whisperx(result: dict) -> list[Segment]:
    segments: list[Segment] = []
    for raw in result.get("segments", []):
        text = (raw.get("text") or "").strip()
        if not text:
            continue
        segments.append(
            Segment(
                text=text,
                start=float(raw["start"]),
                end=float(raw["end"]),
                speaker=raw.get("speaker") or "SPEAKER_UNKNOWN",
            )
        )
    return segments


def transcribe(
    audio_path: str,
    *,
    model_size: str = "large-v3",
    hf_token: str | None = None,
    device: str = "cpu",
) -> list[Segment]:
    hf_token = hf_token or os.environ.get("HF_TOKEN")
    if not hf_token:
        raise TranscribeError(
            "HF_TOKEN is not set. Create a free Hugging Face token, accept the "
            "pyannote/speaker-diarization model terms, and export HF_TOKEN=... "
            "(one-time setup)."
        )

    import whisperx  # imported lazily so unit tests and --help stay fast

    model = whisperx.load_model(model_size, device, compute_type="int8")
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio)

    align_model, align_meta = whisperx.load_align_model(
        language_code=result["language"], device=device
    )
    result = whisperx.align(
        result["segments"], align_model, align_meta, audio, device,
        return_char_alignments=False,
    )

    diarizer = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
    diarize_segments = diarizer(audio)
    result = whisperx.assign_word_speakers(diarize_segments, result)

    return _segments_from_whisperx(result)
