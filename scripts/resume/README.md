# Résumé PDF

`public/resume/gianni-arone-resume.pdf` is built from `resume.html` in this folder. The copy mirrors `public/resume/index.html`, so change both together.

```
python3 scripts/resume/build.py --preview /tmp/resume-preview
```

Requirements: `fonttools`, `pypdf`, Node with `playwright` (set `PLAYWRIGHT_MODULE` to its entry file and `CHROMIUM_PATH` to a browser if neither resolves on its own), and `pypdfium2` for `--preview`.

| Step | File | What it does |
| --- | --- | --- |
| 1 | `instances.py` | Static instances of the site's variable fonts (Plex Sans 400–700, Big Shoulders 800/900), written to a temp folder. Chromium embeds variable fonts as Type 3 glyphs, which some applicant-tracking systems read poorly. |
| 2 | `render.mjs` | Inlines the fonts, renders both Letter pages with Chromium as a tagged PDF with an outline, and fails if either page overflows. It prints the spare room per page in points. |
| 3 | `build.py` | Sets title, author, subject and keywords, then checks the result: 2 pages, no Type 3 fonts, page 1 text starting with the name, the contact details present and no Linktree. |

Layout rules that keep the text layer clean for parsers: no letter-spacing above `.08em` (wider tracking extracts as spaced-out letters), and no `position` on elements that hold text, since Chromium paints positioned boxes after the normal flow and the PDF text then comes out of order.
