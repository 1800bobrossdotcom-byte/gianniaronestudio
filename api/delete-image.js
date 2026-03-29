import { del } from '@vercel/blob';

function hashPassword(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) - h) + str.charCodeAt(i);
    h = h | 0;
  }
  return h;
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

  let urls;
  try {
    const parsed = JSON.parse(body);
    urls = parsed.urls;
  } catch (e) {
    return res.status(400).json({ error: 'Invalid JSON body' });
  }

  if (!Array.isArray(urls) || urls.length === 0) {
    return res.status(400).json({ error: 'Missing urls array' });
  }

  // Validate all URLs are blob storage URLs
  const validPrefix = '.public.blob.vercel-storage.com/';
  for (const url of urls) {
    if (typeof url !== 'string' || !url.includes(validPrefix)) {
      return res.status(400).json({ error: 'Invalid blob URL: ' + url });
    }
  }

  try {
    await del(urls);
    return res.status(200).json({ success: true, deleted: urls.length });
  } catch (err) {
    console.error('Delete error:', err);
    return res.status(500).json({ error: err.message });
  }
}
