# Flags clips that contain intertitles / captions / near-black frames.
import cv2, glob, json, numpy as np, os
def is_texty(fr):
    g = cv2.cvtColor(cv2.resize(fr, (480, 270)), cv2.COLOR_BGR2GRAY)
    dark = (g < 70).mean(); bright = (g > 150).mean()
    if g.mean() < 14: return 'black'
    if dark > 0.72 and 0.006 < bright < 0.22:
        # text = many small bright components laid out in rows
        _, bw = cv2.threshold(g, 140, 255, cv2.THRESH_BINARY)
        n, _, st, _ = cv2.connectedComponentsWithStats(bw)
        small = ((st[1:, 4] > 6) & (st[1:, 4] < 900) & (st[1:, 3] < 40)).sum()
        if small > 25: return 'intertitle'
    # light-background title (dark text on light card)
    if bright > 0.72 and 0.01 < dark < 0.2:
        _, bw = cv2.threshold(255 - g, 140, 255, cv2.THRESH_BINARY)
        n, _, st, _ = cv2.connectedComponentsWithStats(bw)
        if ((st[1:, 4] > 6) & (st[1:, 4] < 900) & (st[1:, 3] < 40)).sum() > 25: return 'card'
    return None
bad = {}
for f in sorted(glob.glob('clips/*.mp4')):
    cap = cv2.VideoCapture(f); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); hits = []
    for t in np.linspace(2, max(3, n - 3), 6).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t)); ok, fr = cap.read()
        if ok:
            r = is_texty(fr)
            if r: hits.append(r)
    cap.release()
    if hits: bad[os.path.basename(f)] = hits
json.dump(bad, open('auto_reject.json', 'w'), indent=1)
print(len(bad), 'flagged of', len(glob.glob('clips/*.mp4')))
