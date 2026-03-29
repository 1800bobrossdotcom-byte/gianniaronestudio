const fs = require('fs');
const path = require('path');

export default function handler(req, res) {
  // Only allow POST requests from authenticated admin
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Verify admin token
  const token = req.headers['x-admin-token'];
  const expectedHash = -1777485270; // hash of "#1333Love444#1"
  
  function hashPassword(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) {
      h = ((h << 5) - h) + str.charCodeAt(i);
      h = h | 0;
    }
    return h;
  }

  if (!token || hashPassword(token) !== expectedHash) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    const imagesDir = path.join(process.cwd(), 'public', 'images');
    
    // Read all image files
    const files = fs.readdirSync(imagesDir);
    const imageFiles = files.filter(file => {
      const ext = path.extname(file).toLowerCase();
      return ['.jpg', '.jpeg', '.png', '.gif', '.webp'].includes(ext);
    }).sort();

    // Write to image-list.json
    const listPath = path.join(process.cwd(), 'public', 'image-list.json');
    fs.writeFileSync(listPath, JSON.stringify(imageFiles, null, 2), 'utf8');

    return res.status(200).json({ 
      success: true, 
      count: imageFiles.length,
      images: imageFiles 
    });
  } catch (err) {
    console.error('Error regenerating list:', err);
    return res.status(500).json({ error: err.message });
  }
}
