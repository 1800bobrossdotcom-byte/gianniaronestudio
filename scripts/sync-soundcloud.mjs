// Refresh public/music.json from SoundCloud: every public track (newest first),
// play counts, and 500px cover art saved under public/img/music/.
// The playlists list stays hand-curated; only its track counts are refreshed.
//
//   npm run sync-soundcloud
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const JSON_PATH = path.join(ROOT, 'public', 'music.json');
const ART_DIR = path.join(ROOT, 'public', 'img', 'music');
const UA = { 'User-Agent': 'Mozilla/5.0' };

const music = JSON.parse(readFileSync(JSON_PATH, 'utf8'));

async function get(url, type = 'json') {
  const r = await fetch(url, { headers: UA });
  if (!r.ok) throw new Error(`${r.status} ${url.replace(/client_id=[^&]+/, 'client_id=…')}`);
  return type === 'json' ? r.json() : type === 'text' ? r.text() : Buffer.from(await r.arrayBuffer());
}

// SoundCloud's web app ships a public client id in its JS bundles
async function clientId() {
  const html = await get(music.url, 'text');
  const scripts = [...html.matchAll(/https:\/\/a-v2\.sndcdn\.com\/assets\/[^"]+\.js/g)].map(m => m[0]).reverse();
  for (const s of scripts) {
    const m = (await get(s, 'text')).match(/client_id:"([A-Za-z0-9]{32})"/);
    if (m) return m[1];
  }
  throw new Error('no client_id found in SoundCloud bundles');
}

async function all(url) {
  const out = [];
  for (let next = url; next; ) {
    const page = await get(next);
    out.push(...page.collection);
    next = page.next_href && page.collection.length ? page.next_href + `&client_id=${cid}` : null;
  }
  return out;
}

// artwork id from ".../artworks-<id>-large.jpg"; reuse the local file if it exists
async function art(url) {
  if (!url) return null;
  const m = url.match(/artworks-(.+)-large\.(\w+)/);
  if (!m) return null;
  const local = [`${m[1]}.${m[2]}`, `${m[1]}.jpg`].find(f => existsSync(path.join(ART_DIR, f)));
  if (local) return `/img/music/${local}`;
  writeFileSync(path.join(ART_DIR, `${m[1]}.jpg`), await get(url.replace('-large.', '-t500x500.'), 'buf'));
  console.log('  art', `${m[1]}.jpg`);
  return `/img/music/${m[1]}.jpg`;
}

const cid = await clientId();
const tracks = (await all(`https://api-v2.soundcloud.com/users/${music.userId}/tracks?limit=200&linked_partitioning=1&client_id=${cid}`))
  .filter(t => t.sharing === 'public')
  .sort((a, b) => b.created_at.localeCompare(a.created_at));
const before = new Set(music.tracks.map(t => t.id));

music.tracks = [];
for (const t of tracks) {
  music.tracks.push({
    id: t.id, title: t.title, url: t.permalink_url, date: t.created_at.slice(0, 10),
    duration: Math.round(t.duration / 1000), genre: t.genre || '', plays: t.playback_count ?? 0,
    art: await art(t.artwork_url), description: t.description || '',
  });
  if (!before.has(t.id)) console.log('new:', t.created_at.slice(0, 10), t.title);
}

const sets = new Map((await all(`https://api-v2.soundcloud.com/users/${music.userId}/playlists?limit=50&linked_partitioning=1&client_id=${cid}`))
  .map(p => [p.id, p]));
for (const p of music.playlists) if (sets.has(p.id)) p.tracks = sets.get(p.id).track_count;

music.synced = new Date().toISOString().slice(0, 10);
writeFileSync(JSON_PATH, JSON.stringify(music, null, 1) + '\n');
console.log(`${music.tracks.length} tracks, ${music.playlists.length} playlists, synced ${music.synced}`);
