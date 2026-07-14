from podscribe.models import Segment
from podscribe.paragraphs import build_paragraphs


def seg(text, start, end, speaker):
    return Segment(text=text, start=start, end=end, speaker=speaker)


def test_merges_same_speaker_contiguous():
    segs = [
        seg("Hello there.", 0.0, 1.0, "SPEAKER_00"),
        seg("How are you?", 1.2, 2.0, "SPEAKER_00"),
    ]
    paras = build_paragraphs(segs)
    assert len(paras) == 1
    assert paras[0].text == "Hello there. How are you?"
    assert paras[0].start == 0.0
    assert paras[0].speaker == "SPEAKER_00"


def test_splits_on_speaker_change():
    segs = [
        seg("Question?", 0.0, 1.0, "SPEAKER_00"),
        seg("Answer.", 1.1, 2.0, "SPEAKER_01"),
    ]
    paras = build_paragraphs(segs)
    assert [p.speaker for p in paras] == ["SPEAKER_00", "SPEAKER_01"]
    assert paras[1].start == 1.1


def test_splits_on_long_pause():
    segs = [
        seg("Before the break.", 0.0, 1.0, "SPEAKER_00"),
        seg("After a long pause.", 5.0, 6.0, "SPEAKER_00"),  # 4s gap > 2s
    ]
    paras = build_paragraphs(segs)
    assert len(paras) == 2


def test_splits_on_max_seconds():
    segs = [
        seg("Start.", 0.0, 1.0, "SPEAKER_00"),
        seg("Still talking.", 95.0, 96.0, "SPEAKER_00"),  # 95s span > 90s (also >pause)
    ]
    paras = build_paragraphs(segs, pause_gap=1000.0)  # isolate the max_seconds rule
    assert len(paras) == 2


def test_splits_on_max_words():
    long_seg = seg(" ".join(["word"] * 200), 0.0, 5.0, "SPEAKER_00")
    follow = seg("next.", 5.5, 6.0, "SPEAKER_00")
    paras = build_paragraphs([long_seg, follow])
    assert len(paras) == 2


def test_empty_input():
    assert build_paragraphs([]) == []
