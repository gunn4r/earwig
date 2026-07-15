from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

from .config import load_config
from .fetch import fetch, sanitize_filename
from .models import PodscribeError
from .naming import NAMER_CHOICES, resolve_names
from .paragraphs import build_paragraphs
from .render import to_markdown
from .setup import run_setup
from .transcribe import transcribe


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="earwig",
        description="Turn a YouTube podcast URL into a speaker-labeled Markdown transcript.",
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--auto", action="store_true",
                        help="apply Claude's speaker names without the confirm step")
    parser.add_argument("--model", default="large-v3",
                        help="Whisper model size (default: large-v3)")
    parser.add_argument("--output", default=None,
                        help="output path (default: ./<sanitized-title>.md)")
    parser.add_argument(
        "--namer", choices=NAMER_CHOICES, default=None,
        help="speaker-naming strategy (default: heuristic, or $EARWIG_NAMER). "
             "auto = claude if installed, else heuristic; off = keep raw SPEAKER_xx labels",
    )
    return parser.parse_args(argv)


def parse_setup_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="earwig setup",
        description="Interactive first-time setup: Hugging Face token, "
                    "prerequisites, and your default namer.",
    )
    parser.add_argument(
        "--namer", choices=NAMER_CHOICES, default=None,
        help="persist this default namer instead of asking",
    )
    parser.add_argument(
        "--no-open-browser", action="store_true",
        help="don't offer to open the Hugging Face pages in a browser",
    )
    return parser.parse_args(argv)


def _setup_command(argv: list[str]) -> int:
    args = parse_setup_args(argv)
    try:
        return run_setup(namer=args.namer, open_browser=not args.no_open_browser)
    except KeyboardInterrupt:
        print("\nSetup cancelled.", file=sys.stderr)
        return 1
    except OSError as exc:  # e.g. the config file is not writable, or another
        # OSError surfaced somewhere in run_setup (e.g. a network check)
        print(f"error: setup failed: {exc}", file=sys.stderr)
        return 1


def _resolve_namer(selected: str | None) -> str:
    name = selected or os.environ.get("EARWIG_NAMER") or "heuristic"
    if name not in NAMER_CHOICES:
        name = "heuristic"
    if name == "auto":
        name = "claude" if shutil.which("claude") else "heuristic"
    return name


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    load_config()
    if argv and argv[0] == "setup":
        return _setup_command(argv[1:])
    args = parse_args(argv)
    try:
        with tempfile.TemporaryDirectory() as workdir:
            print("Downloading audio...", file=sys.stderr)
            audio_path, metadata = fetch(args.url, workdir)
            print(f"Transcribing with {args.model} (this can take a while)...",
                  file=sys.stderr)
            segments = transcribe(audio_path, model_size=args.model)

        paragraphs = build_paragraphs(segments)
        namer = _resolve_namer(args.namer)
        speaker_map = resolve_names(paragraphs, namer=namer, auto=args.auto)

        interactive = not args.auto and namer != "off"
        if interactive:
            print("\nMapping:")
            for sid, name in speaker_map.items():
                print(f"    {sid} -> {name}")
            if input("Write transcript? [Y/n]: ").strip().lower() == "n":
                print("Aborted.", file=sys.stderr)
                return 1

        markdown = to_markdown(metadata, paragraphs, speaker_map)
        out_path = Path(args.output or f"{sanitize_filename(metadata.title)}.md")
        out_path.write_text(markdown, encoding="utf-8")
        print(f"Wrote {out_path}")
        return 0
    except PodscribeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
