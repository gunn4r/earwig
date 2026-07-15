# Changelog

All notable changes to earwig are documented in this file. The format is based on
[Keep a Changelog](https://keepachangelog.com), and this project adheres to
[Semantic Versioning](https://semver.org). While earwig is pre-1.0 (beta), breaking
changes bump the **minor** version.

<!-- towncrier release notes start -->

## [0.2.0] - 2026-07-15

### Features

- Add `--namer {auto,claude,local,heuristic,off}` to choose how speaker names are inferred. The new default `heuristic` namer needs no external tools, so naming no longer requires the Claude CLI. Also adds a `local` namer (via a running Ollama server) and honors the `EARWIG_NAMER` environment variable as the default.

### Removals & Breaking Changes

- Remove the `--no-naming` flag. Use `--namer off` to keep the raw `SPEAKER_xx` labels.


## [0.1.0] - 2026-07-14

Initial beta release: turn a YouTube podcast URL into a speaker-labeled Markdown
transcript (yt-dlp fetch → whisperX transcription + diarization → paragraph merge →
speaker naming → Markdown render).
