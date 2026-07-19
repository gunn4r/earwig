# Changelog

All notable changes to earwig are documented in this file. The format is based on
[Keep a Changelog](https://keepachangelog.com), and this project adheres to
[Semantic Versioning](https://semver.org). While earwig is pre-1.0 (beta), breaking
changes bump the **minor** version.

<!-- towncrier release notes start -->

## [0.3.0] - 2026-07-18

### Features

- Added a `manual` namer (`--namer manual`) that prompts you to type each speaker's name interactively, with no LLM or inference required. Names remain available via `--namer claude` / `--namer local`. ([#10](https://github.com/gunn4r/earwig/issues/10))
- Added `earwig update`, which detects how earwig was installed (uv tool, pipx, or pip) and runs the matching upgrade; a source checkout is told to `git pull`. Added `earwig --version` (and an `earwig version` subcommand) to print the installed version. ([#12](https://github.com/gunn4r/earwig/issues/12))
- Added a `--device {cpu,cuda}` flag to pick the compute device for transcription and diarization (default `cpu`; `cuda` uses `float16` on an NVIDIA GPU). There is no `mps` option — the faster-whisper backend has no Apple-GPU support, so Apple Silicon transcribes on CPU. ([#14](https://github.com/gunn4r/earwig/issues/14))
- Add `earwig setup`, an interactive wizard that walks you through the Hugging Face token, stores it in `~/.config/earwig/env` without echoing it, records your default namer, and verifies ffmpeg, your token, both gated model licenses, and your namer with actionable errors. earwig now reads that config file and `./.env` at startup, so the token file the README has always described actually works.
- Add a one-line installer: `curl -fsSL https://raw.githubusercontent.com/gunn4r/earwig/main/install.sh | sh` installs earwig from git with uv or pipx, warns if `ffmpeg` is missing, and launches `earwig setup`.

### Bug Fixes

- Escape untrusted text at the Markdown render boundary. Video title, channel, source URL, speaker names, and transcript body — all attacker-influenced — are now neutralized before they're written to the output file: HTML/Markdown metacharacters are escaped, control characters (including terminal/ANSI escapes) are stripped, and the `[source](...)` URL is validated as `http(s)` and percent-encoded so a crafted URL can't break out of the link. LLM-inferred speaker names are likewise stripped of control characters before they reach the interactive confirm prompt. Closes the output-injection finding from the §4.6 security audit. ([#18](https://github.com/gunn4r/earwig/issues/18))

### Removals & Breaking Changes

- Removed the `heuristic` speaker namer and the `auto` namer policy. Regex name-inference could not be made accurate enough to be safe (a wrong name is worse than none), so naming is now opt-in and the default is `off` (speakers keep their `SPEAKER_xx` labels). A persisted `EARWIG_NAMER=heuristic`/`auto` now warns and falls back to `off`. ([#10](https://github.com/gunn4r/earwig/issues/10))

### Documentation

- Add a `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1, linked from `CONTRIBUTING.md`) and tidy the README: drop the stale "earlier versions did X" naming note, trim internal-sounding compatibility phrasing, and document the trust model for the downloaded pyannote models.
- Add a project `CLAUDE.md` guide and note beta/pre-1.0 status plus a changelog link in the README.
- Document the `config` and `setup` modules in CONTRIBUTING.md's architecture guide, and point the contributor dev-setup at `earwig setup`.
- Unwrap hard-wrapped prose in `README.md`, `CONTRIBUTING.md`, and `changelog.d/README.md` so each paragraph is a single line — no wording changed, only line breaks.

### Internal / Chores

- Pin the tested dependency ranges: `whisperx>=3.8,<3.9` and `pyannote-audio>=4,<5`, since whisperX's diarization API and default model drift across minor versions. `yt-dlp` is intentionally left uncapped so it keeps pace with YouTube changes. ([#16](https://github.com/gunn4r/earwig/issues/16))
- Harden the CI workflow: declare a top-level least-privilege `permissions: contents: read` (all jobs only read the repo), and pass `github.base_ref` to the changelog check through an `env:` variable instead of interpolating it directly into the `run:` script. Defense-in-depth from the §4.6 security audit; no functional change. ([#17](https://github.com/gunn4r/earwig/issues/17))
- Add `scripts/release.sh` to cut a release in one step (build changelog, bump version, reinstall, commit, tag), with a `--dry-run` preview.
- Keep the local `CLAUDE.md` agent guide private (gitignored); public contributor conventions live in `CONTRIBUTING.md`.


## [0.2.0] - 2026-07-15

### Features

- Add `--namer {auto,claude,local,heuristic,off}` to choose how speaker names are inferred. The new default `heuristic` namer needs no external tools, so naming no longer requires the Claude CLI. Also adds a `local` namer (via a running Ollama server) and honors the `EARWIG_NAMER` environment variable as the default.

### Removals & Breaking Changes

- Remove the `--no-naming` flag. Use `--namer off` to keep the raw `SPEAKER_xx` labels.

## [0.1.0] - 2026-07-14

Initial beta release: turn a YouTube podcast URL into a speaker-labeled Markdown
transcript (yt-dlp fetch → whisperX transcription + diarization → paragraph merge →
speaker naming → Markdown render).
