import { list } from '@vercel/blob';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const file = req.query.file;
  if (!file) {
    return res.status(400).json({ error: 'Missing file parameter' });
  }

  // Sanitize: only allow alphanumeric, dash, underscore, dot
  if (!/^[\w\-.]+$/.test(file)) {
    return res.status(400).json({ error: 'Invalid filename' });
  }

  try {
    const result = await list({ prefix: 'mixes/' });
    const blob = result.blobs.find(b => b.pathname === `mixes/${file}`);
    if (blob) {
      return res.status(200).json({ url: blob.url });
    }
    return res.status(404).json({ error: 'Not found' });
  } catch (e) {
    return res.status(500).json({ error: 'Server error' });
  }
}
