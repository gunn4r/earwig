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

## Status

Design phase. See [`docs/superpowers/specs/2026-07-14-podscribe-design.md`](docs/superpowers/specs/2026-07-14-podscribe-design.md).
