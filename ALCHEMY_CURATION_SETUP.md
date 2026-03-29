# Alchemy Curation Setup - Option B Implementation

## Overview
API-driven curation system with selective display for LOVEBEING NFT gallery integration.

## Files Created

### 1. `public/alchemy-curation.html`
- **Purpose**: Standalone curation interface for browsing & selecting LOVEBEING images
- **Features**:
  - Auto-excludes DARPA, ERC1155, ADVERTISEMENTS categories
  - Interactive grid with click-to-select thumbnails
  - Select All / Clear All actions
  - Apply Selection → stores to localStorage
  - Export JSON for records
  
- **How to Use**:
  1. Open in browser: `http://localhost:3000/alchemy-curation.html` (or via Vercel)
  2. Click "Fetch from LOVEBEING"
  3. Click thumbnails to toggle selection (✓ checkmark appears)
  4. Click "Apply Selection to Gallery" to save
  5. Selected URLs stored in `localStorage['alchemySelection']`

### 2. `public/alchemy-integration.js`
- **Purpose**: Client-side API wrapper for gallery integration
- **Key Functions**:
  - `fetchFromAPI()` → Fetches & caches images from deca.art (1hr cache)
  - `getSelectedFromStorage()` → Retrieves curated selection from localStorage
  - `mergeWithLocal(localImages)` → Combines local images + Alchemy selection
  - `fetchForCuration(onProgress)` → Streaming fetch for UI updates

## Integration into Main Gallery

To integrate curated Alchemy images into your main `public/index.html`:

```html
<!-- Add script near top -->
<script src="alchemy-integration.js"></script>

<!-- In main script section, modify localImages loading: -->
<script>
  const localImages = [
    "images/779a7b1f.jpg",
    // ... existing local images ...
  ];
  
  // Option A: Add selected Alchemy images to display
  (async () => {
    const merged = await AlchemyIntegration.mergeWithLocal(localImages);
    // Use `merged` instead of `localImages` for gallery rendering
    initGallery(merged);
  })();
</script>
```

## Workflow

1. **Curation Phase**:
   - User visits `alchemy-curation.html`
   - Clicks "Fetch from LOVEBEING" (waits for API)
   - Filters appear with 693+ images
   - User selects preferred images (✓ checkmark)
   - Clicks "Apply Selection" → saved to localStorage

2. **Display Phase**:
   - Main gallery loads `alchemy-integration.js`
   - Calls `mergeWithLocal()` to combine local + selected Alchemy
   - Renders merged gallery with GPU-optimized effects

3. **Export/Backup**:
   - Click "Export JSON" in curation UI
   - Downloads `alchemy-selection-2026-03-26.json`
   - Contains full metadata for audit trail

## API Details

- **Source**: `https://deca.art/LOVEBEING`
- **Rate Limit**: 429 Too Many Requests if hit (built-in 1hr cache handles this)
- **Data**: HTML with embedded CDN image links
- **Caching**: `localStorage` + memory cache (1hr)

## Categories Auto-Excluded

- DARPA
- ERC1155
- ADVERTISEMENTS

These won't appear in selection UI, regardless of user filters.

## Technical Stack

- **Client-side**: Vanilla JS (no dependencies)
- **Fetching**: Fetch API with CORS
- **Storage**: localStorage (persistent across sessions)
- **Rendering**: GPU-optimized (leverages existing canvas effects)

## Next Steps

1. Test curation UI: Deploy & open `/alchemy-curation.html`
2. Fetch & select images
3. Integrate `alchemy-integration.js` into main gallery
4. Update `localImages` loading logic
5. Deploy & test full gallery

## Troubleshooting

**Q: "429 Too Many Requests"**
- A: API rate limited. System uses 1hr cache; try in 15-30 min.

**Q: No images loading?**
- A: Check browser console for errors. CORS may vary by network.

**Q: Selected images not appearing in gallery?**
- A: Ensure `alchemy-integration.js` is loaded & `mergeWithLocal()` is called.

**Q: Want to reset selection?**
- A: `localStorage.removeItem('alchemySelection')` in console.
