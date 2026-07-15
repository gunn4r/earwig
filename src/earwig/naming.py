from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.request
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


# Capitalized non-names that a trigger phrase can accidentally capture.
_STOPWORDS = {
    "I", "So", "Well", "Thanks", "Thank", "Welcome", "Okay", "Ok", "Yeah",
    "Yes", "No", "Here", "Joined", "Great", "Good", "Fine", "Sorry", "Glad",
    "Happy", "Excited", "Going", "Just", "Really", "Not", "Doing", "Today",
    "Back", "Please", "Guest", "Sure", "Right", "Nice",
}

# Trigger phrases where the speaker names THEMSELVES -> attribute to that speaker.
_SELF_TRIGGERS = re.compile(
    r"\b(?:my name'?s?(?: is)?|i'?m|i am|this is)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)",
    re.IGNORECASE,
)
_HERE_TRIGGER = re.compile(r"\b([A-Za-z]+)\s+here\b", re.IGNORECASE)

# Trigger phrases where the speaker names SOMEONE ELSE (a guest) or addresses
# them -> attribute to the next paragraph spoken by a different speaker.
_OTHER_TRIGGERS = re.compile(
    r"\b(?:joined by|welcome(?: back)?|please welcome|my guest(?: today)? is|here'?s)"
    r"\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)",
    re.IGNORECASE,
)
_ADDRESS_TRIGGER = re.compile(r"^([A-Za-z]+),")  # "Marcus, what do you think?"


def _clean_name(raw: str) -> str | None:
    # A name is one or two Titlecase tokens, none of them a stopword.
    parts = raw.split()
    if not (1 <= len(parts) <= 2):
        return None
    if not all(p[:1].isupper() and p[1:].islower() and len(p) > 1 for p in parts):
        return None
    if any(p in _STOPWORDS for p in parts):
        return None
    return " ".join(parts)


def _self_name(text: str) -> str | None:
    m = _SELF_TRIGGERS.search(text)
    if m:
        name = _clean_name(m.group(1))
        if name:
            return name
    m = _HERE_TRIGGER.search(text)
    if m:
        return _clean_name(m.group(1))
    return None


def heuristic_names(paragraphs: list[Paragraph]) -> dict[str, str | None]:
    """Infer speaker names from explicit self-introductions and guest intros.

    Zero-dependency, offline fallback namer. Lower accuracy than an LLM: it only
    catches names stated in a recognizable pattern. Unmatched speakers map to None.
    """
    names: dict[str, str] = {}
    order = list(dict.fromkeys(p.speaker for p in paragraphs))

    def assign_to_next_other(index: int, speaker: str, name: str) -> None:
        for nxt in paragraphs[index + 1:]:
            if nxt.speaker != speaker:
                names.setdefault(nxt.speaker, name)  # never overwrite a self-intro
                return

    for i, para in enumerate(paragraphs):
        if para.speaker not in names:
            name = _self_name(para.text)
            if name:
                names[para.speaker] = name
        for regex in (_OTHER_TRIGGERS, _ADDRESS_TRIGGER):
            m = regex.search(para.text)
            if m:
                other = _clean_name(m.group(1))
                if other:
                    assign_to_next_other(i, para.speaker, other)

    return {sid: names.get(sid) for sid in order}


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

    def clean(value: object) -> str | None:
        # Only accept a non-empty string as a name; anything else (null, number,
        # list, empty string) degrades to None so it can't leak into the transcript.
        return value.strip() if isinstance(value, str) and value.strip() else None

    return {sid: clean(data.get(sid)) for sid in speaker_ids}


def _run_claude(prompt: str) -> str:
    try:
        result = subprocess.run(
            ["claude", "-p", "--model", "haiku", prompt],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NamingError(f"could not run claude: {exc}") from exc
    if result.returncode != 0:
        raise NamingError(result.stderr.strip() or "claude -p failed")
    return result.stdout


OLLAMA_BASE_URL = "http://localhost:11434"
_OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/generate"
_OLLAMA_MODEL = "llama3.2"


def _run_ollama(prompt: str) -> str:
    payload = json.dumps(
        {"model": _OLLAMA_MODEL, "prompt": prompt, "stream": False}
    ).encode("utf-8")
    req = urllib.request.Request(
        _OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise NamingError(f"could not run ollama: {exc}") from exc
    if not isinstance(body, dict):
        raise NamingError(f"unexpected ollama response: {body!r}")
    text = body.get("response")
    if not isinstance(text, str):
        raise NamingError(f"unexpected ollama response: {body!r}")
    return text


def infer_names(
    paragraphs: list[Paragraph],
    runner: Callable[[str], str] | None = None,
) -> dict[str, str | None]:
    runner = runner or _run_claude
    speaker_ids = list(collect_speaker_samples(paragraphs))
    raw = runner(build_prompt(paragraphs))
    return parse_mapping(raw, speaker_ids)


Namer = Callable[[list[Paragraph]], dict[str, str | None]]

NAMERS: dict[str, Namer] = {
    "claude": lambda paras: infer_names(paras, runner=_run_claude),
    "local": lambda paras: infer_names(paras, runner=_run_ollama),
    "heuristic": heuristic_names,
}

# "auto" (pick a namer) and "off" (skip naming) are selection policies, not namers.
NAMER_CHOICES: tuple[str, ...] = ("auto", *NAMERS, "off")


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
    namer: str = "heuristic",
    auto: bool = False,
    prompt_fn: Callable[[str], str] = input,
    namer_fn: Namer | None = None,
) -> dict[str, str]:
    speakers = list(dict.fromkeys(p.speaker for p in paragraphs))
    if namer == "off":
        return {s: s for s in speakers}

    fn = namer_fn or NAMERS.get(namer)
    try:
        if fn is None:
            raise NamingError(f"unknown namer: {namer!r}")
        raw = fn(paragraphs)
        guesses = {s: raw.get(s) for s in speakers}
    except Exception:
        guesses = {s: None for s in speakers}

    if auto:
        return {s: (guesses.get(s) or s) for s in speakers}

    samples = collect_speaker_samples(paragraphs)
    return _confirm_mapping(speakers, guesses, samples, prompt_fn)
