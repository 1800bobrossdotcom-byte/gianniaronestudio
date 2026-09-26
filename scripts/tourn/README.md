# Tourn: build scripts

This builds on the Semina pipeline (see `scripts/semina/README.md`). `render_trn.py` is `render_sem.py` without the lyric layer. Footage themes follow the song's sections (`SECTIONS`), and chop/hold decisions are made in two-bar units because of the fast tempo.

| Step | Script | Output |
| --- | --- | --- |
| 1 | `python3 ../semina/analyze.py` | `feat.json` |
| 2 | `python3 fetch3.py` | `clips/` and `sources.json`: DVIDS and NASA public-domain footage, tagged by theme |
| 3 | review by eye | `review.json`: rejected clips (titles, logos, talking heads) and retags |
| 4 | `python3 ../beyond-measure/mosh.py 24` | `mosh/` |
| 5 | `bash runall.sh` | `master.mp4` and `web.mp4` |
