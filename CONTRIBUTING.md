# Contributing to earwig

Thanks for your interest in improving earwig!

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

`ffmpeg` must be on your `PATH`. For the end-to-end test you also need an `HF_TOKEN` — run `earwig setup` to get one and check your prerequisites, or see the README's Setup section to do it by hand.

## Running tests

```bash
pytest -q          # fast unit suite — no token, network, or heavy models required
pytest -m slow     # end-to-end integration test (needs HF_TOKEN, network, ffmpeg)
```

The fast suite is what CI runs and what every pull request must pass. The heavy dependencies (torch / whisperX / pyannote) are only needed for `pytest -m slow` and for actually running the tool — the unit tests mock them out.

## Architecture

earwig is a one-directional pipeline of small, single-purpose modules under `src/earwig/`:

| Module | Responsibility |
|---|---|
| `fetch` | `yt-dlp`: download audio + metadata |
| `transcribe` | `whisperX`: transcription + word timestamps + diarization |
| `paragraphs` | merge segments into readable, timestamped paragraphs |
| `naming` | infer speaker names via a pluggable namer (`--namer`), with confirm / `--auto` / graceful degrade |
| `render` | assemble the Markdown |
| `config` | read/write the env files that hold settings (`HF_TOKEN`, `EARWIG_NAMER`) |
| `setup` | the `earwig setup` wizard: token walkthrough plus fast prerequisite checks |
| `cli` | argument parsing and orchestration |

Each module has a focused unit-test file in `tests/`. Please keep this separation: pure logic that can be tested without the heavy models, and thin IO wrappers around the external tools.

`config` and `setup` follow the same rule as the rest: `setup`'s checks are small functions returning a `CheckResult`, each mockable on its own, and they use only stdlib `urllib`/`shutil` — no whisperX import and no model download, so the fast suite covers them fully. Settings are read with the precedence documented in the README: the environment, then `./.env`, then the per-user config. Only earwig's own keys are loaded from those files.

## Changelog

earwig uses [towncrier](https://towncrier.readthedocs.io) news fragments. **Every PR that changes behavior must add a fragment** in `changelog.d/` — CI fails a PR without one.

Create one file named `<issue>.<type>.md` (or `+<slug>.<type>.md` if there is no issue), where `<type>` is `feature`, `bugfix`, `removal`, `docs`, or `chore`. The body is the changelog line. Example:

    echo 'Add a --foo flag to do the thing.' > changelog.d/123.feature.md

Preview what the next release will look like:

    towncrier build --draft --version X.Y.Z

See `changelog.d/README.md` for the type/semver table.

## Releasing

earwig follows [semver](https://semver.org) and is pre-1.0 (beta): `feature`/`removal` fragments bump the minor, `bugfix` bumps the patch.

The easy path is the release script, which does the whole sequence (build changelog → bump version → reinstall → commit → tag) and stops short of pushing so you can review:

```bash
./scripts/release.sh 0.3.0 --dry-run   # preview the changelog only, change nothing
./scripts/release.sh 0.3.0             # cut the release locally
git push && git push origin v0.3.0     # publish once you're happy
```

It's a maintainer tool (POSIX bash — macOS/Linux; on Windows use WSL/Git Bash or the manual steps below). Under the hood it does exactly this, which you can also run by hand:

1. Ensure the release's fragments are all in `changelog.d/`.
2. Build the changelog: `towncrier build --version X.Y.Z` (compiles fragments into `CHANGELOG.md` and deletes them).
3. Bump `version` in `pyproject.toml` to `X.Y.Z`.
4. Reinstall so metadata updates: `pip install -e .` (then `python -c "import earwig; print(earwig.__version__)"` should print `X.Y.Z`).
5. Commit, then tag: `git tag vX.Y.Z && git push --tags`.

(Publishing to PyPI and the `earwig update` path are tracked separately.)

## Pull requests

- Keep changes focused and add tests for new behavior.
- Make sure `pytest -q` passes.
- Add a changelog fragment (see Changelog above).
- Describe what changed and why.
