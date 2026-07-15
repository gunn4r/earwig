import re
from importlib.metadata import version
from pathlib import Path

import earwig


def test_version_matches_installed_metadata():
    assert earwig.__version__ == version("earwig")


def test_version_is_nonempty_string():
    assert isinstance(earwig.__version__, str) and earwig.__version__


def test_no_hardcoded_version_literal():
    # __version__ must be DERIVED, not a literal like `__version__ = "1.2.3"`,
    # so the pyproject version stays the single source of truth.
    src = Path(earwig.__file__).read_text(encoding="utf-8")
    assert not re.search(r'__version__\s*=\s*[\'"]\d', src)
