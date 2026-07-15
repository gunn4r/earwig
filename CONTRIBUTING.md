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
| `naming` | infer speaker names via a pluggable namer (`--namer`), with confirm / `--auto` / graceful degrade |
| `render` | assemble the Markdown |
| `cli` | argument parsing and orchestration |

Each module has a focused unit-test file in `tests/`. Please keep this separation: pure
logic that can be tested without the heavy models, and thin IO wrappers around the external
tools.

## Changelog

earwig uses [towncrier](https://towncrier.readthedocs.io) news fragments. **Every PR that
changes behavior must add a fragment** in `changelog.d/` — CI fails a PR without one.

Create one file named `<issue>.<type>.md` (or `+<slug>.<type>.md` if there is no issue),
where `<type>` is `feature`, `bugfix`, `removal`, `docs`, or `chore`. The body is the
changelog line. Example:

    echo 'Add a --foo flag to do the thing.' > changelog.d/123.feature.md

Preview what the next release will look like:

    towncrier build --draft --version X.Y.Z

See `changelog.d/README.md` for the type/semver table.

## Releasing

earwig follows [semver](https://semver.org) and is pre-1.0 (beta): `feature`/`removal`
fragments bump the minor, `bugfix` bumps the patch.

1. Ensure the release's fragments are all in `changelog.d/`.
2. Build the changelog: `towncrier build --version X.Y.Z` (compiles fragments into
   `CHANGELOG.md` and deletes them).
3. Bump `version` in `pyproject.toml` to `X.Y.Z`.
4. Reinstall so metadata updates: `pip install -e .` (then `python -c "import earwig;
   print(earwig.__version__)"` should print `X.Y.Z`).
5. Commit, then tag: `git tag vX.Y.Z && git push --tags`.

(Publishing to PyPI and the `earwig update` path are tracked separately.)

## Pull requests

- Keep changes focused and add tests for new behavior.
- Make sure `pytest -q` passes.
- Add a changelog fragment (see Changelog above).
- Describe what changed and why.
