"""earwig: local YouTube podcast to speaker-labeled Markdown transcript."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("earwig")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "unknown"
