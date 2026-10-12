"""Build public/resume/gianni-arone-resume.pdf from scripts/resume/resume.html.

    python3 scripts/resume/build.py [--preview DIR]

Steps: static font instances (instances.py) -> Chromium render (render.mjs) ->
document metadata -> checks -> optional PNG previews of each page.
Needs fonttools, pypdf and playwright; pypdfium2 for --preview.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

from pypdf import PdfReader, PdfWriter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'public', 'resume', 'gianni-arone-resume.pdf')
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import instances  # noqa: E402

META = {
    '/Title': 'Gianni Arone — Résumé',
    '/Author': 'Gianni Arone',
    '/Subject': 'Director of Digital Operations · AI Product Builder · Senior Motion Designer · www.gianniarone.com',
    '/Keywords': 'Gianni Arone, director of digital operations, creative technologist, AI product builder, AI engineering, Claude, Claude Code, '
                 'ChatGPT, OpenAI, Anthropic API, prompt engineering, agent workflows, APIs, React, Next.js, Node, '
                 'Rust, Postgres, senior motion designer, video editor, social content, Rochester NY',
    '/Creator': 'www.gianniarone.com',
}
# words that must survive into the text layer, and words that must not
MUST = ['Gianni Arone', 'www.gianniarone.com', 'gianniaronestudio@gmail.com', 'Claude', 'ChatGPT', 'Evolution24']
NEVER = ['linktr.ee', 'Linktree']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', help='write page PNGs to this folder')
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix='resume-')
    try:
        instances.main(os.path.join(tmp, 'fonts'))
        raw = os.path.join(tmp, 'raw.pdf')
        subprocess.run(['node', os.path.join(HERE, 'render.mjs'), os.path.join(tmp, 'fonts'), raw], check=True)

        writer = PdfWriter(clone_from=raw)
        writer.add_metadata(META)
        with open(OUT, 'wb') as f:
            writer.write(f)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    reader = PdfReader(OUT)
    text = '\n'.join(p.extract_text() for p in reader.pages)
    fonts = {f.get_object().get('/Subtype') for p in reader.pages for f in p['/Resources']['/Font'].values()}
    links = sorted({a.get_object()['/A'].get('/URI') for p in reader.pages for a in p.get('/Annots', [])
                    if '/A' in a.get_object() and '/URI' in a.get_object()['/A']})
    low = text.lower()
    problems = [f'missing "{w}"' for w in MUST if w.lower() not in low] + [f'found "{w}"' for w in NEVER if w.lower() in low]
    if not reader.pages[0].extract_text().lstrip().upper().startswith('GIANNI ARONE'):
        problems.append('page 1 text does not start with the name (paint order is off)')
    if len(reader.pages) != 2:
        problems.append(f'{len(reader.pages)} pages, expected 2')
    if '/Type3' in fonts:
        problems.append('Type 3 fonts embedded')
    print(f'{OUT}: {len(reader.pages)} pages, {os.path.getsize(OUT) // 1024} KB, fonts {sorted(fonts)}')
    print('links:', ', '.join(links))
    if problems:
        sys.exit('FAILED: ' + '; '.join(problems))

    if args.preview:
        import pypdfium2 as pdfium
        os.makedirs(args.preview, exist_ok=True)
        doc = pdfium.PdfDocument(OUT)
        for i in range(len(doc)):
            path = os.path.join(args.preview, f'resume-p{i + 1}.png')
            doc[i].render(scale=2).to_pil().save(path)
            print('preview', path)


if __name__ == '__main__':
    main()
