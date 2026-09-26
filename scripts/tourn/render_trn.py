"""SEMINA: audio-reactive lyric video.
usage: python3 render_sem.py <start_frame> <end_frame> <out.mp4>"""
import numpy as np, cv2, json, glob, random, subprocess, sys, os, re
from scipy.ndimage import uniform_filter1d
from PIL import Image, ImageDraw, ImageFont
from themes import tags_for

W, H, FPS = 1280, 720, 30
F = json.load(open('feat.json')); N = F['n']
A = lambda k: np.array(F[k], np.float32)
rms, flux, sub, mid, high = map(A, ['rms', 'flux', 'sub', 'mid', 'high'])

def pulses(on, strength, decay, thr):
    e = np.zeros(N, np.float32); hit = np.zeros(N, bool); v = 0.0
    s = {i for i in on if strength[i] > thr}
    for i in range(N):
        if i in s: v = max(v * decay, 0.4 + 0.6 * strength[i]); hit[i] = True
        else: v *= decay
        e[i] = v
    return e, hit
kick, kick_hit = pulses(F['on_sub'], sub, 0.70, 0.30)
snare, snare_hit = pulses(F['on_mid'], mid, 0.62, 0.30)
hat, hat_hit = pulses(F['on_high'], high, 0.50, 0.22)
_, any_hit = pulses(F['on'], flux, 0.5, 0.15)
energy = uniform_filter1d(rms, 45)
inten = np.clip((energy - 0.22) / 0.42, 0, 1)
OUTRO_FADE = N - 5 * FPS

# ---------------------------------------------------------------- lyrics
LY = json.load(open('timed.json'))
for k, l in enumerate(LY):
    nxt = LY[k + 1]['start'] if k + 1 < len(LY) else l['end'] + 3
    l['hold'] = min(nxt - 0.05, l['end'] + 2.2)   # stays up until the next line (or ~2s of silence)
    l['tags'] = tags_for(l['text'])
line_at = np.full(N, -1)
for k, l in enumerate(LY):
    a = int(max(0, l['start'] - 0.12) * FPS); b = int(l['hold'] * FPS); line_at[a:b] = k
# themes stay "sticky" through gaps: last line's tags until the next line
theme_line = np.full(N, -1); cur = -1
for i in range(N):
    if line_at[i] >= 0: cur = line_at[i]
    elif cur >= 0 and i / FPS - LY[cur]['hold'] > 4: cur = -1   # long instrumental: drift into abstraction
    theme_line[i] = cur

# ---------------------------------------------------------------- sources
SRC = {x['id']: x for x in json.load(open('sources.json'))}
TAGS = {k: v['tag'] for k, v in SRC.items()}
def ident(p): return re.sub(r'__\d+\.mp4$', '', os.path.basename(p))
CLIPS = sorted(glob.glob('clips/*.mp4'))
REV = json.load(open('review.json')) if os.path.exists('review.json') else {'reject': [], 'retag': {}}
BAD = set(REV['reject'])
CLIPS = [c for c in CLIPS if ident(c) in TAGS and os.path.basename(c) not in BAD]
MOSH = sorted(glob.glob('mosh/*.mp4'))
POOL = {}
for c in CLIPS:
    for t in REV['retag'].get(os.path.basename(c), TAGS[ident(c)]).split(): POOL.setdefault(t, []).append(c)
nframes = {}
def count(p):
    if p not in nframes:
        c = cv2.VideoCapture(p); nframes[p] = int(c.get(cv2.CAP_PROP_FRAME_COUNT)); c.release()
    return nframes[p]

def grad(stops):
    xs = np.linspace(0, 1, len(stops)); x = np.linspace(0, 1, 256)
    return np.stack([np.interp(x, xs, [s[c] for s in stops]) for c in range(3)], 1)[:, ::-1].astype(np.uint8)
DUO = [grad([(0, 0, 0), (235, 230, 214)]), grad([(4, 6, 20), (40, 90, 180), (200, 245, 255)]),
       grad([(0, 0, 0), (120, 0, 10), (255, 60, 40), (255, 235, 220)]), grad([(10, 0, 25), (90, 20, 160), (0, 255, 170)]),
       grad([(0, 8, 0), (20, 120, 30), (190, 255, 160)]), grad([(0, 0, 0), (60, 60, 60), (255, 255, 255)]),
       grad([(8, 0, 30), (150, 40, 120), (255, 200, 120)])]
BURST = [grad([(0, 0, 0), (40, 0, 120), (220, 0, 90), (255, 140, 0), (255, 255, 120), (255, 255, 255)]),
         grad([(255, 0, 140), (0, 220, 255), (255, 255, 0), (0, 0, 0), (255, 0, 0)]),
         grad([(0, 0, 255), (255, 0, 255), (255, 255, 255), (0, 255, 0), (0, 0, 0)]),
         grad([(0, 0, 0), (255, 0, 60), (0, 0, 0), (0, 255, 255), (255, 255, 255)]),
         grad([(20, 0, 60), (0, 90, 255), (0, 255, 200), (255, 250, 60), (255, 40, 0), (255, 255, 255)])]
FLASH = [(255, 255, 255), (0, 0, 0), (255, 0, 70), (0, 230, 255), (255, 240, 0), (170, 0, 255)]

# ---------------------------------------------------------------- beat grid & hold sections
BEAT = 60 * FPS / F['bpm']                       # frames per beat (~22 at 82 BPM)
best = max(np.arange(0, BEAT, 0.5), key=lambda o: kick[np.clip(np.round(o + np.arange(0, N / BEAT) * BEAT).astype(int), 0, N - 1)].sum())
BEATS = np.round(best + np.arange(0, N / BEAT) * BEAT).astype(int); BEATS = BEATS[BEATS < N]
beat_hit = np.zeros(N, bool); beat_hit[BEATS] = True
beat_env = np.zeros(N, np.float32); v = 0.0
for i in range(N):
    v = 1.0 if beat_hit[i] else v * 0.80; beat_env[i] = v
last_beat = np.maximum.accumulate(np.where(beat_hit, np.arange(N), 0))
HOLD_SECT = [(0.0, 24.0), (60.0, 72.0), (150.0, 161.0)]
SECTIONS = [(0, 24, 'iss aurora sun storm timelapse spacewalk'), (24, 60, 'jets carrier rocket drone thermal osprey parachute launch'),
            (60, 72, 'nightvision thermal cyber laser'), (72, 108, 'seas wildfire lightning snow drone storm thermal'),
            (108, 150, 'rocket launch spacewalk mars jets parachute osprey thermal'), (150, 999, 'iss sun aurora spacewalk')]
def sect_tags(f):
    t = f / FPS
    return next(x for a_, b_, x in SECTIONS if a_ <= t < b_).split()
hold = np.zeros(N, bool)
for a_, b_ in HOLD_SECT: hold[int(a_ * FPS):int(b_ * FPS)] = True
def next_beat(f): 
    j = np.searchsorted(BEATS, f); return int(BEATS[j]) if j < len(BEATS) else N

# ---------------------------------------------------------------- director
rnd = random.Random(2024)
scenes = []; recent = []
def pick(tags, allow_mosh):
    if allow_mosh and MOSH and rnd.random() < 0.28: return 'mosh', rnd.choice(MOSH)
    pool = [c for t in tags for c in POOL.get(t, [])]
    if not pool: pool = [c for t in ['stars', 'dance', 'light', 'ocean', 'zoo', 'electric'] for c in POOL.get(t, [])] or CLIPS
    for _ in range(25):
        p = rnd.choice(pool)
        if ident(p) not in recent[-4:] and p not in recent: break
    return 'clip', p
VISUAL = {'moon', 'cat', 'circus', 'ghost', 'ocean', 'wolf', 'stars', 'piano', 'horse', 'morse', 'grave', 'dance', 'birds', 'sun', 'clock', 'school', 'sheep', 'mountain'}
def add_scene(a, b, tags, held):
    kind, path = pick(tags, allow_mosh=(not held) and (line_at[a] < 0 or rnd.random() < 0.5))
    if held and rnd.random() < 0.12: kind, path = 'mosh', rnd.choice(MOSH)
    global recent
    recent = (recent + [ident(path), path])[-10:]
    scenes.append(dict(start=a, end=b, kind=kind, path=path, held=held, tags=tags,
                       mode=rnd.choices(['beatloop', 'beatloop', 'slow', 'halfbeat'])[0] if held else
                            rnd.choices(['normal', 'retrig', 'stutter', 'fast', 'slow', 'rev'], [3, 3, 2, 1, 2, 1])[0],
                       duo=rnd.randrange(len(DUO)), burst=rnd.randrange(len(BURST)), color=rnd.random() < 0.3,
                       seed=rnd.randrange(1 << 30)))
def bar_tags(a, b):
    return sect_tags(a), 1 if rnd.random() < 0.5 else 0
def _unused_bar_tags(a, b):
    """The strongest image in this bar: the line whose tags are most visual, weighted by screen time."""
    score = {}
    for f in range(a, b):
        ln = int(theme_line[f])
        if ln >= 0: score[ln] = score.get(ln, 0) + 1 + 2 * len(VISUAL & set(LY[ln]['tags']))
    if not score: return [], 0
    ln = max(score, key=score.get); return LY[ln]['tags'], len(VISUAL & set(LY[ln]['tags']))
# bars of 4 beats from the beat grid
BARS = [int(x) for x in BEATS[::8]] + [N]
if BARS[0] > 0: BARS = [0] + BARS
prev_held = False; run = 0
for bi in range(len(BARS) - 1):
    a, b = BARS[bi], BARS[bi + 1]
    tags, vis = bar_tags(a, b)
    slow = hold[a]
    # call and response: chop runs resolve into holds; holds break back into chop
    p = (0.62 if slow else 0.18) + 0.14 * min(vis, 2) + (0.25 if run >= (3 if not slow else 99) and not prev_held else 0) - (0.35 if prev_held and run >= 2 else 0)
    
    held = rnd.random() < p
    run = run + 1 if held == prev_held else 1; prev_held = held
    if held:
        # a held bar can split in half so the image changes with a new strong line
        mid = int(BEATS[min(len(BEATS) - 1, bi * 8 + 4)]) if bi * 8 + 4 < len(BEATS) else b
        t2, v2 = bar_tags(mid, b)
        if a < mid < b and v2 and t2 != tags and rnd.random() < 0.5:
            add_scene(a, mid, tags, True); add_scene(mid, b, t2, True)
        else:
            add_scene(a, b, tags, True)
        continue
    i = a
    while i < b:
        e = inten[i]; ln = int(theme_line[i])
        mn = int(12 - 7 * e); mx = int(60 - 32 * e)
        if slow: mn, mx = mn + 6, mx + 20   # chop inside slow passages is looser
        length = min(mx, b - i)
        for j in range(i + mn, min(b, i + mx)):
            if (snare_hit[j] or kick_hit[j]) and rnd.random() < 0.5 + 0.4 * e: length = j - i; break
            if line_at[j] != line_at[j - 1] and line_at[j] >= 0: length = j - i; break
        if b - (i + length) < 5: length = b - i
        add_scene(i, i + length, sect_tags(i), False)
        i += length
# stabs: short flash-cuts of related footage punched into held images on hard snares
stab = {}
for k, sc in enumerate(scenes):
    if not sc['held']: continue
    f = sc['start'] + 4
    while f < sc['end'] - 3:
        if snare_hit[f] and snare[f] > 0.6 and rnd.random() < 0.55:
            L = rnd.randint(2, 4); kind, path = pick(sc['tags'], allow_mosh=True)
            for g in range(f, min(sc['end'] - 1, f + L)): stab[g] = (path, rnd.randrange(1 << 30), f)
            f += L + 6
        else: f += 1
scene_at = np.zeros(N, int)
for k, s in enumerate(scenes): scene_at[s['start']:s['end']] = k
strobe = np.zeros(N, np.int8); stale = np.zeros(N, bool)
i = 0
while i < N - 6 * FPS:
    if hat_hit[i] and not hold[i] and inten[i] > 0.55 and rnd.random() < 0.12 * inten[i]:
        L = rnd.randint(5, 14); strobe[i:i + L] = rnd.randint(1, 3); i += L + 40; continue
    i += 1
i = 0
while i < N:
    if kick_hit[i] and rnd.random() < 0.10:
        L = rnd.randint(20, 75); stale[i:i + L] = True; i += L + 50; continue
    i += 1

# ---------------------------------------------------------------- text
FD = 'fonts/'
def big_font(s):
    f = ImageFont.truetype(FD + 'big-shoulders-display-900.ttf', s); f.set_variation_by_name(b'Black'); return f
MONO = FD + 'ibm-plex-mono-600.ttf'
_fcache = {}
def font(kind, size):
    k = (kind, size)
    if k not in _fcache: _fcache[k] = big_font(size) if kind == 'big' else ImageFont.truetype(MONO, size)
    return _fcache[k]

def layout(k):
    """Pick a style for a line and wrap it; returns style, font, list of rows of word indices, positions."""
    l = LY[k]; r = random.Random(k * 31 + 7); words = [w for w, _, _ in l['words']]; n = len(l['text'])
    style = 'big' if n <= 34 else r.choice(['big', 'mono', 'mono'])
    if n <= 16: style = r.choice(['big', 'big', 'stack'])
    kind = 'mono' if style == 'mono' else 'big'
    maxw = int(W * (0.90 if style != 'mono' else 0.84))
    size = {'big': 200 if n <= 16 else 160 if n <= 28 else 120 if n <= 50 else 92, 'stack': 220, 'mono': 66 if n < 60 else 56 if n < 90 else 48}[style]
    while True:
        f = font(kind, size); sp = f.getlength(' ')
        rows, row, wdt = [], [], 0
        for j, w in enumerate(words):
            ww = f.getlength(w)
            if style == 'stack' or (row and wdt + sp + ww > maxw): rows.append(row); row, wdt = [], 0
            row.append(j); wdt += (sp if len(row) > 1 else 0) + ww
        rows.append(row); rows = [x for x in rows if x]
        lh = int(size * (0.92 if kind == 'big' else 1.45))
        if lh * len(rows) < H * 0.78 and all(sum(f.getlength(words[j]) for j in row) + sp * (len(row) - 1) <= maxw for row in rows): break
        size = int(size * 0.9)
    place = r.choice(['center', 'center', 'low', 'left']) if style != 'mono' else r.choice(['low', 'left', 'center'])
    return dict(style=style, kind=kind, f=f, size=size, rows=rows, lh=lh, place=place, sp=sp, words=words,
                upper=(style != 'mono' and r.random() < 0.5))

LAY = {}
def text_layer(i, r):
    """Returns (alpha mask float HxW, newest-word mask) or None."""
    k = int(line_at[i])
    if k < 0: return None
    if k not in LAY: LAY[k] = layout(k)
    L = LAY[k]; l = LY[k]; t = i / FPS
    shown = [j for j, (_, a, _) in enumerate(l['words']) if a - 0.06 <= t]
    if not shown: return None
    newest = shown[-1] if t - l['words'][shown[-1]][1] < 0.18 else -1
    f = L['f']; lh = L['lh']; total = lh * len(L['rows'])
    y0 = {'center': (H - total) // 2, 'low': H - total - 70, 'left': (H - total) // 2}[L['place']]
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im); hot = Image.new('L', (W, H), 0); dh = ImageDraw.Draw(hot)
    for ri, row in enumerate(L['rows']):
        txt = [L['words'][j].upper() if L['upper'] else L['words'][j] for j in row]
        rw = sum(f.getlength(x) for x in txt) + L['sp'] * (len(row) - 1)
        x = 64 if L['place'] == 'left' else (W - rw) / 2
        y = y0 + ri * lh
        for j, w in zip(row, txt):
            if j in shown:
                d.text((x, y), w, font=f, fill=255)
                if j == newest: dh.text((x, y), w, font=f, fill=255)
            x += f.getlength(w) + L['sp']
    return np.asarray(im, np.float32) / 255, np.asarray(hot, np.float32) / 255

# ---------------------------------------------------------------- scenes & effects
class Scene:
    def __init__(self, k):
        s = scenes[k]; self.s = s; n = s['end'] - s['start']; self.r = random.Random(s['seed'])
        need = n * 2 if s['mode'] == 'fast' else n // 2 + 1 if s['mode'] == 'slow' else n
        tot = count(s['path']); need = max(1, min(need, tot - 1))
        st = self.r.randint(0, max(0, tot - need - 1))
        cap = cv2.VideoCapture(s['path']); cap.set(cv2.CAP_PROP_POS_FRAMES, st); fr = []
        for _ in range(need):
            ok, f = cap.read()
            if not ok: break
            fr.append(cv2.resize(f, (W, H), interpolation=cv2.INTER_LINEAR))
        cap.release(); self.frames = fr or [np.zeros((H, W, 3), np.uint8)]; self.cue = 0
    def frame(self, i):
        s = self.s; k = i - s['start']; fr = self.frames; L = len(fr); m = s['mode']
        if m in ('beatloop', 'halfbeat'):
            # loop a one-beat (or half-beat) slice, restarting on every beat; move the slice each bar
            seg = max(4, int(BEAT if m == 'beatloop' else BEAT / 2))
            bar = int(np.searchsorted(BEATS, i, side='right')) // 8
            if getattr(self, 'bar', None) != bar: self.bar = bar; self.loop0 = self.r.randint(0, max(0, L - seg - 1))
            return fr[min(L - 1, self.loop0 + (i - int(last_beat[i])) % seg)]
        if m == 'retrig':
            if any_hit[i] and k > 0: self.cue = self.r.choice([0, 0, L // 4, L // 2]) - k
            idx = (k + self.cue) % L
        elif m == 'stutter': idx = ((k // 3) * 3) % L
        elif m == 'fast': idx = (k * 2) % L
        elif m == 'slow': idx = (k // 2) % L
        elif m == 'rev': idx = (L - 1 - k) % L
        else: idx = k % L
        return fr[idx]

def zoom(img, z, dx, dy, rot=0.0):
    M = cv2.getRotationMatrix2D((W / 2 + dx, H / 2 + dy), rot, z)
    return cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)

def grade(img, sc, i):
    b = kick[i] * (0.35 + 0.65 * inten[i])
    if sc['color']:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV); hsv[..., 1] = cv2.add(hsv[..., 1], 70)
        out = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    else:
        g = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)); out = DUO[sc['duo']][g]
    if b > 0.3:
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        lut = np.roll(BURST[(sc['burst'] + i // 8) % len(BURST)], int(i * 7) % 256, 0) if b > 0.7 else BURST[sc['burst']]
        out = cv2.addWeighted(out, 1 - min(1, b * 1.2), lut[g], min(1, b * 1.2), 0)
    return out

def rgb_split(img, d):
    d = int(d)
    if d < 1: return img
    b, g, r = cv2.split(img); return cv2.merge([np.roll(b, -d, 1), g, np.roll(r, d, 1)])

def blocks(img, prev, amt, r):
    out = img.copy()
    for _ in range(int(2 + 14 * amt)):
        bw = r.choice([32, 64, 96, 128]); bh = r.choice([32, 64, 96])
        x = r.randrange(0, W - bw); y = r.randrange(0, H - bh)
        if r.random() < 0.5 and prev is not None:
            sx = min(W - bw, max(0, x + r.randint(-80, 80))); sy = min(H - bh, max(0, y + r.randint(-40, 40)))
            out[y:y + bh, x:x + bw] = prev[sy:sy + bh, sx:sx + bw]
        else:
            q = r.choice([8, 16]); blk = out[y:y + bh, x:x + bw]
            out[y:y + bh, x:x + bw] = cv2.resize(cv2.resize(blk, (bw // q, bh // q)), (bw, bh), interpolation=cv2.INTER_NEAREST)
    return out

def stale_blocks(cur, prev, thr, r):
    bs = 16; c = cur.reshape(H // bs, bs, W // bs, bs, 3).astype(np.int16); p = prev.reshape(H // bs, bs, W // bs, bs, 3).astype(np.int16)
    keep = (np.abs(c - p).mean(axis=(1, 3, 4)) < thr)[:, None, :, None, None]
    drift = np.roll(prev, (r.choice([-2, 0, 2]), r.choice([-4, -2, 2, 4])), (0, 1))
    return np.where(keep, drift.reshape(c.shape), c).astype(np.uint8).reshape(H, W, 3)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = 1 - 0.5 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.4
scan = np.where((np.arange(H) % 3) == 0, 0.85, 1.0).astype(np.float32)[:, None]
MASK = np.clip(vig * scan, 0, 1)[..., None]
NOISE = [np.random.default_rng(k).normal(0, 1, (H, W)).astype(np.float32) for k in range(6)]

def composite_text(img, i, r, prev_txt):
    tl = text_layer(i, r)
    if tl is None: return img, None
    a, hot = tl
    e = inten[i]
    # text glitches: kick RGB split, jitter, occasional block corruption of the letters
    d = int(3 + 16 * kick[i] + 10 * hot.max())
    jx = int(r.uniform(-1, 1) * 5 * snare[i])
    a2 = np.roll(a, jx, 1)
    if snare_hit[i] and r.random() < 0.5:
        a2 = blocks((a2[..., None] * 255).astype(np.uint8).repeat(3, 2), None, 0.5, r)[..., 0].astype(np.float32) / 255
    # soft shadow for legibility over bright footage
    sh = cv2.GaussianBlur(a2, (0, 0), 9) * 0.75
    out = img.astype(np.float32) * (1 - sh[..., None])
    red = np.roll(a2, d, 1); blu = np.roll(a2, -d, 1)
    out[..., 2] = out[..., 2] * (1 - red * 0.9) + 255 * red * 0.9
    out[..., 0] = out[..., 0] * (1 - blu * 0.9) + 255 * blu * 0.9
    col = np.array([245, 245, 240], np.float32) if r.random() > 0.08 * (1 + e) else np.array(FLASH[r.randrange(len(FLASH))][::-1], np.float32)
    out = out * (1 - a2[..., None]) + col * a2[..., None]
    # the newest word glows
    if hot.max() > 0:
        g = cv2.GaussianBlur(hot, (0, 0), 14)[..., None]
        out = out + g * np.array([255, 200, 255], np.float32) * 0.6
    return np.clip(out, 0, 255).astype(np.uint8), a2

def render(a, b, outp):
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-vf', 'scale=1920:1080:flags=lanczos', '-c:v', 'libx264', '-crf', '15', '-preset', 'fast',
                           '-pix_fmt', 'yuv420p', outp], stdin=subprocess.PIPE)
    warm = max(0, a - 12); prev = None; cur_k = -1; S = None; STABS = {}
    for i in range(warm, b):
        k = int(scene_at[i]); sc = scenes[k]
        if k != cur_k: S = Scene(k); cur_k = k
        r = random.Random(i * 7919 + 13); e = inten[i]
        img = S.frame(i)
        if i in stab:   # flash-cut of related footage punched into a held image
            path, sd, f0 = stab[i]; key = (path, f0)
            if key not in STABS:
                STABS.clear(); rr = random.Random(sd); cap = cv2.VideoCapture(path); tot = count(path)
                cap.set(cv2.CAP_PROP_POS_FRAMES, rr.randint(0, max(0, tot - 6))); fr = []
                for _ in range(5):
                    ok, f = cap.read()
                    if ok: fr.append(cv2.resize(f, (W, H)))
                cap.release(); STABS[key] = fr or [img]
            fr = STABS[key]; img = fr[min(len(fr) - 1, i - f0)]
        held = sc.get('held')
        if held:
            u = (i - sc['start']) / max(1, sc['end'] - sc['start'])
            z = 1.04 + 0.05 * u + 0.08 * beat_env[i] + 0.05 * kick[i]; sh = 8 * beat_env[i]
        else:
            z = 1.0 + 0.09 * kick[i] * (0.3 + e); sh = 20 * kick[i] * e
        img = zoom(img, z, r.uniform(-sh, sh), r.uniform(-sh, sh), r.uniform(-2, 2) * snare[i] * e)
        img = grade(img, dict(sc, color=False, duo=(sc['duo'] + 3) % len(DUO)) if i in stab else sc, i)
        if stale[i] and prev is not None and not held: img = stale_blocks(img, prev, 10 + 25 * e, r)
        if held:
            if snare_hit[i] and r.random() < 0.35: img = blocks(img, prev, 0.3, r)
        elif snare_hit[i]: img = blocks(img, prev, min(1, 0.3 + e), r)
        elif any_hit[i] and r.random() < 0.2 + 0.4 * e: img = blocks(img, prev, e, r)
        img = rgb_split(img, 1 + 18 * kick[i] * (0.3 + e) + 4 * sub[i])
        prev = img.copy()
        # strobe after text so the words strobe with the picture
        if strobe[i]:
            ph = (i % 2) if strobe[i] != 3 else (i // 2 % 2)
            if ph:
                c = r.random()
                img = 255 - img if c < 0.6 else cv2.cvtColor(255 - cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
        elif snare_hit[i] and snare[i] > 0.85 and r.random() < 0.18 * e and line_at[i] < 0:
            img[:] = FLASH[r.randrange(len(FLASH))][::-1]
        elif hat_hit[i] and r.random() < 0.08 * e:
            img = 255 - img
        fl = 1.0 + (r.random() - 0.5) * 0.05
        out = img.astype(np.float32) * (MASK * fl) + NOISE[i % 6][..., None] * (7 + 6 * hat[i])
        if i >= OUTRO_FADE: out *= max(0.0, 1 - (i - OUTRO_FADE) / (N - OUTRO_FADE))
        if i < 12: out *= i / 12
        if i >= a: ff.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())
        if i % 150 == 0: print(outp, i, flush=True)
    ff.stdin.close(); ff.wait()

if __name__ == '__main__':
    render(int(sys.argv[1]), min(int(sys.argv[2]), N), sys.argv[3])
