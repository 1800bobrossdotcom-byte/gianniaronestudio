#!/usr/bin/env node
/**
 * Refresh public/videos.json and public/img/video/*.jpg from Vimeo.
 *
 *   node scripts/sync-vimeo.mjs            # sync vimeo.com/uaawtf
 *   VIMEO_USER=someone node scripts/sync-vimeo.mjs
 *
 * Uses Vimeo's public simple API (no token). New videos are added with
 * category "spots" unless a title keyword says otherwise; existing entries
 * keep their hand-set category and featured order, so edit videos.json
 * freely and re-run whenever you upload something new.
 *
 * Note: only videos whose Vimeo privacy allows embedding "anywhere" will
 * play inline on the site. The rest link out to vimeo.com.
 */
import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const USER = process.env.VIMEO_USER || 'uaawtf';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const JSON_PATH = path.join(root, 'public', 'videos.json');
const THUMB_DIR = path.join(root, 'public', 'img', 'video');

const CATEGORIES = ['reels', 'spots', 'entertainment', 'music', 'art'];

function guessCategory(title) {
  const t = (title || '').toLowerCase();
  if (/\breel\b|r33l/.test(t)) return 'reels';
  if (/lyric video|music video|official audio|remix|\(official/.test(t)) return 'music';
  if (/disney|sony|universal|hulu|fox|dolby|paramount|pikachu|top gun|nope|matrix|walking dead/.test(t)) return 'entertainment';
  if (/spec|spot|recruit|campaign|commercial/.test(t)) return 'spots';
  return 'spots';
}

function clean(s) {
  return String(s || '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    .trim();
}

async function fetchAll() {
  const out = [];
  for (let page = 1; page <= 20; page++) {
    const url = `https://vimeo.com/api/v2/${USER}/videos.json?page=${page}`;
    const res = await fetch(url, { headers: { 'User-Agent': 'gianniaronestudio-sync/1.0' } });
    if (res.status === 404) break;
    if (!res.ok) throw new Error(`${url} → HTTP ${res.status}`);
    const data = await res.json();
    if (!Array.isArray(data) || data.length === 0) break;
    out.push(...data);
    if (data.length < 20) break;
    await new Promise(r => setTimeout(r, 800));
  }
  return out;
}

async function exists(p) { try { await access(p); return true; } catch { return false; } }

async function main() {
  let existing = { videos: [] };
  try { existing = JSON.parse(await readFile(JSON_PATH, 'utf8')); } catch {}
  const byId = new Map(existing.videos.map(v => [v.id, v]));

  const raw = await fetchAll();
  console.log(`fetched ${raw.length} videos for ${USER}`);
  await mkdir(THUMB_DIR, { recursive: true });

  const videos = [];
  for (const v of raw) {
    const prev = byId.get(v.id) || {};
    const thumbFile = path.join(THUMB_DIR, `${v.id}.jpg`);
    const large = v.thumbnail_large || '';
    if (!(await exists(thumbFile)) && large) {
      const candidates = [large.replace('_640', '_960x540'), large];
      for (const src of candidates) {
        try {
          const r = await fetch(src);
          if (!r.ok) continue;
          const buf = Buffer.from(await r.arrayBuffer());
          if (buf.length < 1000) continue;
          await writeFile(thumbFile, buf);
          console.log(`  thumb ${v.id}`);
          break;
        } catch {}
      }
    }
    const category = CATEGORIES.includes(prev.category) ? prev.category : guessCategory(v.title);
    videos.push({
      id: v.id,
      title: clean(v.title),
      description: clean(v.description),
      date: (v.upload_date || '').slice(0, 10),
      duration: v.duration,
      width: v.width,
      height: v.height,
      embeddable: v.embed_privacy === 'anywhere' || v.embed_privacy === 'approved',
      category,
      featured: prev.featured ?? null,
      thumb: (await exists(thumbFile)) ? `/img/video/${v.id}.jpg` : null,
      remoteThumb: large,
      url: v.url,
    });
  }
  videos.sort((a, b) => (a.date < b.date ? 1 : -1));

  const removed = existing.videos.filter(v => !videos.find(n => n.id === v.id));
  if (removed.length) console.log(`no longer on Vimeo: ${removed.map(v => v.id).join(', ')}`);

  await writeFile(JSON_PATH, JSON.stringify({
    user: USER,
    userUrl: `https://vimeo.com/${USER}`,
    synced: new Date().toISOString().slice(0, 10),
    videos,
  }, null, 1) + '\n');
  console.log(`wrote ${videos.length} videos → public/videos.json`);
}

main().catch(e => { console.error(e); process.exit(1); });
