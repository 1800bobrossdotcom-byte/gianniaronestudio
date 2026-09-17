#!/usr/bin/env node
/**
 * Push the harvested art (Behance, SuperRare, Fake Rares) into the gallery's
 * Vercel Blob store, tagged "digital", so it lives alongside the uploads made
 * from the admin panel.
 *
 *   BLOB_READ_WRITE_TOKEN=vercel_blob_rw_... node scripts/upload-art-to-blob.mjs
 *
 * Get the token from the Vercel project: Storage → your Blob store → .env.local
 * (or Settings → Environment Variables). Safe to re-run: files already present
 * are skipped. Loops are uploaded as their poster frame (the gallery is stills).
 */
import { list, put } from '@vercel/blob';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

if (!process.env.BLOB_READ_WRITE_TOKEN) { console.error('Set BLOB_READ_WRITE_TOKEN first.'); process.exit(1); }
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'public');
const art = JSON.parse(await readFile(path.join(root, 'art.json'), 'utf8'));

const files = [];
for (const b of art.behance) files.push({ local: b.type === 'loop' ? b.poster : b.src, name: `art/behance-${b.id}${path.extname(b.type === 'loop' ? b.poster : b.src)}` });
for (const w of art.superrare) files.push({ local: w.src, name: `art/superrare-${path.basename(w.src)}` });
for (const c of art.fakerares) files.push({ local: c.type === 'loop' ? c.poster : c.src, name: `art/fakerares-${c.title}${path.extname(c.type === 'loop' ? c.poster : c.src)}` });

const existing = new Set();
let cursor;
do { const r = await list({ cursor, prefix: 'art/' }); r.blobs.forEach(b => existing.add(b.pathname)); cursor = r.cursor; } while (cursor);

// tags db lives at _meta/tags.json (url -> tag)
let tags = {};
try { const meta = (await list({ prefix: '_meta/' })).blobs.find(b => b.pathname === '_meta/tags.json'); if (meta) tags = await (await fetch(meta.url)).json(); } catch {}

let uploaded = 0;
for (const f of files) {
  if (existing.has(f.name)) continue;
  const buf = await readFile(path.join(root, f.local));
  const type = f.local.endsWith('.webp') ? 'image/webp' : 'image/jpeg';
  const blob = await put(f.name, buf, { access: 'public', addRandomSuffix: false, contentType: type });
  tags[blob.url] = 'digital';
  uploaded++;
  console.log('uploaded', f.name);
}
await put('_meta/tags.json', JSON.stringify(tags), { access: 'public', addRandomSuffix: false, contentType: 'application/json' });
console.log(`done: ${uploaded} uploaded, ${files.length - uploaded} already there`);
