/**
 * Alchemy Integration Module
 * Fetches curated LOVEBEING NFT images and integrates with GPU-optimized gallery
 */

const AlchemyIntegration = (() => {
  const CONFIG = {
    apiUrl: 'https://deca.art/LOVEBEING',
    storageKey: 'alchemySelection',
    excludedCategories: ['DARPA', 'ERC1155', 'ADVERTISEMENTS'],
    cacheExpiry: 3600000, // 1 hour
  };

  let cachedImages = null;
  let cacheTime = null;

  /**
   * Fetch images from deca.art using simple DOM parsing (client-side)
   */
  async function fetchFromAPI() {
    try {
      // Check cache first
      if (cachedImages && cacheTime && Date.now() - cacheTime < CONFIG.cacheExpiry) {
        console.log('[Alchemy] Using cached images');
        return cachedImages;
      }

      console.log('[Alchemy] Fetching from', CONFIG.apiUrl);
      const response = await fetch(CONFIG.apiUrl, {
        mode: 'cors',
        cache: 'force-cache'
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const html = await response.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');

      const images = [];
      const processed = new Set();

      // Find all images from media-cdn
      const imgElements = Array.from(doc.querySelectorAll('img[src*="media-cdn.deca.art"]'));

      imgElements.forEach((img, idx) => {
        const src = img.src;
        if (src && !processed.has(src)) {
          processed.add(src);

          // Extract title and category from context
          const altText = img.alt || '';
          let category = 'UNCATEGORIZED';

          // Try to find category from heading elements nearby
          const section = img.closest('section') || img.closest('div[class*="collection"]');
          if (section) {
            const heading = section.querySelector('h1, h2, h3');
            if (heading) {
              category = heading.textContent.trim().substring(0, 50);
            }
          }

          // Skip excluded categories
          if (CONFIG.excludedCategories.some(exc => 
            category.toUpperCase().includes(exc.toUpperCase())
          )) {
            return;
          }

          images.push({
            url: src,
            title: altText.substring(0, 80),
            category: category,
            source: 'alchemy'
          });
        }
      });

      cachedImages = images;
      cacheTime = Date.now();

      console.log(`[Alchemy] Fetched ${images.length} curated images`);
      return images;

    } catch (err) {
      console.error('[Alchemy] Fetch failed:', err);
      return [];
    }
  }

  /**
   * Get selected images from localStorage
   */
  function getSelectedFromStorage() {
    try {
      const stored = localStorage.getItem(CONFIG.storageKey);
      if (stored) {
        const data = JSON.parse(stored);
        return data.urls || [];
      }
    } catch (err) {
      console.error('[Alchemy] Storage read failed:', err);
    }
    return [];
  }

  /**
   * Merge local images with curated Alchemy selection
   */
  async function mergeWithLocal(localImages) {
    const selectedAlchemy = getSelectedFromStorage();

    if (selectedAlchemy.length === 0) {
      console.log('[Alchemy] No curated selection in storage, using local images only');
      return localImages;
    }

    // Combine: local + selected alchemy
    const merged = [
      ...localImages,
      ...selectedAlchemy
    ];

    console.log(`[Alchemy] Merged ${localImages.length} local + ${selectedAlchemy.length} alchemy = ${merged.length} total`);
    return merged;
  }

  /**
   * Experimental: Fetch on demand with streaming updates
   * Use this if you want to populate selection UI dynamically
   */
  async function fetchForCuration(onProgress) {
    const images = [];
    try {
      const response = await fetch(CONFIG.apiUrl);
      const html = await response.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');

      const imgElements = Array.from(doc.querySelectorAll('img[src*="media-cdn.deca.art"]'));
      const processed = new Set();

      imgElements.forEach((img, idx) => {
        const src = img.src;
        if (src && !processed.has(src)) {
          processed.add(src);

          let category = 'UNCATEGORIZED';
          const section = img.closest('section') || img.closest('div');
          const heading = section?.querySelector('h1, h2, h3');
          if (heading) {
            category = heading.textContent.trim().substring(0, 50);
          }

          if (!CONFIG.excludedCategories.some(exc => 
            category.toUpperCase().includes(exc.toUpperCase())
          )) {
            const item = {
              id: `alchemy_${processed.size}`,
              url: src,
              title: img.alt?.substring(0, 80) || '',
              category: category
            };
            images.push(item);

            if (onProgress) {
              onProgress(item, images.length);
            }
          }
        }
      });

      return images;
    } catch (err) {
      console.error('[Alchemy] Curation fetch failed:', err);
      throw err;
    }
  }

  return {
    fetchFromAPI,
    getSelectedFromStorage,
    mergeWithLocal,
    fetchForCuration,
    CONFIG
  };
})();

// Export for use in main gallery script
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AlchemyIntegration;
}
