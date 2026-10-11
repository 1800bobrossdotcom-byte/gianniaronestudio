"""Write static instances of the site's variable fonts for the résumé PDF.

Chromium embeds variable fonts in PDFs as Type 3 glyph procedures, which some
applicant-tracking systems read poorly. Static instances embed as ordinary
TrueType subsets. The instances are build intermediates: they go to the folder
given on the command line, never into public/.

    python3 scripts/resume/instances.py <outdir>
"""
import os
import sys

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'public', 'fonts')
WANT = {
    'ibm-plex-sans-400.woff2': [400, 500, 600, 700],
    'big-shoulders-display-900.woff2': [800, 900],
}


def main(out):
    os.makedirs(out, exist_ok=True)
    for src, weights in WANT.items():
        family = src.rsplit('-', 1)[0]
        for w in weights:
            f = TTFont(os.path.join(FONTS, src))
            inst = instancer.instantiateVariableFont(f, {'wght': w}, updateFontNames=False)
            inst.flavor = None
            path = os.path.join(out, f'{family}-{w}.ttf')
            inst.save(path)
            print(path)


if __name__ == '__main__':
    main(sys.argv[1])
