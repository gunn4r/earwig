import os
import subprocess
import sys

import pytest

SHORT_CLIP_URL = "https://www.youtube.com/watch?v=6ErnEr2JcD0"  # real validation video


@pytest.mark.slow
@pytest.mark.skipif(not os.environ.get("HF_TOKEN"), reason="needs HF_TOKEN")
def test_end_to_end_produces_transcript(tmp_path):
    out = tmp_path / "out.md"
    result = subprocess.run(
        [sys.executable, "-m", "earwig.cli", SHORT_CLIP_URL,
         "--auto", "--model", "base", "--output", str(out)],
        capture_output=True, text=True, timeout=1800,
    )
    assert result.returncode == 0, result.stderr
    text = out.read_text()
    assert text.startswith("# ")
    assert "`[" in text  # at least one timestamped paragraph
