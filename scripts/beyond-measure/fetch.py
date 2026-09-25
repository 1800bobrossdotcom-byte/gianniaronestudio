import json, subprocess, urllib.request, random, os, sys, concurrent.futures as cf
IDS = """gov.archives.arc.1634176 gov.archives.arc.12175 gov.archives.arc.651948 gov.archives.arc.2569661
gov.dod.dimoc.23284 gov.archives.arc.649321 gov.archives.arc.896138 gov.archives.arc.653944 342-usaf-42990
330-dvic-653 gov.archives.arc.37826 gov.dod.dimoc.28384 gov.archives.arc.1257667 gov.dod.dimoc.26415
gov.doe.0800008 gov.doe.0800014 gov.doe.0800017 gov.doe.0800010 gov.doe.0800016 gov.doe.0800011
111-adc-7174 gov.ntis.ava11109vnb1 gov.archives.arc.642009 gov.archives.arc.1956144""".split()
os.makedirs('clips', exist_ok=True)
def meta(i): return json.load(urllib.request.urlopen(f'https://archive.org/metadata/{i}', timeout=60))
def work(i):
    try:
        m = meta(i)
        vids = [f for f in m['files'] if f['name'].lower().endswith(('.mp4', '.mpeg4', '.ogv', '.m4v'))]
        if not vids: return i, 'no video'
        # prefer an mp4 of moderate size
        vids.sort(key=lambda f: (not f['name'].endswith('.mp4'), abs(int(f.get('size', 1e9)) - 60e6)))
        f = vids[0]; url = f"https://archive.org/download/{i}/{urllib.request.quote(f['name'])}"
        dur = float(f.get('length') or 0)
        if not dur and False:
            out = subprocess.run(['ffmpeg', '-i', url], capture_output=True, text=True).stderr
            import re; h, mi, s = re.search(r'Duration: (\d+):(\d+):([\d.]+)', out).groups(); dur = int(h)*3600+int(mi)*60+float(s)
        src = f'dl_{i}.mp4'
        if not os.path.exists('clips/'+i+'_0.mp4'):
            subprocess.run(['curl','-sL','--retry','4','-o',src,url],check=True,timeout=1200)
        src = f'dl_{i}.mp4'
        if not os.path.exists('clips/'+i+'_0.mp4'):
            subprocess.run(['curl','-sL','--retry','4','-o',src,url],check=True,timeout=1200)
        rnd = random.Random(i); n = 8 if dur > 300 else 5
        for k in range(n):
            t = dur*0.06 + (dur*0.88)*(k+rnd.random()*0.8)/n
            o = f'clips/{i}_{k}.mp4'
            if os.path.exists(o): continue
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', src, '-t', '3.5', '-an',
                '-vf', 'scale=960:540:force_original_aspect_ratio=increase,crop=960:540,fps=30,format=yuv420p',
                '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', o], timeout=240)
        if os.path.exists(src): os.remove(src)
        if os.path.exists(src): os.remove(src)
        return i, f"{m['metadata'].get('title')} ({dur:.0f}s) {f['name']}"
    except Exception as e: return i, 'ERR ' + repr(e)[:200]
with cf.ThreadPoolExecutor(6) as ex:
    for r in ex.map(work, IDS): print(*r, flush=True)
