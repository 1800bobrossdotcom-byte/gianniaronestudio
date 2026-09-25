import json, urllib.request, fitz, os, concurrent.futures as cf
IDS="""cia-readingroom-document-cia-rdp96-00787r000200080037-4 cia-readingroom-document-cia-rdp96-00788r000300840001-7
cia-readingroom-document-cia-rdp75-00149r000400460033-5 cia-readingroom-document-0005516191 cia-readingroom-document-0005516119
cia-readingroom-document-cia-rdp96-00788r001100400016-0 cia-readingroom-document-cia-rdp78-04913a000100030121-8
cia-readingroom-document-cia-rdp78-04913a000100030103-8 cia-readingroom-document-00146165
cia-readingroom-document-cia-rdp70-00211r000300300002-2 cia-readingroom-document-cia-rdp66b00664r000500160015-3
cia-readingroom-document-0005968809 fbi-file-on-nicola-tesla FBICOINTELPRONewLeftHQ1 cryptolog_73-nsa cryptolog_04-nsa cryptolog_50-nsa""".split()
os.makedirs('docs',exist_ok=True)
def w(i):
    try:
        m=json.load(urllib.request.urlopen(f'https://archive.org/metadata/{i}',timeout=60))
        pdfs=[f for f in m['files'] if f['name'].lower().endswith('.pdf')]
        pdfs.sort(key=lambda f:int(f.get('size',1e12)))
        f=pdfs[0]; p=f'docs/{i}.pdf'
        urllib.request.urlretrieve(f"https://archive.org/download/{i}/{urllib.request.quote(f['name'])}",p)
        d=fitz.open(p); n=0
        for k in range(min(len(d),40)):
            if n>=4: break
            if len(d)>6 and k%max(1,len(d)//5)!=0: continue
            pg=d[k]; z=1500/max(pg.rect.width,pg.rect.height)
            pg.get_pixmap(matrix=fitz.Matrix(z,z),colorspace=fitz.csGRAY).save(f'docs/{i}_{k}.png'); n+=1
        os.remove(p); return i,len(d),n
    except Exception as e: return i,'ERR',repr(e)[:150]
with cf.ThreadPoolExecutor(6) as ex:
    for r in ex.map(w,IDS): print(*r,flush=True)
