"""Time the written lyrics against the whisper word timestamps.
The displayed text is always the written lyric; whisper only supplies timing."""
import json, re, difflib, sys

NUM = {'4': 'four', '7': 'seven', '8': 'eight', '9': 'nine'}
def norm(w):
    w = w.lower().replace("’", "'")
    w = NUM.get(w, w)
    return re.sub(r"[^a-z0-9']", '', w).strip("'")

lines = [l.rstrip() for l in open('lyrics.txt')]
words = []  # (line_idx, display_word)
for li, l in enumerate(lines):
    for w in l.split():
        if norm(w): words.append((li, w))
ww = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'words_medium.en.json'))
ww = [w for w in ww if norm(w['w'])]
# whisper sometimes glues/splits tokens; normalise both sides token by token
A = [norm(w) for _, w in words]
B = [norm(w['w']) for w in ww]
sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
t0 = [None] * len(A); t1 = [None] * len(A)
for a, b, n in sm.get_matching_blocks():
    for k in range(n):
        t0[a + k] = ww[b + k]['s']; t1[a + k] = ww[b + k]['e']
# fuzzy pass inside replaced spans of equal-ish length
for tag, a0, a1, b0, b1 in sm.get_opcodes():
    if tag == 'replace':
        span = ww[b0:b1]
        for k in range(a0, a1):
            if span:
                j = min(len(span) - 1, int((k - a0) / max(1, a1 - a0) * len(span)))
                t0[k] = span[j]['s']; t1[k] = span[j]['e']
matched = sum(x is not None for x in t0)
# interpolate the rest
idx = [i for i, x in enumerate(t0) if x is not None]
for i in range(len(A)):
    if t0[i] is None:
        prev = max([j for j in idx if j < i], default=None); nxt = min([j for j in idx if j > i], default=None)
        if prev is None: t0[i] = t0[nxt] - 0.3 * (nxt - i); t1[i] = t0[i] + 0.25
        elif nxt is None: t0[i] = t1[prev] + 0.3 * (i - prev); t1[i] = t0[i] + 0.25
        else:
            f = (i - prev) / (nxt - prev); t0[i] = t1[prev] + (t0[nxt] - t1[prev]) * f; t1[i] = t0[i] + 0.2
# enforce monotonic
for i in range(1, len(A)):
    if t0[i] < t0[i - 1]: t0[i] = t0[i - 1] + 0.05
    if t1[i] < t0[i]: t1[i] = t0[i] + 0.15
out = []
for li, l in enumerate(lines):
    ws = [(w, round(t0[i], 3), round(t1[i], 3)) for i, (lj, w) in enumerate(words) if lj == li]
    if ws: out.append({'line': li, 'text': l.strip(), 'words': ws, 'start': ws[0][1], 'end': ws[-1][2]})
json.dump(out, open('timed.json', 'w'), indent=1)
print(f'matched {matched}/{len(A)} words directly')
for o in out: print(f"{o['start']:7.2f} {o['end']:7.2f}  {o['text'][:90]}")
