# Semina: build scripts

These scripts render `public/video/semina/semina-1080p.mp4`. Run them in a scratch folder that holds `song.mp3`, `lyrics.txt`, the `fonts/` TTFs (see `scripts/beyond-measure/README.md`) and `../mv/clips` from the Beyond Measure build.

Requirements: `numpy scipy soundfile opencv-python-headless pillow faster-whisper` and an ffmpeg with libx264.

| Step | Script | Output |
| --- | --- | --- |
| 1 | `python3 analyze.py` | `feat.json`: per-frame loudness, bands, onsets, BPM |
| 2 | whisper (`medium.en`, word timestamps) | `words_medium.en.json` |
| 3 | `python3 align.py` | `timed.json`: the written lyrics with per-word times (text comes from `lyrics.txt`, timing from whisper) |
| 4 | `python3 fetch2.py && python3 nasa.py` | `clips/`: public-domain footage, tagged by theme in `tags_all.json` |
| 5 | `python3 textdetect.py`, then review by eye | `review.json`: rejected clips (intertitles, captions, off-topic) and retags |
| 6 | `python3 ../beyond-measure/mosh.py 30` | `mosh/`: datamosh sequences |
| 7 | `bash runall.sh` | `master.mp4` and `web.mp4` |

`themes.py` maps lyric keywords to footage themes. `HOLD_SECT` in `render_sem.py` sets the slow passages, where one image holds for one or two bars and loops on the beat.
