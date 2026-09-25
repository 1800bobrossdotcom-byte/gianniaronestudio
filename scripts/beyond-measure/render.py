"""BEYOND MEASURE — audio-reactive render.
usage: python3 render.py <start_frame> <end_frame> <out.mp4>   (python3 render.py preview 1200 1500 x.mp4)
"""
import numpy as np, cv2, json, glob, random, subprocess, sys, os, re
from scipy.ndimage import uniform_filter1d
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1280, 720, 30
TEXT = False  # title cards, stamps and HUD
F = json.load(open('feat.json')); N = F['n']
A = lambda k: np.array(F[k], np.float32)
rms, flux, sub, low, mid, high = map(A, ['rms', 'flux', 'sub', 'low', 'mid', 'high'])
T = np.arange(N) / FPS

def pulses(on, strength, decay, thr):
    e = np.zeros(N, np.float32); hit = np.zeros(N, bool); v = 0.0
    s = {i for i in on if strength[i] > thr}
    for i in range(N):
        if i in s: v = max(v * decay, 0.4 + 0.6 * strength[i]); hit[i] = True
        else: v *= decay
        e[i] = v
    return e, hit
kick, kick_hit = pulses(F['on_sub'], sub, 0.70, 0.22)
snare, snare_hit = pulses(F['on_mid'], mid, 0.62, 0.25)
hat, hat_hit = pulses(F['on_high'], high, 0.50, 0.15)
_, any_hit = pulses(F['on'], flux, 0.5, 0.12)
energy = uniform_filter1d(rms, 45)
inten = np.clip((energy - 0.08) / 0.45, 0, 1) ** 1.1
INTRO_END = 24.0 * FPS
OUTRO = 176.0 * FPS

# ---------------------------------------------------------------- sources
TITLES = json.load(open('titles.json'))

def ident(path): return re.sub(r'_\d+\.mp4$', '', os.path.basename(path))
CLIPS = sorted(glob.glob('clips/*.mp4'))
MOSH = sorted(glob.glob('mosh/*.mp4'))
DOCS = sorted(glob.glob('docs/*.png'))
nframes = {}
def count(p):
    if p not in nframes:
        c = cv2.VideoCapture(p); nframes[p] = int(c.get(cv2.CAP_PROP_FRAME_COUNT)); c.release()
    return nframes[p]

def label(kind, path):
    if kind == 'doc':
        b = os.path.basename(path)[:-4]
        if b.startswith('cia-readingroom-document-'):
            return 'CIA READING ROOM // ' + b[len('cia-readingroom-document-'):].rsplit('_', 1)[0].upper()
        if b.startswith('cryptolog'): return 'NSA // CRYPTOLOG ' + b.split('_')[1]
        if 'COINTELPRO' in b: return 'FBI // COINTELPRO NEW LEFT HQ-1'
        if 'tesla' in b: return 'FBI // FILE 100-2237 TESLA'
        return b.upper()
    if kind == 'mosh': return 'SIGNAL CORRUPTED // I-FRAME LOSS'
    i = ident(path); m = TITLES.get(i, {}); t = (m.get('title') or i).upper()
    agency = 'DOE' if i.startswith('gov.doe') else 'DOD' if 'dimoc' in i else 'NTIS' if 'ntis' in i else 'NARA'
    return f"{agency} // {i.upper()} // {t[:52]}" + (f" // {m['year']}" if m.get('year') else '')

# ---------------------------------------------------------------- palettes (RGB stops)
def grad(stops):
    xs = np.linspace(0, 1, len(stops)); x = np.linspace(0, 1, 256)
    rgb = np.stack([np.interp(x, xs, [s[c] for s in stops]) for c in range(3)], 1)
    return rgb[:, ::-1].astype(np.uint8)  # to BGR
DUO = [grad([(0, 0, 0), (235, 230, 214)]),                       # bone
       grad([(4, 6, 20), (40, 90, 180), (200, 245, 255)]),      # cold
       grad([(0, 0, 0), (120, 0, 10), (255, 60, 40), (255, 235, 220)]),  # red room
       grad([(10, 0, 25), (90, 20, 160), (0, 255, 170)]),       # acid
       grad([(0, 8, 0), (20, 120, 30), (190, 255, 160)]),       # night vision
       grad([(0, 0, 0), (60, 60, 60), (255, 255, 255)])]        # mono
BURST = [grad([(0, 0, 0), (40, 0, 120), (220, 0, 90), (255, 140, 0), (255, 255, 120), (255, 255, 255)]),  # thermal
         grad([(255, 0, 140), (0, 220, 255), (255, 255, 0), (0, 0, 0), (255, 0, 0)]),
         grad([(0, 0, 255), (255, 0, 255), (255, 255, 255), (0, 255, 0), (0, 0, 0)]),
         grad([(0, 0, 0), (255, 0, 60), (0, 0, 0), (0, 255, 255), (255, 255, 255)]),
         grad([(20, 0, 60), (0, 90, 255), (0, 255, 200), (255, 250, 60), (255, 40, 0), (255, 255, 255)])]
FLASH = [(255, 255, 255), (0, 0, 0), (255, 0, 70), (0, 230, 255), (255, 240, 0), (170, 0, 255)]

# ---------------------------------------------------------------- director (deterministic, global)
rnd = random.Random(1987)
scenes = []  # dict(start, end, kind, path, ...)
def pick(kind, recent):
    pool = {'clip': CLIPS, 'mosh': MOSH, 'doc': DOCS}[kind]
    for _ in range(20):
        p = rnd.choice(pool)
        if ident(p) not in recent: return p
    return p
recent = []
i = 0
while i < N:
    t = i / FPS
    if i < INTRO_END:
        length = rnd.randint(50, 110)
        kind = rnd.choices(['doc', 'clip'], [0.55, 0.45])[0]
    elif i >= OUTRO:
        length = rnd.randint(40, 70); kind = rnd.choices(['clip', 'doc', 'mosh'], [.5, .3, .2])[0]
    else:
        e = inten[i]
        mn = int(10 - 6 * e); mx = int(55 - 30 * e)
        # cut on the first strong hit after mn frames, else at mx
        length = mx
        for j in range(i + mn, min(N, i + mx)):
            if (snare_hit[j] or kick_hit[j]) and rnd.random() < 0.55 + 0.4 * e: length = j - i; break
        kind = rnd.choices(['clip', 'mosh', 'doc'], [0.52, 0.33, 0.15])[0]
    end = min(N, i + length)
    if i < OUTRO <= end and i != OUTRO: end = int(OUTRO)
    if i < INTRO_END <= end and i != INTRO_END: end = int(INTRO_END)
    path = pick(kind, recent); recent = (recent + [ident(path)])[-8:]
    sc = dict(start=i, end=end, kind=kind, path=path,
              mode=rnd.choices(['normal', 'retrig', 'stutter', 'fast', 'slow', 'rev'], [3, 3, 2, 1, 1, 1])[0],
              duo=rnd.randrange(len(DUO)), burst=rnd.randrange(len(BURST)),
              color=rnd.random() < 0.25, ghost=pick('doc', []) if kind != 'doc' and rnd.random() < 0.3 else None,
              z0=rnd.uniform(1.1, 2.6), z1=rnd.uniform(1.1, 2.6), p0=(rnd.random(), rnd.random()), p1=(rnd.random(), rnd.random()),
              seed=rnd.randrange(1 << 30))
    if i < INTRO_END: sc['mode'] = rnd.choice(['normal', 'slow']); sc['duo'] = rnd.choice([0, 5, 1])
    scenes.append(sc); i = end
scene_at = np.zeros(N, int)
for k, s in enumerate(scenes): scene_at[s['start']:s['end']] = k

# strobe bursts, stale-block mosh windows, stamps
strobe = np.zeros(N, np.int8); stale = np.zeros(N, bool); stamp_at = {}
i = int(INTRO_END)
while i < OUTRO:
    if hat_hit[i] and inten[i] > 0.45 and rnd.random() < 0.22 * inten[i]:
        L = rnd.randint(6, 20); strobe[i:i + L] = rnd.randint(1, 3); i += L + 16; continue
    i += 1
i = int(INTRO_END)
while i < OUTRO:
    if kick_hit[i] and rnd.random() < 0.11:
        L = rnd.randint(20, 70); stale[i:i + L] = True; i += L + 60; continue
    i += 1
STAMPS = ['DECLASSIFIED', 'TOP SECRET', 'REDACTED', 'EYES ONLY', 'NOFORN', 'SECRET', '(b)(1)', '(b)(3)', 'FOIA',
          'CLASSIFIED', 'BEYOND MEASURE', 'SANITIZED', 'UNCLASSIFIED', 'CONFIDENTIAL']
i = int(INTRO_END)
while i < OUTRO:
    if (snare_hit[i] or kick_hit[i]) and rnd.random() < 0.18:
        stamp_at[i] = (rnd.choice(STAMPS), rnd.randint(8, 22), rnd.uniform(-18, 18), rnd.random(), rnd.random(), rnd.randrange(1 << 30))
        i += rnd.randint(40, 140); continue
    i += 1

# ---------------------------------------------------------------- assets
FD = 'fonts/'
def f_big(s, w=b'Black'):
    f = ImageFont.truetype(FD + 'big-shoulders-display-900.ttf', s); f.set_variation_by_name(w); return f
f_mono = ImageFont.truetype(FD + 'ibm-plex-mono-500.ttf', 17)
f_mono_s = ImageFont.truetype(FD + 'ibm-plex-mono-500.ttf', 14)

def make_stamp(text, seed):
    r = random.Random(seed); size = r.choice([70, 90, 120, 150])
    font = f_big(size); bb = font.getbbox(text); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = size // 5; im = Image.new('L', (tw + pad * 4, th + pad * 4), 0); d = ImageDraw.Draw(im)
    d.rectangle([pad // 2, pad // 2, im.width - pad // 2, im.height - pad // 2], outline=255, width=max(4, size // 14))
    d.text((pad * 2 - bb[0], pad * 2 - bb[1]), text, font=font, fill=255)
    a = np.asarray(im, np.float32) / 255
    ink = np.random.default_rng(seed).random(a.shape) ** 0.35  # rough ink
    ink = cv2.GaussianBlur(ink.astype(np.float32), (0, 0), 1.2)
    return np.clip(a * (ink * 1.4), 0, 1)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = 1 - 0.55 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.4
scan = np.where((np.arange(H) % 3) == 0, 0.82, 1.0).astype(np.float32)[:, None]
MASK = np.clip(vig * scan, 0, 1)[..., None]
NOISE = [np.random.default_rng(k).normal(0, 1, (H, W)).astype(np.float32) for k in range(6)]

class Scene:
    """Loads the frames a scene needs, once."""
    cache = {}
    def __init__(self, k):
        s = scenes[k]; self.s = s; n = s['end'] - s['start']
        self.r = random.Random(s['seed'])
        if s['kind'] == 'doc':
            self.doc = cv2.imread(s['path'], cv2.IMREAD_GRAYSCALE)
            self.bars = []
            return
        need = n * 2 if s['mode'] == 'fast' else n
        tot = count(s['path']); need = min(need, max(1, tot - 1))
        st = self.r.randint(0, max(0, tot - need - 1))
        cap = cv2.VideoCapture(s['path']); cap.set(cv2.CAP_PROP_POS_FRAMES, st)
        fr = []
        for _ in range(need):
            ok, f = cap.read()
            if not ok: break
            fr.append(cv2.resize(f, (W, H), interpolation=cv2.INTER_LINEAR))
        cap.release()
        self.frames = fr or [np.zeros((H, W, 3), np.uint8)]
        self.ghost = cv2.imread(s['ghost'], cv2.IMREAD_GRAYSCALE) if s['ghost'] else None
        self.cue = 0

    def doc_view(self, img, u, z0, z1, p0, p1):
        h, w = img.shape; z = z0 + (z1 - z0) * u
        px = p0[0] + (p1[0] - p0[0]) * u; py = p0[1] + (p1[1] - p0[1]) * u
        scale = max(W / w, H / h) * z
        cx = px * max(0, w * scale - W); cy = py * max(0, h * scale - H)
        M = np.float32([[scale, 0, -cx], [0, scale, -cy]])
        return cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_CONSTANT, borderValue=235)

    def frame(self, i):
        s = self.s; k = i - s['start']; n = s['end'] - s['start']; u = k / max(1, n - 1)
        if s['kind'] == 'doc':
            g = self.doc_view(self.doc, u, s['z0'], s['z1'], s['p0'], s['p1'])
            if kick_hit[i] or snare_hit[i]:  # redaction bars land on the beat
                y = self.r.randint(40, H - 60); x = self.r.randint(0, W // 2)
                self.bars.append((x, y, self.r.randint(160, W - x), self.r.randint(14, 34)))
            for (x, y, bw, bh) in self.bars: g[y:y + bh, x:x + bw] = 8
            return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
        fr = self.frames; m = s['mode']; L = len(fr)
        if m == 'retrig':
            if any_hit[i] and k > 0: self.cue = self.r.choice([0, 0, L // 4, L // 2]) - k
            idx = (k + self.cue) % L
        elif m == 'stutter': idx = ((k // 3) * 3) % L
        elif m == 'fast': idx = (k * 2) % L
        elif m == 'slow': idx = (k // 2) % L
        elif m == 'rev': idx = (L - 1 - k) % L
        else: idx = k % L
        f = fr[idx]
        if self.ghost is not None:
            g = self.doc_view(self.ghost, u, 1.3, 1.6, s['p0'], s['p1'])
            f = cv2.multiply(f, cv2.cvtColor(g, cv2.COLOR_GRAY2BGR), scale=1 / 255)
        return f

# ---------------------------------------------------------------- effects
def zoom(img, z, dx, dy, rot=0.0):
    M = cv2.getRotationMatrix2D((W / 2 + dx, H / 2 + dy), rot, z)
    return cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)

def grade(img, sc, i, r):
    b = kick[i] * (0.35 + 0.65 * inten[i])
    if sc['color'] and sc['kind'] == 'clip':
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV); hsv[..., 1] = cv2.add(hsv[..., 1], 70)
        out = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    else:
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        g = cv2.equalizeHist(g) if sc['kind'] != 'doc' else g
        out = DUO[sc['duo']][g]
    if b > 0.28 and i >= INTRO_END:  # color burst: gradient map, cycling on the beat
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        lut = np.roll(BURST[(sc['burst'] + int(i // 8)) % len(BURST)], int(i * 7) % 256, 0) if b > 0.7 else BURST[sc['burst']]
        out = cv2.addWeighted(out, 1 - min(1, b * 1.2), lut[g], min(1, b * 1.2), 0)
    return out

def rgb_split(img, d):
    d = int(d)
    if d < 1: return img
    b, g, r = cv2.split(img)
    return cv2.merge([np.roll(b, -d, 1), g, np.roll(r, d, 1)])

def slices(img, amt, r):
    out = img.copy(); n = r.randint(3, 3 + int(12 * amt))
    for _ in range(n):
        y = r.randrange(H); h = r.randint(4, int(20 + 120 * amt)); dx = int(r.uniform(-1, 1) * 260 * amt)
        band = np.roll(out[y:y + h], dx, 1)
        if r.random() < 0.3: band = band[..., r.sample([0, 1, 2], 3)]
        if r.random() < 0.15: band = 255 - band
        out[y:y + h] = band
    return out

def blocks(img, prev, amt, r):
    out = img.copy()
    for _ in range(int(2 + 14 * amt)):
        bw = r.choice([32, 64, 96, 128, 192]); bh = r.choice([16, 32, 64, 96])
        x = r.randrange(0, W - bw); y = r.randrange(0, H - bh)
        c = r.random()
        if c < 0.4 and prev is not None:
            sx = min(W - bw, max(0, x + r.randint(-80, 80))); sy = min(H - bh, max(0, y + r.randint(-40, 40)))
            out[y:y + bh, x:x + bw] = prev[sy:sy + bh, sx:sx + bw]
        elif c < 0.75:
            blk = out[y:y + bh, x:x + bw]; q = r.choice([8, 16])
            out[y:y + bh, x:x + bw] = cv2.resize(cv2.resize(blk, (max(1, bw // q), max(1, bh // q))), (bw, bh), interpolation=cv2.INTER_NEAREST)
        else:
            out[y:y + bh, x:] = out[y:y + bh, x:x + 1]  # smear a column to the edge
    return out

def pixel_smear(img, r):
    y0 = r.randrange(0, H - 120); h = r.randint(60, 300); x0 = r.randrange(0, W // 2)
    seg = img[y0:y0 + h, x0:].astype(np.int16)
    lum = seg.sum(2)
    m = np.maximum.accumulate(lum, axis=1)
    img[y0:y0 + h, x0:] = np.where((lum > 420)[..., None], seg, np.maximum.accumulate(seg, axis=1)).astype(np.uint8)
    return img

def stale_blocks(cur, prev, thr, r):
    # pseudo-datamosh: blocks that don't change enough keep the previous frame's pixels, and drift
    bs = 16; c = cur.reshape(H // bs, bs, W // bs, bs, 3).astype(np.int16)
    p = prev.reshape(H // bs, bs, W // bs, bs, 3).astype(np.int16)
    diff = np.abs(c - p).mean(axis=(1, 3, 4))
    keep = (diff < thr)[:, None, :, None, None]
    drift = np.roll(prev, (r.choice([-2, 0, 2]), r.choice([-4, -2, 2, 4])), (0, 1))
    return np.where(keep, drift.reshape(c.shape), c).astype(np.uint8).reshape(H, W, 3)

def text(draw, xy, s, font, fill):
    draw.text(xy, s, font=font, fill=fill)

def tc(i):
    s = i // FPS; return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{i % FPS:02d}"

def title_card(img, i, lines, alpha, glitch, r):
    ov = Image.new('L', (W, H), 0); d = ImageDraw.Draw(ov); y = H // 2 - 110
    for (s, size) in lines:
        f = f_big(size); bb = d.textbbox((0, 0), s, font=f)
        d.text(((W - (bb[2] - bb[0])) // 2 - bb[0], y - bb[1]), s, font=f, fill=255); y += (bb[3] - bb[1]) + 30
    m = np.asarray(ov)
    if glitch > 0: m = slices(m[..., None].repeat(3, 2), glitch, r)[..., 0]
    a = (m.astype(np.float32) / 255 * alpha)[..., None]
    col = np.array([235, 240, 245], np.float32)
    out = img * (1 - a) + col * a
    d = int(6 + 20 * glitch)
    red = np.roll(a, d, 1) * (1 - a); blu = np.roll(a, -d, 1) * (1 - a)
    out[..., 2] += red[..., 0] * 255; out[..., 0] += blu[..., 0] * 255
    return np.clip(out, 0, 255).astype(np.uint8)

# ---------------------------------------------------------------- main loop
def render(a, b, outp):
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-vf', 'scale=1920:1080:flags=lanczos', '-c:v', 'libx264', '-crf', '15', '-preset', 'fast',
                           '-pix_fmt', 'yuv420p', outp], stdin=subprocess.PIPE)
    warm = max(0, a - 12); prev = None; cur_k = -1; S = None; stamps = []
    for i in range(warm, b):
        k = scene_at[i]; sc = scenes[k]
        if k != cur_k: S = Scene(k); cur_k = k
        r = random.Random(i * 7919 + 13)
        e = inten[i]
        img = S.frame(i)
        # motion: kick punch-in + shake, slow drift in intro
        z = 1.0 + 0.10 * kick[i] * (0.3 + e) + (0.03 * np.sin(i / 90) if i < INTRO_END else 0)
        sh = 22 * kick[i] * e
        img = zoom(img, z, r.uniform(-sh, sh), r.uniform(-sh, sh), r.uniform(-2, 2) * snare[i] * e)
        img = grade(img, sc, i, r)
        if stale[i] and prev is not None: img = stale_blocks(img, prev, 10 + 25 * e, r)
        if i >= INTRO_END:
            if snare[i] > 0.3: img = slices(img, snare[i] * (0.3 + 0.8 * e), r)
            if (snare_hit[i] or any_hit[i]) and r.random() < 0.25 + 0.5 * e: img = blocks(img, prev, e, r)
            if e > 0.55 and r.random() < 0.08: img = pixel_smear(img, r)
        elif r.random() < 0.04:  # intro: sparse flicker
            img = slices(img, 0.2, r)
        img = rgb_split(img, 1 + 22 * kick[i] * (0.3 + e) + 5 * sub[i])
        # stamps
        if TEXT and i in stamp_at:
            txt, dur, ang, px, py, sd = stamp_at[i]; st = make_stamp(txt, sd)
            hh, ww = st.shape; M = cv2.getRotationMatrix2D((ww / 2, hh / 2), ang, 1.0)
            cos, sin = abs(M[0, 0]), abs(M[0, 1]); nw, nh = int(hh * sin + ww * cos), int(hh * cos + ww * sin)
            M[0, 2] += nw / 2 - ww / 2; M[1, 2] += nh / 2 - hh / 2
            st = cv2.warpAffine(st, M, (nw, nh)); nw, nh = min(nw, W), min(nh, H); st = st[:nh, :nw]
            stamps.append((st, int(px * (W - nw)), int(py * (H - nh)), i + dur))
        stamps = [s for s in stamps if s[3] > i]
        if stamps:
            fimg = img.astype(np.float32)
            for (st, x, y, _) in stamps:
                if r.random() < 0.12: continue  # flicker
                a_ = st[..., None] * 0.92; reg = fimg[y:y + st.shape[0], x:x + st.shape[1]]
                ink = np.array([30, 20, 215], np.float32) if r.random() > 0.1 else np.array([255, 255, 255], np.float32)
                fimg[y:y + st.shape[0], x:x + st.shape[1]] = reg * (1 - a_) + ink * a_
            img = fimg.astype(np.uint8)
        # strobe
        if strobe[i]:
            ph = (i % 2) if strobe[i] != 3 else (i // 2 % 2)
            if ph:
                c = r.random()
                if c < 0.45: img = 255 - img
                elif c < 0.8: img[:] = FLASH[r.randrange(len(FLASH))][::-1]
                else: img = cv2.cvtColor(255 - cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
        elif i >= INTRO_END and snare_hit[i] and snare[i] > 0.8 and r.random() < 0.3 * e:
            img[:] = FLASH[r.randrange(len(FLASH))][::-1]
        elif i >= INTRO_END and hat_hit[i] and r.random() < 0.14 * e:
            img = 255 - img
        prev = img.copy()
        # film texture: scanlines, vignette, grain, flicker
        fl = 1.0 + (r.random() - 0.5) * (0.10 if i < INTRO_END else 0.05)
        out = img.astype(np.float32) * (MASK * fl) + (NOISE[i % 6][..., None] * (7 + 6 * hat[i]))
        # titles
        if TEXT and 6 * FPS <= i < INTRO_END:
            u = (i - 6 * FPS) / (INTRO_END - 6 * FPS)
            alpha = min(1, u * 6) * min(1, (1 - u) * 5)
            out *= 1 - 0.45 * alpha
            out = title_card(np.clip(out, 0, 255), i, [('BEYOND MEASURE', 168), ('GIANNI ARONE', 50)], alpha,
                             0.5 if r.random() < 0.12 else 0.0, r).astype(np.float32)
        if i >= N - 7 * FPS:
            u = (i - (N - 7 * FPS)) / (7 * FPS)
            out *= max(0.0, 1 - u * 1.6)
            alpha = min(1, u * 5) * min(1, (1 - u) * 6)
            if TEXT: out = title_card(np.clip(out, 0, 255), i, [('BEYOND MEASURE', 150), ('GIANNI ARONE', 42),
                             ('ARCHIVAL FOOTAGE & DOCUMENTS: NATIONAL ARCHIVES · DOE · DOD · CIA · NSA · FBI — PUBLIC DOMAIN', 22)],
                             alpha, 0.4 if r.random() < 0.1 else 0.0, r).astype(np.float32)
        img = np.clip(out, 0, 255).astype(np.uint8)
        # HUD
        pim = Image.fromarray(img); d = ImageDraw.Draw(pim); hc = (230, 230, 230)
        if TEXT and 0.6 * FPS < i < N - 7 * FPS:
            text(d, (28, 22), 'FOIA // CASE 0925-BM // BEYOND MEASURE', f_mono, hc)
            if (i // 15) % 2 == 0: d.ellipse([W - 118, 27, W - 104, 41], fill=(40, 40, 230))
            text(d, (W - 96, 22), 'REC', f_mono, hc)
            text(d, (W - 190, H - 42), tc(i), f_mono, hc)
            text(d, (28, H - 40), label(sc['kind'], sc['path']), f_mono_s, hc)
            lvl = int(160 * rms[i]); d.rectangle([28, H - 58, 28 + lvl, H - 54], fill=hc)
        if i >= a: ff.stdin.write(np.asarray(pim).tobytes())
        if i % 150 == 0: print(outp, i, flush=True)
    ff.stdin.close(); ff.wait()

if __name__ == '__main__':
    a, b, o = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    render(a, min(b, N), o)
