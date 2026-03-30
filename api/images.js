import { list } from '@vercel/blob';

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

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    let allBlobs = [];
    let cursor;

    do {
      const result = await list({ cursor });
      allBlobs = allBlobs.concat(result.blobs);
      cursor = result.cursor;
    } while (cursor);

    const tagsDb = await loadTagsDb();

    const images = allBlobs
      .filter(b => {
        if (b.pathname.startsWith('_meta/')) return false;
        const ext = b.pathname.split('.').pop().toLowerCase();
        return ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext);
      })
      .map(b => ({
        url: b.url,
        pathname: b.pathname,
        size: b.size,
        uploadedAt: b.uploadedAt,
        tag: tagsDb[b.url] || 'physical',
      }));

    return res.status(200).json(images);
  } catch (err) {
    console.error('List error:', err);
    return res.status(500).json({ error: err.message });
  }
}
