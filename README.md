# gianniarone.com

Portfolio for Gianni Arone: video (Vimeo), art (Behance, SuperRare, Fake Rares, GIPHY, studio gallery), websites, music (SoundCloud as visitor) and resume.

Static HTML in `public/`, served by Vercel, with serverless functions in `api/` for the studio gallery's Blob-backed admin panel.

## Pages

| Path | What |
| --- | --- |
| `/` | Home: hero collage, reel, featured video, art picks, featured sites, album, about |
| `/video/` | Every video from vimeo.com/uaawtf with filters; playable ones open in an on-page player |
| `/art/` | Illustration & GIF art, SuperRare works by series, Fake Rares, GIPHY wall, physical strip |
| `/art/gallery/` | The original Blob-backed gallery (admin panel behind the gear icon), now also showing the static art as "digital" |
| `/web/` | Website cards; each opens a micro-page lightbox with a scrolling full-page capture, phone view and live link |
| `/music/` | SoundCloud: album player, every track (click to play), playlists and archive |
| `/resume/` | Resume, print-friendly (Print / Save as PDF button) |

Shared styling is `public/portfolio.css`; shared behaviour (nav, reveal animations, lazy loops, video modal, micro-pages, lightbox) is `public/portfolio.js`.

## Data files (edit these to change content)

| File | Feeds | Refresh |
| --- | --- | --- |
| `public/videos.json` | Video pages | `npm run sync-vimeo` (keeps hand-set `category` and `featured`) |
| `public/sites.json` | Web cards and micro-pages | Edit by hand; screenshots live in `public/img/sites/` and `public/img/sites/full/` |
| `public/art.json` | Art page, home art picks, gallery "digital" items | Edit by hand; assets in `public/img/art/` |
| `public/music.json` | Music page | Edit by hand; artwork in `public/img/music/` |

## Video playback

Only videos whose Vimeo privacy allows embedding **anywhere** play on the site. The rest show a "Vimeo ↗" badge and open on vimeo.com. To make everything play on-site: Vimeo → Videos → select all → Privacy → *Where can this be embedded?* → Anywhere (or add gianniarone.com to the allowed domains).

## Putting the art into Blob storage

The art page and the gallery already display the harvested art from `public/img/art/`. To store copies in the gallery's Vercel Blob store as well (tagged "digital"):

```sh
BLOB_READ_WRITE_TOKEN=... npm run upload-art
```

## Local preview

```sh
npm run dev   # http://localhost:3000 (API routes are not served locally; the gallery falls back gracefully)
```
