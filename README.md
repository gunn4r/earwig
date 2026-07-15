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

Speaker diarization uses gated Hugging Face models. Create a free Hugging Face token,
then click "Agree and access repository" on both:

- https://huggingface.co/pyannote/speaker-diarization-community-1
- https://huggingface.co/pyannote/segmentation-3.0

Then make the token available (either export it, or put `HF_TOKEN=hf_...` in a `.env`
file in the project root):

    export HF_TOKEN=hf_...

## Usage

    podscribe "https://youtube.com/watch?v=..."      # review speaker names, then writes .md
    podscribe "<url>" --auto                          # skip the review step
    podscribe "<url>" --no-naming                     # keep raw SPEAKER_xx labels
    podscribe "<url>" --model medium --output ep.md   # faster model, explicit path

The default model is `large-v3` (most accurate, slow on CPU). Use `--model base` or
`--model medium` for much faster runs at some cost to transcription quality.

## Troubleshooting

- **`GatedRepoError` / 403 on a pyannote model** — you haven't accepted that model's terms
  yet. Open the model page (see Setup) and click "Agree and access repository".
- **`torchcodec` / `libtorchcodec` warning about ffmpeg versions** — harmless. whisperX
  falls back to another audio backend; transcription and diarization still run.
