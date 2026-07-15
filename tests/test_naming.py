import pytest

from earwig.models import Paragraph, NamingError
from earwig.naming import (
    collect_speaker_samples,
    build_prompt,
    parse_mapping,
    infer_names,
    resolve_names,
    heuristic_names,
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
    runner = lambda prompt: '{"SPEAKER_00": "Alice", "SPEAKER_01": null}'
    out = resolve_names(paras(), auto=True, runner=runner)
    assert out == {"SPEAKER_00": "Alice", "SPEAKER_01": "SPEAKER_01"}


def test_resolve_names_no_naming_keeps_raw_ids():
    out = resolve_names(paras(), no_naming=True)
    assert out == {"SPEAKER_00": "SPEAKER_00", "SPEAKER_01": "SPEAKER_01"}


def test_resolve_names_degrades_when_runner_fails():
    def boom(prompt):
        raise NamingError("claude unavailable")
    # auto=True + failure -> every speaker falls back to raw id, no exception
    out = resolve_names(paras(), auto=True, runner=boom)
    assert out == {"SPEAKER_00": "SPEAKER_00", "SPEAKER_01": "SPEAKER_01"}


def test_resolve_names_interactive_prompts_and_overrides():
    runner = lambda prompt: '{"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"}'
    # user accepts Alice (blank -> guess), overrides Bob -> Bob Smith
    answers = iter(["", "Bob Smith"])
    out = resolve_names(paras(), runner=runner, prompt_fn=lambda _: next(answers))
    assert out == {"SPEAKER_00": "Alice", "SPEAKER_01": "Bob Smith"}


def test_resolve_names_auto_degrades_on_value_error():
    """resolve_names must catch non-NamingError exceptions from runner."""
    def boom(prompt):
        raise ValueError("unexpected runner error")
    # auto=True + non-NamingError exception -> every speaker falls back to raw id, no exception
    out = resolve_names(paras(), auto=True, runner=boom)
    assert out == {"SPEAKER_00": "SPEAKER_00", "SPEAKER_01": "SPEAKER_01"}


def test_resolve_names_interactive_degrades_on_value_error():
    """resolve_names interactive path must catch non-NamingError exceptions and still return names."""
    def boom(prompt):
        raise ValueError("unexpected runner error")
    # interactive path with runner failure -> prompt_fn called, blank input -> falls back to raw id
    answers = iter(["", ""])
    out = resolve_names(paras(), runner=boom, prompt_fn=lambda _: next(answers))
    assert out == {"SPEAKER_00": "SPEAKER_00", "SPEAKER_01": "SPEAKER_01"}


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
