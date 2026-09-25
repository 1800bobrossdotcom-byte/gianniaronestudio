# Beyond Measure: build scripts

These scripts render `public/video/beyond-measure/beyond-measure-1080p.mp4`. Run them from a scratch folder (not the repo). Put `song.mp3` in that folder, plus `fonts/` holding TTF copies of `big-shoulders-display-900` and `ibm-plex-mono-500` (convert the woff2 files in `public/fonts` with fontTools).

Requirements: Python 3 with `numpy scipy soundfile opencv-python-headless pillow pymupdf`, plus an ffmpeg that has libx264.

| Step | Script | Output |
| --- | --- | --- |
| 1 | `ffmpeg -i song.mp3 -ac 1 -ar 22050 song.wav && python3 analyze.py` | `feat.json`: per-frame (30fps) loudness, band energies, onsets for kick, snare and hats |
| 2 | `python3 fetch.py` | `clips/`: 3.5s clips cut from public-domain government films on archive.org |
| 3 | `python3 docs.py` | `docs/`: page renders of declassified CIA, NSA and FBI documents |
| 4 | `python3 mosh.py 24` | `mosh/`: real datamoshes (MPEG-4 Part 2 with I-frames dropped and P-frames repeated) |
| 5 | `bash runall.sh` | `master.mp4`: renders four chunks in parallel, concatenates them and muxes in the audio |

The render is deterministic: the director in `render.py` runs off fixed seeds, so the same inputs always produce the same cut.

Web encode: `ffmpeg -i master.mp4 -c:v libx264 -preset slow -b:v 3600k -pass 1/2 -c:a aac -b:a 192k -movflags +faststart`
