import urllib.error

import pytest

from earwig.models import Paragraph, NamingError
from earwig.naming import (
    collect_speaker_samples,
    build_prompt,
    parse_mapping,
    infer_names,
    resolve_names,
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


def test_parse_mapping_strips_control_chars_from_names():
    # An LLM (driven by attacker-controlled transcript audio) could return a name
    # laced with ANSI/OSC escapes; strip them so they can't reach the terminal.
    raw = '{"SPEAKER_00": "\\u001b[31mEvil\\u001b[0m", "SPEAKER_01": "Jane"}'
    out = parse_mapping(raw, ["SPEAKER_00", "SPEAKER_01"])
    assert "\x1b" not in (out["SPEAKER_00"] or "")
    assert out["SPEAKER_00"] == "[31mEvil[0m"
    assert out["SPEAKER_01"] == "Jane"


def test_parse_mapping_control_only_name_degrades_to_none():
    raw = '{"SPEAKER_00": "\\u001b\\u0007"}'
    out = parse_mapping(raw, ["SPEAKER_00"])
    assert out["SPEAKER_00"] is None


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


def test_namers_registry_and_choices():
    from earwig.naming import NAMERS, NAMER_CHOICES
    assert set(NAMERS) == {"claude", "local"}
    assert NAMER_CHOICES == ("off", "manual", "claude", "local")


def test_resolve_names_unknown_namer_degrades_to_raw_ids():
    # An unknown namer string must not raise KeyError -- it should degrade
    # to raw speaker ids, same as any other namer failure.
    out = resolve_names(paras(), auto=True, namer="bogus")
    assert out == {"SPEAKER_00": "SPEAKER_00", "SPEAKER_01": "SPEAKER_01"}


def test_resolve_names_defaults_to_off():
    # No namer arg -> off -> raw ids, no inference, no prompts.
    called = False
    def prompt(_):
        nonlocal called
        called = True
        return ""
    out = resolve_names(paras(), prompt_fn=prompt)
    assert out == {"SPEAKER_00": "SPEAKER_00", "SPEAKER_01": "SPEAKER_01"}
    assert called is False


def test_resolve_names_manual_prompts_for_each_speaker():
    answers = iter(["Alice", "Bob Smith"])
    out = resolve_names(paras(), namer="manual", prompt_fn=lambda _: next(answers))
    assert out == {"SPEAKER_00": "Alice", "SPEAKER_01": "Bob Smith"}


def test_resolve_names_manual_empty_entry_keeps_raw_id():
    out = resolve_names(paras(), namer="manual", prompt_fn=lambda _: "")
    assert out == {"SPEAKER_00": "SPEAKER_00", "SPEAKER_01": "SPEAKER_01"}


def test_resolve_names_manual_with_auto_degrades_to_raw_ids():
    # manual has no guesses to apply; --auto (non-interactive) must not prompt.
    def prompt(_):
        raise AssertionError("must not prompt when auto=True")
    out = resolve_names(paras(), namer="manual", auto=True, prompt_fn=prompt)
    assert out == {"SPEAKER_00": "SPEAKER_00", "SPEAKER_01": "SPEAKER_01"}


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


def test_run_ollama_raises_naming_error_on_non_object_json(monkeypatch):
    # A valid JSON array (not an object) must not surface as AttributeError
    # from body.get(...) -- it should degrade to a NamingError like any
    # other malformed-response case.
    def fake_urlopen(req, timeout=None):
        return _FakeResp(b"[1, 2, 3]")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(NamingError):
        _run_ollama("prompt text")
