import re, json, subprocess, urllib.request, urllib.parse, os, random, html, concurrent.futures as cf
UA = {'User-Agent': 'Mozilla/5.0'}
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode('utf8', 'ignore')
DV = {'thermal':'thermal drone footage', 'nightvision':'night vision', 'drone':'drone b-roll', 'jets':'f-35 takeoff', 'carrier':'aircraft carrier flight deck launch',
      'rocket':'rocket launch space force', 'osprey':'osprey night', 'parachute':'freefall parachute', 'hurricane':'hurricane aerial', 'wildfire':'wildfire aerial',
      'seas':'heavy seas ship', 'cyber':'cyber operations center', 'laser':'laser weapon', 'lightning':'lightning storm', 'timelapse':'timelapse night city', 'snow':'arctic snow helicopter'}
os.makedirs('clips', exist_ok=True); os.makedirs('dl', exist_ok=True)
meta = {}
def dv(tag, q, k=3):
    pg = get('https://www.dvidshub.net/search/?' + urllib.parse.urlencode({'q': q, 'filter[type]': 'video', 'sort': 'relevance'}))
    ids = list(dict.fromkeys(re.findall(r'href="(/video/\d+/[^"]+)"', pg)))[:k * 2]
    out = []
    for p in ids:
        if len(out) >= k: break
        try:
            h = get('https://www.dvidshub.net' + p)
            mp4 = re.findall(r'https://[^"\' ]+\.mp4', h)
            if not mp4: continue
            title = html.unescape(re.search(r'<title>([^<]+)</title>', h).group(1)).split(' | ')[0].strip()
            out.append(dict(id='dvids-' + p.split('/')[2], tag=tag, url=mp4[0], title=title, page='https://www.dvidshub.net' + p, org='DVIDS'))
        except Exception as e: print('ERR', p, e)
    return out
def nasa(tag, q, k=3):
    d = json.loads(get('https://images-api.nasa.gov/search?' + urllib.parse.urlencode({'q': q, 'media_type': 'video'})))['collection']['items'][:k * 2]
    out = []
    for x in d:
        if len(out) >= k: break
        nid = x['data'][0]['nasa_id']
        a = json.loads(get('https://images-api.nasa.gov/asset/' + urllib.parse.quote(nid)))['collection']['items']
        mp4 = [y['href'] for y in a if y['href'].endswith('.mp4')]
        pref = [h for h in mp4 if '~medium' in h] or [h for h in mp4 if '~orig' not in h] or mp4
        if pref: out.append(dict(id='nasa-' + re.sub(r'[^A-Za-z0-9_-]', '_', nid)[:80], tag=tag, url=pref[0].replace('http://', 'https://').replace(' ', '%20'), title=x['data'][0]['title'], page='https://images.nasa.gov/details/' + urllib.parse.quote(nid), org='NASA'))
    return out
NA = {'iss':'ISS earth night timelapse', 'launch':'launch pad liftoff slow motion', 'spacewalk':'spacewalk', 'sun':'SDO sun 4K', 'mars':'Perseverance Mars', 'aurora':'aurora from space station', 'storm':'GOES satellite hurricane'}
def cut(it):
    o = f"clips/{it['id']}__0.mp4"
    if os.path.exists(o): return it['id'], 'cached'
    src = f"dl/{it['id']}.mp4"
    try:
        subprocess.run(['curl', '-sL', '--max-time', '900', '-o', src, it['url']], check=True)
        e = subprocess.run(['ffmpeg', '-i', src], capture_output=True, text=True).stderr
        h, m, s = re.search(r'Duration: (\d+):(\d+):([\d.]+)', e).groups(); dur = int(h) * 3600 + int(m) * 60 + float(s)
        n = int(min(8, max(3, dur // 12))); r = random.Random(it['id'])
        for k in range(n):
            t = dur * 0.05 + dur * 0.9 * (k + r.random() * 0.6) / n
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', src, '-t', '3.5', '-an', '-vf',
                'scale=960:540:force_original_aspect_ratio=increase,crop=960:540,fps=30,format=yuv420p', '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', f"clips/{it['id']}__{k}.mp4"])
        os.remove(src); return it['id'], n
    except Exception as ex: return it['id'], 'ERR ' + repr(ex)[:100]
items = []
for t, q in DV.items(): items += dv(t, q)
for t, q in NA.items(): items += nasa(t, q)
items = list({i['id']: i for i in items}.values())
json.dump(items, open('sources.json', 'w'), indent=1)
print(len(items), 'sources', flush=True)
with cf.ThreadPoolExecutor(4) as ex:
    for r in ex.map(cut, items): print(*r, flush=True)
