# earwig

[![CI](https://github.com/gunn4r/earwig/actions/workflows/ci.yml/badge.svg)](https://github.com/gunn4r/earwig/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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

## Why

Most transcript tools give you an undifferentiated wall of text. earwig is built for
**conversations** — it separates who is speaking and labels them with real names, so the
output reads like a script. It's aimed at podcasts and interviews.

## Features

- **Runs locally.** Audio download, transcription, and speaker diarization all happen on
  your machine. The only network call besides the download is an optional request to
  `claude -p` to infer speaker names from context — and it sends only a small text slice,
  never the audio.
- **Speaker diarization** via [whisperX](https://github.com/m-bain/whisperX) + `pyannote`.
- **Automatic speaker naming.** Claude reads the transcript and guesses real names from
  intros and context. You review and correct them before anything is written (or `--auto`
  to skip the review).
- **Verbatim output.** Transcript text is never paraphrased — only speaker labels change.
- **Per-paragraph timestamps** you can seek to.

## How it works

```
YouTube URL
  → yt-dlp            download audio + metadata
  → whisperX          transcribe + word timestamps + speaker diarization (SPEAKER_00/01/…)
  → merge             group segments into readable, timestamped paragraphs
  → claude -p         infer real names for the anonymous speakers (review or --auto)
  → render            write speaker-labeled Markdown
```

## Requirements

- **Python 3.11+**
- **ffmpeg** on your `PATH` (`brew install ffmpeg` / `apt install ffmpeg`)
- A **Hugging Face token** (free) for the gated diarization models — see Setup
- The **Claude CLI** (`claude`) on your `PATH`, for the speaker-naming step (optional; use
  `--no-naming` to skip it)

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
    earwig "<url>" --no-naming                     # keep raw SPEAKER_xx labels
    earwig "<url>" --model medium --output ep.md   # faster model, explicit output path

In the default (review) mode, earwig shows a sample line for each detected speaker and
Claude's guessed name; press Enter to accept or type a correction. Assigning the same name
to two speaker IDs merges them — handy when diarization over-splits a speaker.

The default model is `large-v3` (most accurate, slow on CPU). Use `--model base` or
`--model medium` for much faster runs at some cost to transcription quality. A GPU helps a
lot for the larger models.

## Troubleshooting

- **`GatedRepoError` / 403 on a pyannote model** — you haven't accepted that model's terms.
  Open the model page (see Setup) and click "Agree and access repository".
- **`torchcodec` / `libtorchcodec` warning about ffmpeg versions** — harmless. whisperX
  falls back to another audio backend; transcription and diarization still run.
- **A speaker stays `SPEAKER_xx`** — Claude couldn't infer that person's name from context
  (e.g. a host who never says their own name). In review mode, just type it; `--auto` keeps
  the raw label.

## Development

    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    pytest -q                     # fast unit suite (no token/network needed)
    pytest -m slow                # end-to-end test (needs HF_TOKEN, network, ffmpeg)

See [`docs/superpowers/specs`](docs/superpowers/specs) for the design spec and
[`docs/superpowers/plans`](docs/superpowers/plans) for the implementation plan.

## Licensing note

earwig's own code is MIT licensed (see [`LICENSE`](LICENSE)). The `pyannote` diarization
models it downloads have their **own** licenses and gating terms, which you accept during
setup — those govern your use of the models, separately from this tool's license.
