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


def _compute_type(device: str) -> str:
    # faster-whisper/CTranslate2 backend: float16 is the standard on CUDA,
    # int8 keeps CPU runs tractable.
    return "float16" if device == "cuda" else "int8"


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
            "HF_TOKEN is not set. Run `earwig setup` to create a Hugging Face token, "
            "accept the two gated pyannote model licenses, and save the token — or set "
            "HF_TOKEN yourself if you'd rather do it by hand."
        )

    import whisperx  # imported lazily so unit tests and --help stay fast
    from whisperx.diarize import DiarizationPipeline  # moved off top level in whisperX 3.8+

    model = whisperx.load_model(model_size, device, compute_type=_compute_type(device))
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio)

    align_model, align_meta = whisperx.load_align_model(
        language_code=result["language"], device=device
    )
    result = whisperx.align(
        result["segments"], align_model, align_meta, audio, device,
        return_char_alignments=False,
    )

    # whisperX 3.8+: DiarizationPipeline lives in whisperx.diarize and takes token=.
    # Pin the model explicitly so behavior is deterministic across whisperX versions
    # (its default has drifted). community-1 is the current pyannote pipeline; note that
    # with pyannote-audio 4.x even the older 3.1 pipeline pulls community-1 components,
    # so this is the model whose terms the user must accept.
    diarizer = DiarizationPipeline(
        model_name="pyannote/speaker-diarization-community-1",
        token=hf_token,
        device=device,
    )
    diarize_segments = diarizer(audio)
    result = whisperx.assign_word_speakers(diarize_segments, result)

    return _segments_from_whisperx(result)
