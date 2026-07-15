import urllib.error

import pytest

from earwig.models import Paragraph, NamingError
from earwig.naming import (
    collect_speaker_samples,
    build_prompt,
    parse_mapping,
    infer_names,
    resolve_names,
    heuristic_names,
    _run_ollama,
)


def paras():
    return [
        Paragraph(speaker="SPEAKER_00", start=0.0, text="Welcome, I'm Alice."),
        Paragraph(speaker="SPEAKER_01", start=5.0, text="Thanks Alice, I'm Bob."),
        Paragraph(speaker="SPEAKER_00", start=10.0, text="So Bob, tell us more."),
    ]


def test_collect_speaker_samples_first_quote_per_speaker():
    samples = collect_speaker_samples(paras())
    assert samples["SPEAKER_00"] == "Welcome, I'm Alice."
    assert samples["SPEAKER_01"] == "Thanks Alice, I'm Bob."


def test_build_prompt_mentions_ids_and_demands_json():
    prompt = build_prompt(paras())
    assert "SPEAKER_00" in prompt and "SPEAKER_01" in prompt
    assert "JSON" in prompt


def test_parse_mapping_plain_json():
    raw = '{"SPEAKER_00": "Alice", "SPEAKER_01": null}'
    out = parse_mapping(raw, ["SPEAKER_00", "SPEAKER_01"])
    assert out == {"SPEAKER_00": "Alice", "SPEAKER_01": None}


def test_parse_mapping_tolerates_code_fence_and_prose():
    raw = 'Sure!\n```json\n{"SPEAKER_00": "Alice"}\n```'
    out = parse_mapping(raw, ["SPEAKER_00"])
    assert out == {"SPEAKER_00": "Alice"}


def test_parse_mapping_raises_without_object():
    with pytest.raises(NamingError):
        parse_mapping("no json here", ["SPEAKER_00"])


def test_parse_mapping_rejects_non_string_and_empty_values():
    raw = '{"SPEAKER_00": 42, "SPEAKER_01": ["a"], "SPEAKER_02": "  ", "SPEAKER_03": "Kyle"}'
    out = parse_mapping(raw, ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02", "SPEAKER_03"])
    # numbers, lists, and whitespace-only names degrade to None; real names are kept (trimmed)
    assert out == {
        "SPEAKER_00": None,
        "SPEAKER_01": None,
        "SPEAKER_02": None,
        "SPEAKER_03": "Kyle",
    }


def test_infer_names_uses_injected_runner():
    runner = lambda prompt: '{"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"}'
    out = infer_names(paras(), runner=runner)
    assert out == {"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"}


def test_resolve_names_auto_applies_guesses_and_falls_back_for_null():
    namer_fn = lambda paras: {"SPEAKER_00": "Alice", "SPEAKER_01": None}
    out = resolve_names(paras(), auto=True, namer_fn=namer_fn)
    assert out == {"SPEAKER_00": "Alice", "SPEAKER_01": "SPEAKER_01"}


def test_resolve_names_off_keeps_raw_ids():
    out = resolve_names(paras(), namer="off")
    assert out == {"SPEAKER_00": "SPEAKER_00", "SPEAKER_01": "SPEAKER_01"}


def test_resolve_names_degrades_when_namer_fails():
    def boom(paras):
        raise NamingError("namer unavailable")
    out = resolve_names(paras(), auto=True, namer_fn=boom)
    assert out == {"SPEAKER_00": "SPEAKER_00", "SPEAKER_01": "SPEAKER_01"}


def test_resolve_names_interactive_prompts_and_overrides():
    namer_fn = lambda paras: {"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"}
    answers = iter(["", "Bob Smith"])
    out = resolve_names(paras(), namer_fn=namer_fn, prompt_fn=lambda _: next(answers))
    assert out == {"SPEAKER_00": "Alice", "SPEAKER_01": "Bob Smith"}


def test_resolve_names_auto_degrades_on_value_error():
    """resolve_names must catch non-NamingError exceptions from the namer."""
    def boom(paras):
        raise ValueError("unexpected namer error")
    out = resolve_names(paras(), auto=True, namer_fn=boom)
    assert out == {"SPEAKER_00": "SPEAKER_00", "SPEAKER_01": "SPEAKER_01"}


def test_resolve_names_interactive_degrades_on_value_error():
    """Interactive path must catch non-NamingError exceptions and still return names."""
    def boom(paras):
        raise ValueError("unexpected namer error")
    answers = iter(["", ""])
    out = resolve_names(paras(), namer_fn=boom, prompt_fn=lambda _: next(answers))
    assert out == {"SPEAKER_00": "SPEAKER_00", "SPEAKER_01": "SPEAKER_01"}


def test_namers_registry_has_concrete_strategies():
    from earwig.naming import NAMERS, NAMER_CHOICES
    assert set(NAMERS) == {"claude", "local", "heuristic"}
    assert NAMER_CHOICES == ("auto", "claude", "local", "heuristic", "off")


def test_resolve_names_defaults_to_heuristic():
    # No namer_fn, no namer arg -> uses the heuristic namer on real text.
    out = resolve_names(paras(), auto=True)
    assert out == {"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"}


def test_heuristic_self_introduction():
    p = [
        Paragraph(speaker="SPEAKER_00", start=0.0, text="Welcome, I'm Alice."),
        Paragraph(speaker="SPEAKER_01", start=5.0, text="Thanks Alice, I'm Bob."),
    ]
    assert heuristic_names(p) == {"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"}


def test_heuristic_my_name_is_and_here():
    p = [
        Paragraph(speaker="SPEAKER_00", start=0.0, text="My name is Sarah Chen."),
        Paragraph(speaker="SPEAKER_01", start=5.0, text="Dave here, good to be on."),
    ]
    assert heuristic_names(p) == {"SPEAKER_00": "Sarah Chen", "SPEAKER_01": "Dave"}


def test_heuristic_guest_intro_maps_to_next_speaker():
    p = [
        Paragraph(speaker="SPEAKER_00", start=0.0, text="Today I'm joined by Marcus."),
        Paragraph(speaker="SPEAKER_01", start=5.0, text="Great to be here."),
    ]
    assert heuristic_names(p) == {"SPEAKER_00": None, "SPEAKER_01": "Marcus"}


def test_heuristic_no_match_returns_none():
    p = [
        Paragraph(speaker="SPEAKER_00", start=0.0, text="So anyway, the weather was nice."),
        Paragraph(speaker="SPEAKER_01", start=5.0, text="Yeah, totally."),
    ]
    assert heuristic_names(p) == {"SPEAKER_00": None, "SPEAKER_01": None}


def test_heuristic_rejects_capitalized_non_names():
    # "I'm Great" must not become the name "Great"; sentence-initial "So" is not a name.
    p = [
        Paragraph(speaker="SPEAKER_00", start=0.0, text="I'm Great, thanks for asking."),
        Paragraph(speaker="SPEAKER_01", start=5.0, text="So, where were we?"),
    ]
    assert heuristic_names(p) == {"SPEAKER_00": None, "SPEAKER_01": None}


def test_heuristic_self_intro_wins_over_later_mention():
    p = [
        Paragraph(speaker="SPEAKER_00", start=0.0, text="I'm Alice."),
        Paragraph(speaker="SPEAKER_01", start=5.0, text="I'm joined by Alice's twin."),
    ]
    # SPEAKER_00 keeps Alice; the "joined by" does not overwrite an existing name.
    out = heuristic_names(p)
    assert out["SPEAKER_00"] == "Alice"


class _FakeResp:
    def __init__(self, body: bytes):
        self._body = body
    def read(self):
        return self._body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def test_run_ollama_returns_response_field(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["data"] = req.data
        return _FakeResp(b'{"response": "{\\"SPEAKER_00\\": \\"Alice\\"}"}')

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    out = _run_ollama("prompt text")
    assert out == '{"SPEAKER_00": "Alice"}'
    assert b"prompt text" in captured["data"]


def test_run_ollama_raises_naming_error_when_unreachable(monkeypatch):
    def boom(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(NamingError):
        _run_ollama("prompt text")
