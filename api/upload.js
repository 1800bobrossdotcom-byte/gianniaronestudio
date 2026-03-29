import { put } from '@vercel/blob';

export const config = {
  api: {
    bodyParser: false,
  },
};

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

  const filename = req.query.filename;
  if (!filename) {
    return res.status(400).json({ error: 'Missing filename' });
  }

  // Sanitize filename - only allow alphanumeric, dash, underscore, dot
  const sanitized = filename.replace(/[^a-zA-Z0-9._-]/g, '_');
  const ext = sanitized.split('.').pop().toLowerCase();
  const allowed = ['jpg', 'jpeg', 'png', 'gif', 'webp'];
  if (!allowed.includes(ext)) {
    return res.status(400).json({ error: 'Invalid file type. Allowed: ' + allowed.join(', ') });
  }

  try {
    const blob = await put(sanitized, req, {
      access: 'public',
      addRandomSuffix: true,
    });
    return res.status(200).json({ url: blob.url, pathname: blob.pathname });
  } catch (err) {
    console.error('Upload error:', err);
    return res.status(500).json({ error: err.message });
  }
}
