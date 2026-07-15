# earwig — project guide for Claude

earwig is a local CLI that turns a YouTube podcast URL into a verbatim,
per-paragraph-timestamped, **speaker-labeled** Markdown transcript. Public repo:
`github.com/gunn4r/earwig` (MIT). This file captures project-specific context; the
global `~/.claude/CLAUDE.md` still applies for universal standards.

## Critical environment gotcha

The working directory is `~/r/podscribe`, but the package/CLI/repo are all named
**`earwig`**. **Do not rename the folder** — the `./.venv` has hardcoded paths that
would break. The `podscribe` name is historical only.

## Running it

- Python 3.12 venv at `./.venv`. Run tests with `.venv/bin/pytest -q` (fast unit suite —
  mocks torch/whisperX/yt-dlp, needs no token/network/models).
- `.venv/bin/pytest -m slow` runs the end-to-end integration test — needs `HF_TOKEN`,
  network, and `ffmpeg`.
- Diarization needs `HF_TOKEN` in a gitignored `./.env`, plus accepting two gated HF models
  (`speaker-diarization-community-1`, `segmentation-3.0`). `ffmpeg` must be on `PATH`.

## Architecture

A one-directional pipeline of small, single-purpose modules under `src/earwig/`:

| Module | Responsibility |
|---|---|
| `fetch` | `yt-dlp`: download audio + metadata |
| `transcribe` | `whisperX`: transcription + word timestamps + diarization (whisperX 3.8+ API; imported lazily so unit tests and `--help` stay fast) |
| `paragraphs` | merge segments into readable, timestamped paragraphs |
| `naming` | infer speaker names via a **pluggable namer**, with confirm / `--auto` / graceful degrade |
| `render` | assemble the Markdown |
| `cli` | argument parsing and orchestration |

Keep the separation: pure logic testable without the heavy models, and thin IO wrappers
around external tools. Each module has a focused `tests/test_*.py`.

## Key conventions

- **Pluggable namer** (`src/earwig/naming.py`): `--namer {auto,claude,local,heuristic,off}`
  (default `heuristic`; `EARWIG_NAMER` env overrides the default). Strategies live in the
  `NAMERS` registry; `NAMER_CHOICES` is derived from it, so a new LLM provider is a runner
  fn + one registry line. **Graceful-degradation contract:** `resolve_names` never raises and
  always returns a name per speaker — preserve this.
- **Versioning:** `pyproject.toml` is the single source of truth for the version;
  `src/earwig/__init__.py` derives `__version__` via `importlib.metadata` — **never add a
  hardcoded version literal back.** Semver; pre-1.0/beta (feature/removal → minor,
  bugfix → patch).
- **Changelog:** every behavior-changing PR adds a towncrier fragment in `changelog.d/`
  (`<id>.<type>.md`, types: feature/bugfix/removal/docs/chore). CI (`.github/workflows/ci.yml`)
  fails a PR without one. Releases: `towncrier build --version X.Y.Z` → bump `pyproject.toml`
  → `pip install -e .` → commit → tag `vX.Y.Z`. See `CONTRIBUTING.md`.
- **Git:** never commit on `main`; branch per issue (`{n}-{desc}`). Push to feature branches;
  merge via PR.

## Testing note (divergence from global standard)

The global `~/.claude/CLAUDE.md` describes a `scripts/test_runner.sh` + `test_logs/latest_summary.json`
interface. earwig does **not** use that — it runs `pytest` directly (fast suite by default;
`-m slow` for integration). Read pytest output, not a summary JSON.

## Docs layout

- `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `changelog.d/README.md` — committed.
- `docs/` is **gitignored** (local only): the post-MVP backlog (`docs/TODO-post-mvp.md`, the
  source of truth for remaining §4 work) and the brainstorm/plan specs under
  `docs/superpowers/`. Read `docs/TODO-post-mvp.md` first when picking up new work.
