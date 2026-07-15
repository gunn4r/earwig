# podscribe

A local CLI that turns a YouTube podcast URL into a verbatim, per-paragraph-timestamped,
speaker-labeled Markdown transcript.

```bash
podscribe "https://youtube.com/watch?v=..."
# → writes ./the-podcast-episode-title.md
```

Transcription and diarization run entirely on your machine (via `yt-dlp` + `whisperX`).
The only network step is an optional call to `claude -p` to infer real speaker names from
context — reviewed by you before anything is written (skip with `--auto`).

## Install

Requires Python 3.11+ and `ffmpeg` on your PATH.

    uv tool install .        # or: pipx install .

## Setup (one time)

Create a free Hugging Face token, accept the terms for the
`pyannote/speaker-diarization` model, then:

    export HF_TOKEN=hf_...

## Usage

    podscribe "https://youtube.com/watch?v=..."      # review speaker names, then writes .md
    podscribe "<url>" --auto                          # skip the review step
    podscribe "<url>" --no-naming                     # keep raw SPEAKER_xx labels
    podscribe "<url>" --model medium --output ep.md   # faster model, explicit path
