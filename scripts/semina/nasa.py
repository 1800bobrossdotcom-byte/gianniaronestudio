import json, urllib.request, urllib.parse, subprocess, os, random, re
IDS = {'GSFC_20190513_m4714_Lee_Lincoln_Scarp_Moon_Flyover':'moon', 'KSC-20260201-MH-JBS01-0001-Artemis_II_Full_Moon_Sunrise_Timelapse-M18703':'moon light',
 'GSFC_20160426_SDO_m12224_SolarFlare':'sun light electric', 'GSFC_20170403_Trio_m12563_SolarFlares':'sun light electric',
 'GSFC_20170412_Lights_m12573_EarthAtNight':'light stars numbers', 'GSFC_20100915_Firefly_m10645_BRolll':'electric', 'Evolution_of_Galaxies_H264':'stars',
 'GSFC_20110617_LRO_m10794_Eclipse_Librating_Moon':'moon', 'GSFC_20161212_Tidal_m12450_Magnetic':'ocean tides'}
os.makedirs('clips', exist_ok=True); tags = json.load(open('tags.json')) if os.path.exists('tags.json') else {}
for i, t in IDS.items():
    try:
        a = json.load(urllib.request.urlopen('https://images-api.nasa.gov/asset/' + urllib.parse.quote(i), timeout=60))['collection']['items']
        mp4 = [x['href'] for x in a if x['href'].endswith('.mp4')]
        mp4.sort(key=lambda h: (('~mobile' in h) + 2 * ('~small' in h), -('~medium' in h), ('~orig' in h)))
        pref = [h for h in mp4 if '~medium' in h] or [h for h in mp4 if '~orig' not in h] or mp4
        url = pref[0].replace('http://', 'https://').replace(' ', '%20'); src = f'dl/{i}.mp4'
        subprocess.run(['curl', '-sL', '--max-time', '900', '-o', src, url], check=True)
        out = subprocess.run(['ffmpeg', '-i', src], capture_output=True, text=True).stderr
        h, mi, s = re.search(r'Duration: (\d+):(\d+):([\d.]+)', out).groups(); dur = int(h)*3600+int(mi)*60+float(s)
        n = int(min(8, max(3, dur // 15))); rnd = random.Random(i)
        for k in range(n):
            tt = dur*0.05 + dur*0.9*(k + rnd.random()*0.6)/n
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{tt:.2f}', '-i', src, '-t', '3.5', '-an', '-vf',
                'scale=960:540:force_original_aspect_ratio=increase,crop=960:540,fps=30,format=yuv420p', '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', f'clips/nasa-{i}__{k}.mp4'])
        os.remove(src); print(i, n, url.split('/')[-1], flush=True)
        tags['nasa-' + i] = t
    except Exception as e: print(i, 'ERR', repr(e)[:120])
json.dump(tags, open('tags_nasa.json', 'w'), indent=1)
