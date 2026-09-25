import json, subprocess, urllib.request, urllib.parse, random, os, re, concurrent.futures as cf
SRC = {  # id: tags
 'gov.archives.arc.45017':'moon space', 'a-trip-to-the-moon-le-voyage-dans-la-lune-1902':'moon stage', 'TheEclipse1907':'moon stars sun',
 'solar-eclipse-1900-documentary-short-1900':'sun stars moon',
 'gov.dod.dimoc.25183':'ocean water', 'silent-un-drame-au-fond-de-la-mer-aka-drama-at-the-bottom-of-the-sea':'ocean water',
 'fc-fc-474a-c':'ocean water', 'fc-fc-2427':'water', 'fc-fc-2493':'water', 'silent-captain-nissen-going-through-whirlpool-rapids-niagara-falls':'water',
 '33-203':'birds animals', 'fc-fc-4869':'birds animals', 'fc-fc-473':'animals zoo', 'fc-fc-214':'animals zoo birds', 'MareyFilmsVBVariousAnimals':'animals zoo motion',
 '33-189':'horse motion animals', 'gov.dod.dimoc.23735':'morse hands', 'gov.archives.arc.36813':'morse hands', '111-m-121':'morse',
 'gov.dod.dimoc.39864':'electric numbers', 'gov.dod.dimoc.39951':'electric numbers', 'gov.dod.dimoc.28336':'electric building',
 '111-LC-44557':'snake', '33-337-r2':'flowers', 'fc-fc-904':'school children', '111-adc-2342':'grave', 'gov.archives.arc.36909':'grave',
 '33-152':'mountain wind', 'fc-fc-4104':'mountain wind', '33-420-r1':'sheep animals', 'fc-fc-1685':'sheep animals',
 '330-dvic-24159-r1':'film record', 'serpentine-dance-1895-yt':'dance light', 'denishawn-dance-film':'dance', 'silent-ballet-des-sylphides-aka-dance-of-the-sylphs':'dance stage',
 'migration-osinoff':'circus', 'fc-fc-216':'circus animals', 'the-devils-circus-1926-by-benjamin-christensen':'circus stage',
 'the-boxing-cats-prof.-weltons-1894':'cat', 'silent-the-sick-kitten':'cat', 'silent-la-clownesse-fantme-aka-the-magician-and-the-imp':'stage ghost',
 'BobsElectricTheater':'stage electric', 'silent-le-piano-irrsistible-aka-the-irresistible-piano':'piano', 'silent-scrooge-or-marleys-ghost':'ghost',
 'LegendOfAGhost1908':'ghost', 'silent-clash-of-the-wolves':'wolf', 'fc-fc-327':'clock numbers', '70-85':'clock', 'fc-fc-2587':'car',
 'silent-uncle-joshs-nightmare':'sleep ghost', 'PreviewTheTiredTailorsDream':'sleep', 'silent-the-stenographers-friend-or-what-was-accomplished-by-an-edison-business-phonograph':'record words',
}
os.makedirs('clips', exist_ok=True); os.makedirs('dl', exist_ok=True)
def pick(files):
    v = [f for f in files if f['name'].lower().endswith(('.mp4', '.m4v', '.ogv', '.mpeg', '.avi', '.mkv', '.webm'))]
    def score(f):
        sz = int(f.get('size', 1e10)); n = f['name'].lower()
        return (not n.endswith('.mp4'), '512kb' not in n and '.ia.mp4' not in n and sz > 400e6, sz > 900e6, -min(sz, 400e6))
    v.sort(key=score); return v[0] if v else None
def work(i):
    try:
        m = json.load(urllib.request.urlopen(f'https://archive.org/metadata/{i}', timeout=60))
        f = pick(m['files'])
        if not f: return i, 'novideo'
        src = f'dl/{i}.bin'
        if not os.path.exists(f'clips/{i}__0.mp4'):
            subprocess.run(['curl', '-sL', '--retry', '4', '--max-time', '1500', '-o', src, f"https://archive.org/download/{i}/{urllib.parse.quote(f['name'])}"], check=True)
            out = subprocess.run(['ffmpeg', '-i', src], capture_output=True, text=True).stderr
            h, mi, s = re.search(r'Duration: (\d+):(\d+):([\d.]+)', out).groups(); dur = int(h)*3600+int(mi)*60+float(s)
            n = int(min(16, max(4, dur // 25)))
            rnd = random.Random(i)
            for k in range(n):
                t = dur*0.04 + dur*0.92*(k + rnd.random()*0.7)/n
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', src, '-t', '3.5', '-an',
                    '-vf', 'scale=960:540:force_original_aspect_ratio=increase,crop=960:540,fps=30,format=yuv420p',
                    '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', f'clips/{i}__{k}.mp4'], timeout=300)
            os.remove(src)
        return i, f"{m['metadata'].get('title')} | {m['metadata'].get('year') or m['metadata'].get('date')} | {f['name']}"
    except Exception as e: return i, 'ERR ' + repr(e)[:150]
if __name__ == '__main__':
    json.dump(SRC, open('tags.json', 'w'), indent=1)
    with cf.ThreadPoolExecutor(3) as ex:
        for r in ex.map(work, SRC): print(*r, flush=True)
