from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from .fetch import fetch, sanitize_filename
from .models import PodscribeError
from .naming import resolve_names
from .paragraphs import build_paragraphs
from .render import to_markdown
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
    parser.add_argument("--no-naming", action="store_true",
                        help="skip name inference; keep raw SPEAKER_xx labels")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        with tempfile.TemporaryDirectory() as workdir:
            print("Downloading audio...", file=sys.stderr)
            audio_path, metadata = fetch(args.url, workdir)
            print(f"Transcribing with {args.model} (this can take a while)...",
                  file=sys.stderr)
            segments = transcribe(audio_path, model_size=args.model)

        paragraphs = build_paragraphs(segments)
        speaker_map = resolve_names(
            paragraphs, auto=args.auto, no_naming=args.no_naming
        )

        interactive = not args.auto and not args.no_naming
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
