<p align="center">
  <img src="assets/icon.svg" width="120" alt="earwig">
</p>

<h1 align="center">earwig</h1>

<p align="center">
  <a href="https://github.com/gunn4r/earwig/actions/workflows/ci.yml"><img src="https://github.com/gunn4r/earwig/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/version-0.2.0-blue.svg" alt="Version 0.2.0"></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/status-beta-orange.svg" alt="Status: beta"></a>
</p>

> _earwig_ (v.) — to listen in on a conversation.

A local command-line tool that turns a YouTube podcast URL into a **verbatim,
per-paragraph-timestamped, speaker-labeled Markdown transcript**.

```bash
earwig "https://youtube.com/watch?v=..."
# → writes ./the-podcast-episode-title.md
```

```markdown
# How I Built a $40K/Month Vending Machine Route
*The Small Bets Podcast · 32:10 · [source](https://youtube.com/watch?v=EXAMPLE)*

---

**Dana Alvarez** `[00:00]`
Welcome back to the show. Today I'm sitting down with someone who turned a
boring, overlooked business into a genuinely passive income stream...

**Marcus Webb** `[00:12]`
Thanks for having me. The whole thing started because I wanted something that
didn't need me glued to a laptop all day...
```

> The example above is fictional. See [`examples/example-transcript.md`](examples/example-transcript.md)
> for a fuller synthetic sample of earwig's output.

> **Status:** beta (`0.x`) — pre-1.0, so flags and output may still change. Release history
> lives in [`CHANGELOG.md`](CHANGELOG.md).

## Why

Most transcript tools give you an undifferentiated wall of text. earwig is built for
**conversations** — it separates who is speaking and labels them with real names, so the
output reads like a script. It's aimed at podcasts and interviews.

## Features

- **Runs locally.** Audio download, transcription, and speaker diarization all happen on
  your machine. The default speaker namer (`heuristic`) is a zero-dependency, offline regex
  matcher — no network call at all. The optional `claude` and `local` namers send only a
  small text slice (never the audio) to `claude -p` or a local Ollama server, respectively.
- **Speaker diarization** via [whisperX](https://github.com/m-bain/whisperX) + `pyannote`.
- **Automatic speaker naming.** A pluggable namer guesses real names from intros and
  context — the built-in `heuristic` namer by default, or the optional `claude`/`local`
  LLM namers for better accuracy. You review and correct names before anything is written
  (or `--auto` to skip the review).
- **Verbatim output.** Transcript text is never paraphrased — only speaker labels change.
- **Per-paragraph timestamps** you can seek to.

## How it works

```
YouTube URL
  → yt-dlp            download audio + metadata
  → whisperX          transcribe + word timestamps + speaker diarization (SPEAKER_00/01/…)
  → merge             group segments into readable, timestamped paragraphs
  → namer             infer real names for the anonymous speakers (heuristic default;
                       claude/local optional; review or --auto)
  → render            write speaker-labeled Markdown
```

## Requirements

- **Python 3.11+**
- **ffmpeg** on your `PATH` (`brew install ffmpeg` / `apt install ffmpeg`)
- A **Hugging Face token** (free) for the gated diarization models — see Setup
- Nothing else for speaker naming — the default `heuristic` namer is bundled and offline.
  Optionally, the **Claude CLI** (`claude`) on your `PATH` enables `--namer claude`, and a
  local [Ollama](https://ollama.com) server on `localhost:11434` enables `--namer local`.
  See [Speaker naming](#speaker-naming).

## Install

    uv tool install .        # or: pipx install .

## Setup (one time)

Speaker diarization uses gated Hugging Face models. Create a free
[Hugging Face token](https://huggingface.co/settings/tokens), then click
"Agree and access repository" on both:

- https://huggingface.co/pyannote/speaker-diarization-community-1
- https://huggingface.co/pyannote/segmentation-3.0

Then make the token available (export it, or put `HF_TOKEN=hf_...` in a `.env` file in the
project root):

    export HF_TOKEN=hf_...

## Usage

    earwig "https://youtube.com/watch?v=..."      # review speaker names, then writes .md
    earwig "<url>" --auto                          # skip the review step
    earwig "<url>" --namer off                     # keep raw SPEAKER_xx labels
    earwig "<url>" --namer heuristic               # zero-dependency regex namer (default)
    earwig "<url>" --namer claude                  # use the Claude CLI to guess names
    earwig "<url>" --namer local                   # use a local Ollama model to guess names
    earwig "<url>" --model medium --output ep.md   # faster model, explicit output path

In the default (review) mode, earwig shows a sample line for each detected speaker and
the namer's guessed name; press Enter to accept or type a correction. Assigning the same
name to two speaker IDs merges them — handy when diarization over-splits a speaker.

The default model is `large-v3` (most accurate, slow on CPU). Use `--model base` or
`--model medium` for much faster runs at some cost to transcription quality. A GPU helps a
lot for the larger models.

## Speaker naming

earwig ships four speaker-naming strategies plus an `auto` selection mode, selected with `--namer {auto,claude,local,heuristic,off}`:

- **`heuristic`** (the default) — a zero-dependency regex matcher that looks for
  self-introductions and guest introductions/direct-address ("I'm Dana", "welcome, Marcus")
  to infer names. Runs fully offline, no external process or network call.
- **`claude`** — shells out to the [Claude CLI](https://github.com/anthropics/claude-code)
  (`claude -p`) with a small text slice from the transcript. Requires the `claude` CLI on your
  `PATH`, authenticated.
- **`local`** — sends the same kind of prompt to a local [Ollama](https://ollama.com)
  server (`http://localhost:11434`). Requires Ollama running with a model pulled.
- **`off`** — skip naming entirely and keep the raw `SPEAKER_xx` labels non-interactively.
- **`auto`** — use `claude` if the Claude CLI is installed, otherwise fall back to
  `heuristic`.

If `--namer` is omitted, earwig checks the `EARWIG_NAMER` environment variable, then falls
back to `heuristic`. Both `claude` and `local` degrade gracefully to raw speaker ids if the
underlying service is unavailable at runtime — they never crash the run. A future
`earwig setup` command will let you choose and persist a default namer instead of setting
`EARWIG_NAMER` by hand.

## Troubleshooting

- **`GatedRepoError` / 403 on a pyannote model** — you haven't accepted that model's terms.
  Open the model page (see Setup) and click "Agree and access repository".
- **`torchcodec` / `libtorchcodec` warning about ffmpeg versions** — harmless. whisperX
  falls back to another audio backend; transcription and diarization still run.
- **A speaker stays `SPEAKER_xx`** — the namer couldn't infer that person's name from
  context (e.g. a host who never says their own name), or `--namer off`/an unreachable
  `claude`/`local` service degraded to raw labels. In review mode, just type it; `--auto`
  keeps the raw label.

## Development

    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    pytest -q                     # fast unit suite (no token/network needed)
    pytest -m slow                # end-to-end test (needs HF_TOKEN, network, ffmpeg)

## Licensing note

earwig's own code is MIT licensed (see [`LICENSE`](LICENSE)). The `pyannote` diarization
models it downloads have their **own** licenses and gating terms, which you accept during
setup — those govern your use of the models, separately from this tool's license.
