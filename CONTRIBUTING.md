# Contributing to earwig

Thanks for your interest in improving earwig!

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

`ffmpeg` must be on your `PATH`. For the end-to-end test you also need an `HF_TOKEN`
(see the README's Setup section).

## Running tests

```bash
pytest -q          # fast unit suite — no token, network, or heavy models required
pytest -m slow     # end-to-end integration test (needs HF_TOKEN, network, ffmpeg)
```

The fast suite is what CI runs and what every pull request must pass. The heavy
dependencies (torch / whisperX / pyannote) are only needed for `pytest -m slow` and for
actually running the tool — the unit tests mock them out.

## Architecture

earwig is a one-directional pipeline of small, single-purpose modules under `src/earwig/`:

| Module | Responsibility |
|---|---|
| `fetch` | `yt-dlp`: download audio + metadata |
| `transcribe` | `whisperX`: transcription + word timestamps + diarization |
| `paragraphs` | merge segments into readable, timestamped paragraphs |
| `naming` | infer speaker names via `claude -p`, with confirm / `--auto` / graceful degrade |
| `render` | assemble the Markdown |
| `cli` | argument parsing and orchestration |

Each module has a focused unit-test file in `tests/`. Please keep this separation: pure
logic that can be tested without the heavy models, and thin IO wrappers around the external
tools.

## Pull requests

- Keep changes focused and add tests for new behavior.
- Make sure `pytest -q` passes.
- Describe what changed and why.
