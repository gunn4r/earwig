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

A local command-line tool that turns a YouTube podcast URL into a **verbatim, per-paragraph-timestamped, speaker-labeled Markdown transcript**.

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

> The example above is fictional. See [`examples/example-transcript.md`](examples/example-transcript.md) for a fuller synthetic sample of earwig's output.

> **Status:** beta (`0.x`) — pre-1.0, so flags and output may still change. Release history lives in [`CHANGELOG.md`](CHANGELOG.md).

## Why

Most transcript tools give you an undifferentiated wall of text. earwig is built for **conversations** — it separates who is speaking and labels them with real names, so the output reads like a script. It's aimed at podcasts and interviews.

## Features

- **Runs locally.** Audio download, transcription, and speaker diarization all happen on your machine. Speaker naming is off by default (no network call at all). The optional `claude` and `local` namers send only a small text slice (never the audio) to `claude -p` or a local Ollama server, respectively.
- **Speaker diarization** via [whisperX](https://github.com/m-bain/whisperX) + `pyannote`.
- **Opt-in speaker naming.** By default speakers keep their anonymous `SPEAKER_xx` labels. Opt into names with `--namer manual` (type them yourself as you review) or the `claude`/`local` LLM namers, which infer names from intros and context. You review and correct names before anything is written (or `--auto` to skip the review).
- **Verbatim output.** Transcript text is never paraphrased — only speaker labels change.
- **Per-paragraph timestamps** you can seek to.

## How it works

```
YouTube URL
  → yt-dlp            download audio + metadata
  → whisperX          transcribe + word timestamps + speaker diarization (SPEAKER_00/01/…)
  → merge             group segments into readable, timestamped paragraphs
  → namer             optionally label the anonymous speakers (off by default;
                       manual/claude/local opt-in; review or --auto)
  → render            write speaker-labeled Markdown
```

## Requirements

- **Python 3.11+**
- **ffmpeg** on your `PATH` (`brew install ffmpeg` / `apt install ffmpeg`)
- A **Hugging Face token** (free) for the gated diarization models — see Setup
- Nothing else for speaker naming — it's off by default, and `--namer manual` (type names yourself) needs no dependencies. Optionally, the **Claude CLI** (`claude`) on your `PATH` enables `--namer claude`, and a local [Ollama](https://ollama.com) server on `localhost:11434` enables `--namer local`. See [Speaker naming](#speaker-naming).

## Install

The one-line installer sets everything up — it installs earwig with [uv](https://docs.astral.sh/uv/) (or pipx), warns you if `ffmpeg` is missing, and launches `earwig setup`:

    curl -fsSL https://raw.githubusercontent.com/gunn4r/earwig/main/install.sh | sh

It's safe to re-run (it upgrades in place) and never uses `sudo`. On a machine with neither uv nor pipx it tells you how to get uv rather than installing anything behind your back.

Prefer to run it yourself? Install straight from git:

    uv tool install git+https://github.com/gunn4r/earwig@main     # or: pipx install git+https://github.com/gunn4r/earwig@main

(From a local checkout, `uv tool install .` works too.)

### Updating and uninstalling

`earwig update` upgrades in place — it detects how earwig was installed (uv tool, pipx, or pip) and runs the matching upgrade, pulling the latest build from `main`. If you're running from a source checkout, it tells you to `git pull` instead. Check what you're on with `earwig --version`.

To remove it, use the same tool that installed it — e.g. `uv tool uninstall earwig` or `pipx uninstall earwig`.

## Compatibility

- **macOS (Apple Silicon):** confirmed working end-to-end (the development machine, Python 3.12).
- **macOS (Intel):** unverified, but expected to work — it uses the same wheels.
- **Linux:** the fast unit suite runs in CI on Python 3.11 and 3.12. The full torch/whisperX/pyannote pipeline ships Linux wheels and is expected to work, but has not yet been run end-to-end here.
- **Windows:** unverified and likely rough (torch and ffmpeg pathing). Use [WSL2](https://learn.microsoft.com/windows/wsl/install) and follow the Linux path.
- **Python:** 3.11 and 3.12 are tested (the CI matrix). 3.13 is not yet supported (dependency wheel availability); 3.12 is the safe pick.
- **Hardware / GPU:** CPU works but is slow — the default `large-v3` model runs roughly 10–30+ minutes per hour of audio. Use `--model base` or `--model medium` to trade some accuracy for a much faster run. On an NVIDIA GPU, `--device cuda` speeds transcription substantially (it uses `float16`). Apple Silicon transcribes on CPU regardless: the underlying faster-whisper/CTranslate2 backend has no Apple-GPU support, which is why there is no `mps` option. The `--device cuda` path is implemented against whisperX's documented API but has not yet been verified on real CUDA hardware.

## Setup (one time)

Run the setup wizard — it explains what's needed, opens the right pages, stores your token, and verifies everything:

    earwig setup

It walks you through creating a free [Hugging Face token](https://huggingface.co/settings/tokens) and accepting the licenses for the two gated models that speaker diarization needs, saves the token to `~/.config/earwig/env` (mode `0600`, never printed), records your default speaker namer, and then checks that `ffmpeg` is installed, your token works, both model licenses are accepted, and your namer is available. Every failed check tells you exactly what to do about it.

`earwig setup --namer off` skips the namer question, and `--no-open-browser` stops it from opening pages for you.

### Where settings live

earwig reads settings from, in order of precedence: the environment, a `.env` file in the current directory, then `~/.config/earwig/env` (or `$XDG_CONFIG_HOME/earwig/env`). `earwig setup` writes the last one, so an installed `earwig` works from any directory; a `.env` in a checkout is handy for development and overrides it.

### Doing it by hand

If you'd rather not use the wizard: create a [Hugging Face token](https://huggingface.co/settings/tokens), click "Agree and access repository" on both

- https://huggingface.co/pyannote/speaker-diarization-community-1
- https://huggingface.co/pyannote/segmentation-3.0

then either export the token or put it in one of the files above:

    export HF_TOKEN=hf_...
    # or: echo 'HF_TOKEN=hf_...' >> .env

`ffmpeg` must also be on your `PATH` (macOS: `brew install ffmpeg`; Debian/Ubuntu: `sudo apt install ffmpeg`).

## Usage

    earwig "https://youtube.com/watch?v=..."      # default: raw SPEAKER_xx labels, writes .md
    earwig "<url>" --namer manual                  # type each speaker's name as you review
    earwig "<url>" --namer claude                  # use the Claude CLI to infer names
    earwig "<url>" --namer local                   # use a local Ollama model to infer names
    earwig "<url>" --namer claude --auto           # infer names, skip the review step
    earwig "<url>" --namer off                     # explicit no-naming (same as default)
    earwig "<url>" --model medium --output ep.md   # faster model, explicit output path
    earwig "<url>" --device cuda                    # transcribe on an NVIDIA GPU (much faster)
    earwig --version                               # print the installed version
    earwig update                                  # upgrade earwig to the latest build

By default earwig writes the transcript non-interactively with anonymous `SPEAKER_xx` labels. When you opt into a namer (`manual`, `claude`, or `local`), review mode shows a sample line for each detected speaker and its guessed name; press Enter to accept or type a correction (add `--auto` to skip the review). Assigning the same name to two speaker IDs merges them — handy when diarization over-splits a speaker.

The default model is `large-v3` (most accurate, slow on CPU). Use `--model base` or `--model medium` for much faster runs at some cost to transcription quality. A GPU helps a lot for the larger models.

## Speaker naming

Naming is opt-in. earwig selects a strategy with `--namer {off,manual,claude,local}`:

- **`off`** (the default) — skip naming and keep the raw `SPEAKER_xx` labels, non-interactively. Nothing is guessed, so a wrong name can never ship.
- **`manual`** — no inference: earwig prompts you to type each speaker's name as you review the samples. Zero dependencies, fully offline.
- **`claude`** — shells out to the [Claude CLI](https://github.com/anthropics/claude-code) (`claude -p`) with a small text slice from the transcript. Requires the `claude` CLI on your `PATH`, authenticated.
- **`local`** — sends the same kind of prompt to a local [Ollama](https://ollama.com) server (`http://localhost:11434`). Requires Ollama running with a model pulled.

Earlier versions shipped a `heuristic` regex namer and an `auto` mode; both were removed because regex name-inference wasn't accurate enough to trust (a wrong name is worse than none). A persisted `EARWIG_NAMER=heuristic`/`auto` now warns and falls back to `off`.

If `--namer` is omitted, earwig checks the `EARWIG_NAMER` environment variable, then falls back to `off`. Both `claude` and `local` degrade gracefully to raw speaker ids if the underlying service is unavailable at runtime — they never crash the run. `earwig setup` records your choice for you, so you don't have to set `EARWIG_NAMER` by hand.

## Troubleshooting

- **`GatedRepoError` / 403 on a pyannote model** — you haven't accepted that model's terms. Open the model page (see Setup) and click "Agree and access repository".
- **`torchcodec` / `libtorchcodec` warning about ffmpeg versions** — harmless. whisperX falls back to another audio backend; transcription and diarization still run.
- **A speaker stays `SPEAKER_xx`** — expected under the default `--namer off`. It also happens when a `claude`/`local` namer couldn't infer that person's name (e.g. a host who never says their own name) or the service was unreachable and degraded to raw labels. To label speakers, re-run with `--namer manual` (type them) or `--namer claude`/`local`; in review mode just type the name (`--auto` keeps whatever was guessed).

## Development

    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    pytest -q                     # fast unit suite (no token/network needed)
    pytest -m slow                # end-to-end test (needs HF_TOKEN, network, ffmpeg)

## Licensing note

earwig's own code is MIT licensed (see [`LICENSE`](LICENSE)). The `pyannote` diarization models it downloads have their **own** licenses and gating terms, which you accept during setup — those govern your use of the models, separately from this tool's license.
