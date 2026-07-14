from podscribe.fetch import _metadata_from_info, sanitize_filename


def test_metadata_from_info_maps_fields():
    info = {
        "title": "Episode 12: Deep Dive",
        "uploader": "The Pod",
        "duration": 3600,
        "webpage_url": "https://youtu.be/abc",
        "chapters": [{"title": "Intro", "start_time": 0}],
    }
    meta = _metadata_from_info(info)
    assert meta.title == "Episode 12: Deep Dive"
    assert meta.channel == "The Pod"
    assert meta.duration_seconds == 3600
    assert meta.url == "https://youtu.be/abc"
    assert meta.chapters == [{"title": "Intro", "start_time": 0}]


def test_metadata_from_info_handles_missing_fields():
    meta = _metadata_from_info({})
    assert meta.title == "Untitled"
    assert meta.channel == "Unknown"
    assert meta.duration_seconds == 0
    assert meta.chapters == []


def test_sanitize_filename():
    assert sanitize_filename("Episode 12: Deep Dive!") == "episode-12-deep-dive"
    assert sanitize_filename("   ") == "transcript"
    assert len(sanitize_filename("x" * 200)) == 100
