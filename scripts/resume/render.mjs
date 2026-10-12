// Render scripts/resume/resume.html to a PDF with Chromium (Playwright).
//
//   node scripts/resume/render.mjs <static-fonts-dir> <out.pdf>
//
// <static-fonts-dir> holds the instances written by instances.py. Plex Mono is
// already static and comes straight from public/fonts. Set PLAYWRIGHT_MODULE to
// a playwright entry point and CHROMIUM_PATH to a browser if they are not
// resolvable from here.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const pub = path.join(here, '..', '..', 'public', 'fonts');
const [fontsDir, out] = process.argv.slice(2);
if (!fontsDir || !out) { console.error('usage: node render.mjs <static-fonts-dir> <out.pdf>'); process.exit(2); }

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');

const face = (family, weight, file, fmt) =>
  `@font-face{font-family:'${family}';font-weight:${weight};font-style:normal;` +
  `src:url(data:font/${fmt};base64,${readFileSync(file).toString('base64')}) format('${fmt === 'ttf' ? 'truetype' : fmt}')}`;
const faces = [
  ...[400, 500, 600, 700].map(w => face('Plex Sans', w, path.join(fontsDir, `ibm-plex-sans-${w}.ttf`), 'ttf')),
  ...[800, 900].map(w => face('Big Shoulders', w, path.join(fontsDir, `big-shoulders-display-${w}.ttf`), 'ttf')),
  ...[400, 500, 600].map(w => face('Plex Mono', w, path.join(pub, `ibm-plex-mono-${w}.woff2`), 'woff2')),
].join('\n');

const html = readFileSync(path.join(here, 'resume.html'), 'utf8')
  .replace(/<style id="fonts">[\s\S]*?<\/style>/, `<style id="fonts">${faces}</style>`);

const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const page = await browser.newPage({ viewport: { width: 816, height: 1056 } });
await page.emulateMedia({ media: 'print' });
await page.setContent(html, { waitUntil: 'load' });
await page.evaluate(async () => {
  const want = ['400 10px "Plex Sans"', '500 10px "Plex Sans"', '600 10px "Plex Sans"', '700 10px "Plex Sans"',
    '800 10px "Big Shoulders"', '900 10px "Big Shoulders"', '400 10px "Plex Mono"', '500 10px "Plex Mono"', '600 10px "Plex Mono"'];
  await Promise.all(want.map(f => document.fonts.load(f)));
  await document.fonts.ready;
  const missing = want.filter(f => !document.fonts.check(f));
  if (missing.length) throw new Error('fonts did not load: ' + missing.join(', '));
});

// every page must hold its content: report the slack (or overflow) in points
const fit = await page.evaluate(() => [...document.querySelectorAll('.flow')].map(f => {
  const last = [...f.children].at(-1).getBoundingClientRect().bottom;
  return Math.round((f.getBoundingClientRect().bottom - last) * 0.75 * 10) / 10;
}));
console.log('slack per page (pt):', fit.join(', '));
if (fit.some(s => s < 0)) { await browser.close(); throw new Error('content overflows a page'); }

await page.pdf({ path: out, width: '8.5in', height: '11in', printBackground: true, preferCSSPageSize: true,
  tagged: true, outline: true });
await browser.close();
console.log('wrote', out);
