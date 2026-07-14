from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Iterable

from .models import NamingError, Paragraph

_SAMPLE_LEN = 280


def collect_speaker_samples(paragraphs: list[Paragraph]) -> dict[str, str]:
    samples: dict[str, str] = {}
    for para in paragraphs:
        text = para.text.strip()
        if text and para.speaker not in samples:
            samples[para.speaker] = text[:_SAMPLE_LEN]
    return samples


def build_prompt(paragraphs: list[Paragraph], head_seconds: float = 180.0) -> str:
    intro = "\n\n".join(
        f"{p.speaker}: {p.text}" for p in paragraphs if p.start <= head_seconds
    )
    samples = collect_speaker_samples(paragraphs)
    ids = ", ".join(sorted(samples))
    sample_block = "\n".join(f'{sid}: "{quote}"' for sid, quote in sorted(samples.items()))
    return (
        "You are labeling speakers in a podcast transcript.\n"
        f"The anonymous speaker IDs are: {ids}.\n\n"
        "Opening of the conversation:\n"
        f"{intro}\n\n"
        "One sample line per speaker:\n"
        f"{sample_block}\n\n"
        "Infer each speaker's real name from context — self-introductions and "
        "people addressing each other by name. "
        "Respond with ONLY a JSON object mapping each speaker ID to a name string, "
        "or null if you cannot tell. No prose, no code fence.\n"
        'Example: {"SPEAKER_00": "Jane Doe", "SPEAKER_01": null}'
    )


def parse_mapping(raw: str, speaker_ids: Iterable[str]) -> dict[str, str | None]:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise NamingError(f"no JSON object in claude output: {raw!r}")
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise NamingError(f"invalid JSON from claude: {exc}") from exc
    return {sid: (data.get(sid) or None) for sid in speaker_ids}


def _run_claude(prompt: str) -> str:
    try:
        result = subprocess.run(
            ["claude", "-p", "--model", "haiku", prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NamingError(f"could not run claude: {exc}") from exc
    if result.returncode != 0:
        raise NamingError(result.stderr.strip() or "claude -p failed")
    return result.stdout


def infer_names(
    paragraphs: list[Paragraph],
    runner: Callable[[str], str] | None = None,
) -> dict[str, str | None]:
    runner = runner or _run_claude
    speaker_ids = list(collect_speaker_samples(paragraphs))
    raw = runner(build_prompt(paragraphs))
    return parse_mapping(raw, speaker_ids)


def _confirm_mapping(
    speakers: list[str],
    guesses: dict[str, str | None],
    samples: dict[str, str],
    prompt_fn: Callable[[str], str],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for speaker in speakers:
        guess = guesses.get(speaker)
        sample = samples.get(speaker, "")
        print(f"\n{speaker}")
        if sample:
            print(f'  Sample: "{sample[:120]}"')
        label = f"  Name [{guess}]: " if guess else "  Name: "
        entry = prompt_fn(label).strip()
        mapping[speaker] = entry or guess or speaker
    return mapping


def resolve_names(
    paragraphs: list[Paragraph],
    *,
    auto: bool = False,
    no_naming: bool = False,
    runner: Callable[[str], str] | None = None,
    prompt_fn: Callable[[str], str] = input,
) -> dict[str, str]:
    speakers = list(dict.fromkeys(p.speaker for p in paragraphs))
    if no_naming:
        return {s: s for s in speakers}

    try:
        guesses = infer_names(paragraphs, runner=runner)
    except NamingError:
        guesses = {s: None for s in speakers}

    if auto:
        return {s: (guesses.get(s) or s) for s in speakers}

    samples = collect_speaker_samples(paragraphs)
    return _confirm_mapping(speakers, guesses, samples, prompt_fn)
