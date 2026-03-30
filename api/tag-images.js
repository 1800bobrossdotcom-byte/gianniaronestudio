import { put, list } from '@vercel/blob';

function hashPassword(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) - h) + str.charCodeAt(i);
    h = h | 0;
  }
  return h;
}

const VALID_TAGS = ['physical', 'digital', 'music', 'written', 'photography'];

async function loadTagsDb() {
  try {
    const result = await list({ prefix: '_meta/' });
    const meta = result.blobs.find(b => b.pathname === '_meta/tags.json');
    if (meta) {
      const res = await fetch(meta.url);
      return await res.json();
    }
  } catch (e) {}
  return {};
}

async function saveTagsDb(db) {
  await put('_meta/tags.json', JSON.stringify(db), {
    access: 'public',
    addRandomSuffix: false,
    contentType: 'application/json',
  });
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const token = req.headers['x-admin-token'];
  const expectedHash = -2057484341;
  if (!token || hashPassword(token) !== expectedHash) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  let body = '';
  await new Promise((resolve) => {
    req.on('data', chunk => { body += chunk; });
    req.on('end', resolve);
  });

  let urls, tag;
  try {
    const parsed = JSON.parse(body);
    urls = parsed.urls;
    tag = parsed.tag;
  } catch (e) {
    return res.status(400).json({ error: 'Invalid JSON body' });
  }

  if (!Array.isArray(urls) || urls.length === 0) {
    return res.status(400).json({ error: 'Missing urls array' });
  }

  if (!VALID_TAGS.includes(tag)) {
    return res.status(400).json({ error: 'Invalid tag. Allowed: ' + VALID_TAGS.join(', ') });
  }

  try {
    const db = await loadTagsDb();
    for (const url of urls) {
      if (typeof url === 'string') {
        db[url] = tag;
      }
    }
    await saveTagsDb(db);
    return res.status(200).json({ success: true, updated: urls.length, tag: tag });
  } catch (err) {
    console.error('Tag error:', err);
    return res.status(500).json({ error: err.message });
  }
}
