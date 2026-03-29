import { list } from '@vercel/blob';

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

    const images = allBlobs
      .filter(b => {
        const ext = b.pathname.split('.').pop().toLowerCase();
        return ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext);
      })
      .map(b => ({
        url: b.url,
        pathname: b.pathname,
        size: b.size,
        uploadedAt: b.uploadedAt,
      }));

    return res.status(200).json(images);
  } catch (err) {
    console.error('List error:', err);
    return res.status(500).json({ error: err.message });
  }
}
