from earwig.models import Metadata, Segment, Paragraph, FetchError, PipelineError


def test_dataclasses_construct():
    m = Metadata(title="T", channel="C", duration_seconds=10, url="u")
    assert m.chapters == []
    s = Segment(text="hi", start=0.0, end=1.0, speaker="SPEAKER_00")
    assert s.speaker == "SPEAKER_00"
    p = Paragraph(speaker="SPEAKER_00", start=0.0, text="hi")
    assert p.text == "hi"


def test_exception_hierarchy():
    assert issubclass(FetchError, PipelineError)
